from .util import get_entry_prices, get_bsc_contract_instance, get_web3_provider
from ._config import DEFAULT_BSC_RPC_URL
from .vault_contracts import DeltaNeutralVault, DeltaNeutralOracle, AutomatedVaultController

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
        self.working_token = summary['workingToken']

        # Relevant contracts to control the vault and get data
        self.oracle = DeltaNeutralOracle(self.w3_provider)
        self.vault = DeltaNeutralVault(self.address, self.w3_provider)
        self.controller = AutomatedVaultController(self.w3_provider)

    """ ------------------ Transactional Methods (Requires private wallet key) ------------------ """

    def invest(self):
        raise NotImplementedError

    def withdraw(self):
        raise NotImplementedError

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
        return self.get_vault_summary().capacity

    def cost_basis(self) -> float:
        """Returns the entry price of the position"""
        return self.entry_price() * self.shares()[0]

    def current_value(self) -> float:
        """Returns the current position value in USD"""
        return self.shares()[1]

    def pnl(self) -> float:
        """Returns the pnl for the current position in USD value"""
        shares_vault, shares_usd = self.shares()
        entry_value = self.entry_price() * shares_vault

        return shares_usd - entry_value

    def shares(self) -> tuple[float, float]:
        """
        Returns the amount of vault shares held in the position, and the value of the shares in USD
        The share value in USD is also the position value as shown on the webapp.

        :return: (vault_shares, vault_shares_usd)
        """
        shares_int = self.vault.shares(self.owner_address)
        shares_usd = self.vault.sharesToUSD(shares_int) / 10 ** 18

        return shares_int / 10 ** self.bep20_vault_token.decimals(), shares_usd

    def entry_price(self) -> float:  # tuple[float, float]
        """CURRENTLY - Returns the entry share price (single share) in USD
        To get current share price, use self.get_vault_summary()['shareTokenprice']

        :return: entry_share_price_usd
        """
        try:
            for data in get_entry_prices(self.owner_address):
                if data['strategyPoolAddress'].lower() == self.address.lower():
                    if self.vault_type == "neutral":
                        entry_share_price = float(data['avgEntryPrice']) / 10 ** 18
                        entry_share_price_usd = entry_share_price
                    else:
                        bep20_b_token = BEP20Token(self.working_token['tokenB']['address'], self.w3_provider)
                        entry_share_price = float(data['avgEntryPrice']) / 10 ** bep20_b_token.decimals()
                        entry_share_price_usd = self.oracle.getTokenPrice(bep20_b_token.address) * entry_share_price

                    return entry_share_price_usd
        except Exception as exc:
            raise Exception(f"An error occurred when attempting to fetch entry price for position {self.name} - {exc}")
