from os.path import join, abspath, dirname
from os import getcwd, pardir
import json

import requests

def get_contract_instance(contract_address: str, abi_filename: str):
    pass


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


def bep20_balance(address: str) -> float:
    pass


def bep20_decimals(address: str) -> int:
    pass


def store_abi(abi_url: str, abi_filename: str, abi_path: str = None) -> None:
    """
    Format and store a smart contract ABI in JSON locally
    :param abi_url: BSC SCAN -> Export ABI -> RAW/Text Format -> Get the URL
                    (ex. "http://api.etherscan.io/api?module=contract&action=getabi&address=0xc4a59cfed3fe06bdb5c21de75a70b20db280d8fe&format=raw")
    :param abi_filename: The desired filename for local storage
    :param abi_path: The local path for the abi if one already exists and is being refactored
    """
    contract_abi = requests.get(abi_url).json()

    path = join(join(dirname(__file__)), "abi", abi_filename) if abi_path is None else abi_path
    with open(path, "w") as json_file:
        json_file.write(json.dumps(contract_abi, indent=2))
