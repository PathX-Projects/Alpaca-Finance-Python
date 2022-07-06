import json

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


def format_json_file(filepath: str) -> None:
    with open(filepath, 'r') as infile:
        data = json.load(infile)
        with open(filepath, 'w') as outfile:
            outfile.write(json.dumps(data, indent=2))
