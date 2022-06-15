import requests


def get_entry_prices(wallet_address: str) -> list[dict]:
    """
    Fetch all of the pool entry prices for the given wallet address

    :param wallet_address:
    :return: List of dicts containing:
                * succeed: bool
                * strategyPoolAddress: str
                * avgEntryPrice: str (in integer format)
    """
    r = requests.get(f"https://api.alpacafinance.org/bsc/v1/delta-neutral/avg-entry-prices?userAddress={wallet_address}")
    return r.json()["data"]["avgEntryPrices"]