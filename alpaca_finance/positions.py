import requests
# from web3 import Web3
from attrdict import AttrDict

from .util import get_entry_prices


class AutomatedVaultPosition:
    def __init__(self, position_key: str, owner_wallet_address: str, owner_wallet_key: str = None):
        summary = self.get_vault_summary(position_key.lower())

        self.owner_address = owner_wallet_address
        self.owner_key = owner_wallet_key

        # Store position metadata
        self.key = summary['key']
        self.name = summary['name']
        self.address = summary['address'].lower()

    """ ------------------ Transactional Methods (Requires private wallet key) ------------------ """

    def harvest_rewards(self):
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

    def cost_basis(self):
        # "shareTokenPrice" from self.get_vault_summary() may be useful

        pass

    def current_value(self):
        pass

    def pnl(self) -> float:
        """Returns the pnl for the current position in USD value"""
        pass

    def entry_price(self) -> float:
        try:
            for data in get_entry_prices(self.owner_address):
                if data['strategyPoolAddress'].lower() == self.address.lower():
                    return float(data['avgEntryPrice'])
            else:
                raise IndexError
        except IndexError:
            raise Exception(f"could not fetch entry price for position: {self.address}")
        except Exception as exc:
            raise Exception(f"An error occurred when attempting to fetch entry price for position {self.name} - {exc}")
