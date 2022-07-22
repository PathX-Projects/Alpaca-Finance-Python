from typing import Optional, Union
from math import floor

from ..util import get_entry_prices, get_web3_provider, get_vault_addresses
from ._config import DEFAULT_BSC_RPC_URL
from .receipt import TransactionReceipt, build_receipt
from .contracts import DeltaNeutralVault, DeltaNeutralOracle, AutomatedVaultController, DeltaNeutralVaultGateway

from eth_abi import decode_abi
import requests
import web3.contract
from web3 import Web3
from attrdict import AttrDict
from bep20 import BEP20Token


class AutomatedVaultPosition:
    def __init__(self, position_key: str, owner_wallet_address: str, owner_wallet_key: str = None, w3_provider: Web3 = None):
        if w3_provider is None:
            self.w3_provider = get_web3_provider(DEFAULT_BSC_RPC_URL)
        else:
            self.w3_provider = w3_provider

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

    def do_invest(self) -> TransactionReceipt:
        raise NotImplementedError

    def do_withdraw(self, shares: int, pct_stable: float = None, strategy: str = "Minimize Trading") -> TransactionReceipt:
        """
        Withdraws the specified amount of shares from the automated vault position.

        :param shares: The amount of share to withdraw from the vault (in share tokens) (self.shares()[0] = close position)
        :param pct_stable: The percentage of stable token returned to the owner (.50 = 50% stable and 50% asset returned)
        :param strategy: The strategy to use to withdraw, as shown on the webapp (Minimize Trading, Convert All)
        """
        assert self.shares()[0] >= shares, f"Shares owned insufficient to withdraw {shares} " \
                                           f"({self.from_wei(shares, self.bep20_vault_token.decimals())}) shares"

        if strategy.lower() == "minimize trading":
            return self._execute(self.vault.withdraw(shares))
        elif strategy.lower() == "convert all":
            assert pct_stable is not None, "Please provide a stable token percentage to determine token swap"
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
        print(txn)

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
        print(transaction)

        try:
            decoded_bank_transaction = self.vault.contract.decode_function_input(transaction.input)
        except:
            decoded_bank_transaction = self.gateway.contract.decode_function_input(transaction.input)

        decoded_calldata = decode_abi(
            ["uint256"],
            decoded_bank_transaction[1]['_data']
        )

        return decoded_bank_transaction, decoded_calldata

