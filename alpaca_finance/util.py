from os.path import join, abspath, dirname
from os import getcwd, pardir
import json

from alpaca_finance.automated_vault._config import DEFAULT_BSC_RPC_URL

import requests
from web3 import Web3


def get_web3_provider(network_rpc_url: str) -> Web3:
    """Returns a Web3 connection provider object"""
    return Web3(Web3.HTTPProvider(network_rpc_url))


def get_bsc_contract_instance(contract_address: str, abi_filename: str, w3_provider: Web3 = None):
    if w3_provider is None:
        w3_provider = get_web3_provider(DEFAULT_BSC_RPC_URL)

    abi_storage_path = join(abspath(dirname(__file__)), "automated_vault/abi")
    with open(join(abi_storage_path, abi_filename)) as json_file:
        contract_abi = json.load(json_file)

    contract_address = Web3.toChecksumAddress(contract_address)

    return w3_provider.eth.contract(address=contract_address, abi=contract_abi)


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


def store_abi(abi_url: str, abi_filename: str, abi_path: str = None) -> None:
    """
    Format and store a smart contract ABI in JSON locally
    :param abi_url: BSC SCAN -> Export ABI -> RAW/Text Format -> Get the URL
                    (ex. "http://api.etherscan.io/api?module=contract&action=getabi&address=0xc4a59cfed3fe06bdb5c21de75a70b20db280d8fe&format=raw")
    :param abi_filename: The desired filename for local storage
    :param abi_path: The local path for the abi if one already exists and is being refactored
    """
    contract_abi = requests.get(abi_url).json()

    path = join(join(dirname(__file__)), "automated_vault/abi", abi_filename) if abi_path is None else abi_path
    with open(path, "w") as json_file:
        json_file.write(json.dumps(contract_abi, indent=2))


def get_vault_addresses(vault_address: str) -> dict:
    for r in requests.get("https://raw.githubusercontent.com/alpaca-finance/bsc-alpaca-contract/main/.mainnet.json").json()['DeltaNeutralVaults']:
        if r['address'].lower() == vault_address.lower():
            return r
