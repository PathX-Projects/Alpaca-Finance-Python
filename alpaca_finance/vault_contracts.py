from .util import get_bsc_contract_instance
from ._config import DELTA_NEUTRAL_ORACLE_ADDRESS, DELTA_NEUTRAL_VAULT_ADDRESS, AUTOMATED_VAULT_CONTROLLER_ADDRESS

from web3 import Web3
from bep20.util import checksum


class DeltaNeutralOracle:
    def __init__(self, w3_provider: Web3 = None):
        self.contract = get_bsc_contract_instance(contract_address=DELTA_NEUTRAL_ORACLE_ADDRESS,
                                                  abi_filename="DeltaNeutralOracle.json",
                                                  w3_provider=w3_provider)

    def lpToDollar(self, lp_amount: int, pancakeswap_lp_token_address: str) -> int:
        """Return the value in USD for the given lpAmount"""
        return self.contract.functions.lpToDollar(lp_amount, checksum(pancakeswap_lp_token_address)).call()

    def dollarToLp(self, dollar_amount: int, lp_token_address: str) -> int:
        """Return the amount of LP for the given USD"""
        return self.contract.functions.dollarToLp(dollar_amount, checksum(lp_token_address)).call()

    def getTokenPrice(self, token_address: str) -> int:
        """Return the price of the given token (address) in USD"""
        return self.contract.functions.getTokenPrice(checksum(token_address)).call()[0] / 10 ** 18


class DeltaNeutralVault:
    def __init__(self, w3_provider: Web3 = None):
        self.contract = get_bsc_contract_instance(contract_address=DELTA_NEUTRAL_VAULT_ADDRESS,
                                                  abi_filename="DeltaNeutralVault.json", w3_provider=w3_provider)

    def withdraw(self):
        pass


class AutomatedVaultController:
    def __init__(self, w3_provider: Web3 = None):
        self.contract = get_bsc_contract_instance(contract_address=AUTOMATED_VAULT_CONTROLLER_ADDRESS,
                                                  abi_filename="AutomatedVaultController.json",
                                                  w3_provider=w3_provider)

    def getUserVaultShares(self, owner_address: str, vault_address: str) -> int:
        return self.contract.functions.getUserVaultShares(checksum(owner_address), checksum(vault_address)).call()

    def totalCredit(self, user_address: str) -> int:
        """Get the user's total credit in USD"""
        return self.contract.functions.totalCredit(checksum(user_address)).call()