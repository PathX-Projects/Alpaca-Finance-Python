from typing import Optional

from .util import get_entry_prices, get_web3_provider, get_vault_addresses
from ._config import DEFAULT_BSC_RPC_URL
from .vault_contracts import DeltaNeutralVault, DeltaNeutralOracle, AutomatedVaultController, DeltaNeutralVaultGateway

import requests
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

        # Set the stable token for reference
        self.stable_token = BEP20Token(self.vault.stableTokenAddress())

    """ ------------------ Transactional Methods (Requires private wallet key) ------------------ """

    def invest(self):
        raise NotImplementedError

    def withdraw(self, shares: int):
        """Withdraws the specified amount of shares from the automated vault position."""
        return self.vault.withdraw(shares)

    def close_position(self):
        raise NotImplementedError

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

    def sign_and_send_tx(self):
        pass

    def decode_transaction_data(self, transaction_address: Optional):
        """
        Returns the transaction data used to invoke the smart contract function for the underlying contract
        First fetches the transaction data for the HomoraBank.execute() function, then gets the transaction data
        for the underlying smart contract
        :param w3_provider: The Web3.HTTPProvider object for interacting with the network
        :param transaction_address: The transaction address (binary or str)
        :return: (
            decoded bank function (ContractFunction, dict),
            decoded spell function (ContractFunction, dict)
        )
        """
        transaction = self.w3_provider.eth.get_transaction(transaction_address)

        decoded_bank_transaction = self.vault.contract.decode_function_input(transaction.input)

        # return decoded_bank_transaction

        encoded_contract_data = decoded_bank_transaction[1]['_data']

        return decoded_bank_transaction, self.gateway.contract.decode_function_input(encoded_contract_data)

