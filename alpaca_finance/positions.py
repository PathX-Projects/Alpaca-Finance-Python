import requests
from web3 import Web3
from attrdict import AttrDict

from .util import get_entry_prices


class AutomatedVaultPosition:
    def __init__(self, position_key: str, owner_wallet_address: str, owner_wallet_key: str = None):
        summary = self.get_vault_summary(position_key.lower())

        # Store position metadata
        self.position_key = summary['key']
        self.position_name = summary['name']
        self.position_address = summary['address'].lower()

        # Store entry price for future calculations
        try:
            self.entry_price = int([record for record in get_entry_prices(owner_wallet_address)
                                    if record['strategyPoolAddress'].lower() == self.position_address][0]['avgEntryPrice'])
        except IndexError:
            raise Exception(f"could not fetch entry price for position: {self.position_address}")

    def harvest_rewards(self):
        pass

    def close_position(self):
        pass

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
                position_key = self.position_key
            except AttributeError:
                raise ValueError("Could not fetch vault summary -> position key not supplied")

        r = requests.get("https://alpaca-static-api.alpacafinance.org/bsc/v1/landing/summary.json")
        if r.status_code != 200:
            raise Exception(f"{r.status_code}: {r.text}")

        for vault in r.json()["data"]["strategyPools"]:
            if vault["key"].lower() == position_key:
                return AttrDict(vault)
        else:
            raise ValueError(f"Could not locate a vault with the key {self.position_key}")

    def get_rebalance_history(self):
        pass

    def get_cost_basis(self):
        # "shareTokenPrice" from self.get_vault_summary() may be useful

        pass

    def get_current_value(self):
        pass

    def get_pnl(self) -> float:
        """Returns the pnl for the current position in USD value"""
        pass
