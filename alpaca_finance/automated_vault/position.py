from typing import Union, Optional
from math import floor

from ..util import get_entry_prices, get_web3_provider, get_vault_addresses, checksum
from ._config import DEFAULT_BSC_RPC_URL
from .receipt import TransactionReceipt, build_receipt
from .contracts import DeltaNeutralVault, DeltaNeutralOracle, AutomatedVaultController, DeltaNeutralVaultGateway

from eth_abi import decode_abi
import requests
import web3.contract
from web3 import Web3
from web3.constants import MAX_INT
from attrdict import AttrDict
from bep20 import BEP20Token


class AutomatedVaultPosition:
    def __init__(self, position_key: str, owner_wallet_address: str, owner_wallet_key: str = None, w3_provider: Web3 = None):
        if w3_provider is None:
            self.w3_provider = get_web3_provider(DEFAULT_BSC_RPC_URL)
        else:
            self.w3_provider = w3_provider
        if self.w3_provider.eth.chainId != 56:
            raise ValueError("This package currently supports positions on the Binance Smart Chain (BSC - 56) network only")

        summary = self.get_vault_summary(position_key.lower())

        self.owner_address = owner_wallet_address
        self.owner_key = owner_wallet_key

        # Store position metadata
        self.key = summary['key']
        self.name = summary['name']
        self.address = summary['address'].lower()
        self.vault_type = "neutral" if self.key.startswith("n") else "long/savings"
        self.bep20_vault_token = BEP20Token(self.address, self.w3_provider)

        # Relevant contracts to control the vault and get data
        self.oracle = DeltaNeutralOracle(self.w3_provider)
        self.vault = DeltaNeutralVault(self.address, self.w3_provider)
        self.controller = AutomatedVaultController(self.w3_provider)
        self.gateway = DeltaNeutralVaultGateway(get_vault_addresses(self.address)['gateway'], self.w3_provider)

        # Set the vault tokens for reference
        self.stable_token = BEP20Token(self.vault.stableTokenAddress(), self.w3_provider)
        self.asset_token = BEP20Token(self.vault.assetTokenAddress(), self.w3_provider)

    """ ------------------ Transactional Methods (Requires private wallet key) ------------------ """

    def do_invest(self, stable_token_amt: int = 0, asset_token_amt: int = 0, _approve=False) -> TransactionReceipt:
        """
        Invest the specified amount of each token into the Automated Vault.
        Use self.asset_token and self.stable_token to identify the underlying assets.

        :param stable_token_amt: The amount of stable token to deposit
        :param asset_token_amt: The amount of asset token to deposit
        :param _approve: If True, approves the deposit token for spending by the vault token
        :return:
        """
        assert stable_token_amt > 0 or asset_token_amt > 0, \
            "Please provide an investment value for either the stable or asset tokens"

        # Ensure that allowances match desired investment amount
        if stable_token_amt > 0:
            token_bal = self.stable_token.balanceOf(self.owner_address)
            assert token_bal >= stable_token_amt, \
                f"Insufficient funds to invest {stable_token_amt} {self.stable_token.symbol()} ({token_bal} Owned)"
            if _approve:
                self.do_approve_token(self.stable_token)
        if asset_token_amt > 0:
            token_bal = self.asset_token.balanceOf(self.owner_address)
            assert token_bal >= asset_token_amt, \
                f"Insufficient funds to invest {asset_token_amt} {self.asset_token.symbol()} ({token_bal} Owned)"
            if _approve:
                self.do_approve_token(self.asset_token)

        return self._execute(self.vault.invest(stable_token_amt, asset_token_amt, shareReceiver=self.owner_address))

    def do_withdraw(self, shares: int, pct_stable: float = None, strategy: str = "Minimize Trading") -> TransactionReceipt:
        """
        Withdraws the specified amount of shares from the automated vault position.

        :param shares: The amount of share to withdraw from the vault (in share tokens) (self.shares()[0] = close position)
        :param pct_stable: The percentage of stable token returned to the owner (.50 = 50% stable and 50% asset returned)
        :param strategy: The strategy to use to withdraw, as shown on the webapp (Minimize Trading, Convert All)
        (NOT IN USE) :param _approve: If True, force approves the vault token to be spent by either the gateway or the vault contract
        """
        assert self.shares()[0] >= shares, f"Shares owned insufficient to withdraw {shares} " \
                                           f"({self.from_wei(shares, self.bep20_vault_token.decimals())}) shares"

        if strategy.lower() == "minimize trading":
            # assert self.bep20_vault_token.allowance(self.owner_address, self.vault.address) >= shares, \
            #     f"Insufficient approval amount - Spender ({self.vault.address}) requires an allowance of {shares} " \
            #     f"{self.bep20_vault_token.symbol()} ({self.bep20_vault_token.address})"

            return self._execute(self.vault.withdraw(shares))
        elif strategy.lower() == "convert all":
            assert pct_stable is not None, "Please provide a stable token percentage to determine token swap"
            assert self.bep20_vault_token.allowance(self.owner_address, self.gateway.address) >= shares, \
                f"Insufficient approval amount - Spender ({self.gateway.address}) requires an allowance of {shares} " \
                f"{self.bep20_vault_token.symbol()} ({self.bep20_vault_token.address})"

            assert 0.0 < pct_stable <= 1.0, "Invalid value for pct_stable parameter, must follow 0.0 < pct_stable <= 1.0"

            stable_return_bps = floor(pct_stable * 10000)

            return self._execute(self.gateway.withdraw(shares, stableReturnBps=stable_return_bps))
        else:
            raise ValueError("Invalid strategy - Options are 'Minimize Trading' or 'Convert All'")

    def do_close(self, pct_stable: float = None, strategy: str = "Minimize Trading") -> TransactionReceipt:
        """
        Withdraws all outstanding shares from the pool and closes position.

        :param pct_stable: See self.withdraw()
        :param strategy: See self.withdraw()
        """
        return self.do_withdraw(shares=self.shares()[0], pct_stable=pct_stable, strategy=strategy)

    def do_approve_token(self, token: Union[BEP20Token, str], amount: int = None, _spender: str = None) -> TransactionReceipt:
        """
        Approves the given token for usage by the Automated Vault.

        :param token: Optional - either the BEP20Token object, or the token address (str)
        :param amount: The amount of token to approve, default = maximum
        :param _spender: (Should not be changed by the caller) The address to give token spending access to
        """
        if type(token) != BEP20Token:
            token = BEP20Token(token)

        if amount is None:
            # Use maximum approval amount if no amount is specified
            amount = 2 ** 256 - 1

        if _spender is None:
            _spender = self.address

        func_call = token.prepare_approve(checksum(_spender), amount)

        return self._execute(func_call)


    """ ---------------- Informational Methods (Private wallet key not required) ---------------- """

    def get_vault_summary(self, position_key: str = None) -> AttrDict:
        """
        Fetch data about the current vault position

        :return: Vault summary Attribute Dictionary containing the following keys:
            * key: str
            * name: str
            * address (strategyPoolAddress): str
            * aprTradingFeeExcluded: str (float)
            * apyTradingFeeExcluded: str (float)
            * apr: str (float) (in % form)
            * apy: str (float) (in % form)
            * tvl: str (float)
            * tvlIncludingDebt: str (float)
            * shareTokenPrice: str (float)
            * capacity: str (float)
            * inceptionDate: str (datetime object 2022-03-24T00:00:00.000Z)
            * uiToken: Attribute Dict
                * address: str
                * symbol: str
            * workingToken: Attribute Dict
                * address: str
                * symbol: str
                * tokenA: Attribute Dict
                    * address: str
                    * symbol: str
                * tokenB: Attribute Dict
                    * address: str
                    * symbol: str

        """
        if position_key is None:
            try:
                position_key = self.key
            except AttributeError:
                raise ValueError("Could not fetch vault summary -> position key not supplied")

        r = requests.get("https://alpaca-static-api.alpacafinance.org/bsc/v1/landing/summary.json")
        if r.status_code != 200:
            raise Exception(f"{r.status_code}: {r.text}")

        for vault in r.json()["data"]["strategyPools"]:
            if vault["key"].lower() == position_key:
                return AttrDict(vault)
        else:
            raise ValueError(f"Could not locate a vault with the key {self.key}")

    def rebalance_history(self):
        pass

    def yields(self) -> list[float, float, float, float]:
        """
        :return:
            - current APR (excluding trading fee)
            - current APY (excluding trading fee)
            - current APR
            - current APY
        """
        summary = self.get_vault_summary()
        return [float(summary[key]) for key in ["aprTradingFeeExcluded", "apyTradingFeeExcluded", "apr", "apy"]]

    def tvl(self) -> list[float, float]:
        """
        :return:
            - TVL (total value locked)
            - TVL Including Debt
        """
        summary = self.get_vault_summary()
        return [float(summary[key]) for key in ["tvl", "tvlIncludingDebt"]]

    def capacity(self) -> float:
        return float(self.get_vault_summary().capacity)

    def current_value(self) -> float:
        """Returns the current position value in USD"""
        return self.shares()[-1]

    def pnl(self) -> float:
        """Returns the pnl for the current position in USD value"""
        shares_vault_int, shares_vault, shares_usd = self.shares()
        entry_value = self.cost_basis() * shares_vault

        return shares_usd - entry_value

    def shares(self) -> tuple[int, float, float]:
        """
        Returns the amount of vault shares held in the position, and the value of the shares in USD
        The share value in USD is also the position value as shown on the webapp.

        :return: (vault_shares, vault_shares_usd)
        """
        shares_int = self.vault.shares(self.owner_address)
        shares_usd = self.vault.sharesToUSD(shares_int) / 10 ** 18

        return shares_int, shares_int / 10 ** self.bep20_vault_token.decimals(), shares_usd

    def cost_basis(self) -> float:  # tuple[float, float]
        """CURRENTLY - Returns the entry share price (single share) in USD
        To get current share price, use self.get_vault_summary()['shareTokenprice']

        :return: entry_share_price_usd

        @dev (ignore):
        For Neutral AV (prefixed with n3x or n8x), "avgEntryPrice" will be denominated in USD.
        For Long AV or Savings AV (prefixed with L3x or L8x), "avgEntryPrice" will be denominated in the Savings Asset (e.g. BTCB or ETH).
        """
        try:
            for data in get_entry_prices(self.owner_address):
                if data['strategyPoolAddress'].lower() == self.address.lower():
                    entry_share_price = float(data['avgEntryPrice']) / 10 ** self.stable_token.decimals()
                    entry_share_price_usd = self.oracle.getTokenPrice(self.stable_token.address) * entry_share_price

                    return entry_share_price_usd * self.shares()[1]
        except Exception as exc:
            raise Exception(f"An error occurred when attempting to fetch entry price for position {self.name} - {exc}")

    """ -------------------------------- Utility Methods -------------------------------- """

    def _execute(self, function_call: web3.contract.ContractFunction) -> TransactionReceipt:
        """
        :param function_call: The uncalled and prepared contract method to sign and send
        """
        if self.owner_key is None:
            raise ValueError("Private key is required to sign transactions")

        txn = function_call.buildTransaction({
            "from": self.owner_address,
            'chainId': 56,  # 56: BSC mainnet
            # 'gas': 76335152,
            'gasPrice': 5000000000,
            'nonce': self.w3_provider.eth.get_transaction_count(self.owner_address),
        })
        # print(txn)

        signed_txn = self.w3_provider.eth.account.sign_transaction(
            txn, private_key=self.owner_key
        )
        tx_hash = self.w3_provider.eth.send_raw_transaction(signed_txn.rawTransaction)

        receipt = dict(self.w3_provider.eth.wait_for_transaction_receipt(tx_hash))

        try:
            return build_receipt(receipt)
        except Exception as exc:
            print(f"COULD NOT BUILD TRANSACTION RECEIPT OBJECT - {exc}")
            # Catch case to prevent receipt from being lost if TransactionReceipt object somehow can't be built
            return receipt

    @staticmethod
    def to_wei(amt: float, decimals: int) -> int:
        return int(amt * (10 ** decimals))

    @staticmethod
    def from_wei(amt: int, decimals: int) -> int:
        return amt / (10 ** decimals)

    def _decode_withdraw_transaction(self, transaction_address: Optional):
        """
        Returns the transaction data used to invoke the smart contract function for the underlying contract
        First fetches the transaction data for the HomoraBank.execute() function, then gets the transaction data
        for the underlying smart contract

        :param transaction_address: The transaction address (binary or str)
        :return: (
            decoded bank function (ContractFunction, dict),
            decoded spell function (ContractFunction, dict)
        )
        """
        transaction = self.w3_provider.eth.get_transaction(transaction_address)
        print(transaction)

        try:
            decoded_bank_transaction = self.vault.contract.decode_function_input(transaction.input)
        except:
            decoded_bank_transaction = self.gateway.contract.decode_function_input(transaction.input)

        decoded_calldata = decode_abi(
            ['uint256', 'uint256'],
            decoded_bank_transaction[1]['_data']
        )

        return decoded_bank_transaction, decoded_calldata

    def _decode_deposit_transaction(self, transaction_address: Optional):
        """
        Returns the transaction data used to invoke the smart contract function for the underlying contract
        First fetches the transaction data for the HomoraBank.execute() function, then gets the transaction data
        for the underlying smart contract

        :param transaction_address: The transaction address (binary or str)
        :return: (
            decoded bank function (ContractFunction, dict),
            decoded spell function (ContractFunction, dict)
        )
        """
        transaction = self.w3_provider.eth.get_transaction(transaction_address)
        # print(transaction)

        try:
            decoded_bank_transaction = self.vault.contract.decode_function_input(transaction.input)
        except:
            decoded_bank_transaction = self.gateway.contract.decode_function_input(transaction.input)

        decoded_calldata = decode_abi(
            ["uint256"],
            decoded_bank_transaction[1]['_data']
        )

        return decoded_bank_transaction, decoded_calldata

