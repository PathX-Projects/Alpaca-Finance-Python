import os
import sys
sys.path.insert(0, '..')

from alpaca_finance.vault_contracts import AutomatedVaultController

import requests

if __name__ == "__main__":
    controller = AutomatedVaultController()

    WALLET_ADDRESS = "0xC9E6e248928aC18eD6b103653cBcF66d23B743C6"

    for pool in requests.get("https://alpaca-static-api.alpacafinance.org/bsc/v1/landing/summary.json").json()['data']['strategyPools']:
        print(pool['name'], "Shares:", controller.getUserVaultShares(WALLET_ADDRESS, pool['address']))
        print(pool['workingToken']['symbol'])

