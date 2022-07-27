from ..util import get_bsc_contract_instance
from ._config import DELTA_NEUTRAL_ORACLE_ADDRESS, AUTOMATED_VAULT_CONTROLLER_ADDRESS
# from .work_bytes import WithdrawWorkByte  #  <- Deprecated

import requests
import web3.contract
from web3 import Web3
from bep20.util import checksum
from eth_abi import encode_abi


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
    def __init__(self, vault_address: str, w3_provider: Web3 = None, protocol: str = "pancakeswap"):
        """
        :param vault_address: The address for the Delta Neutral Vault
        :param protocol: The protocol ID that the vault resides on (pancakeswap or biswap)
        :param w3_provider: Web3 provider (optional), if provided speeds up initialization time
        """
        AVAILABLE_PROTOCOLS = ["pancakeswap", "biswap"]

        self.address = vault_address
        self.contract = get_bsc_contract_instance(contract_address=vault_address,
                                                  abi_filename="DeltaNeutralVault.json", w3_provider=w3_provider)
        self.protocol = protocol.lower()
        assert protocol in AVAILABLE_PROTOCOLS, NotImplementedError(f"Available protocols are {AVAILABLE_PROTOCOLS}")

        self.ACTION_WORK = 1

        r = requests.get("https://raw.githubusercontent.com/alpaca-finance/bsc-alpaca-contract/main/.mainnet.json").json()

        # Get vault addresses:
        try:
            self.addresses = list(filter(lambda v: v['address'].lower() == vault_address.lower(), r['DeltaNeutralVaults']))[0]
            """
            E.x.
            "name": "Long 3x BUSD-BTCB PCS2",
            "symbol": "L3x-BUSDBTCB-PCS2",
            "address": "0xA1679223b7585725aFb425a6F59737a05e085C40",
            "deployedBlock": 18042257,
            "config": "0x39936A4eC165e2372C8d91c011eb36576dBE5d32",
            "assetToken": "0xe9e7cea3dedca5984780bafc599bd69add087d56",
            "stableToken": "0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c",
            "assetVault": "0x7C9e73d4C71dae564d41F78d56439bB4ba87592f",
            "stableVault": "0x08FC9Ba2cAc74742177e0afC3dC8Aed6961c24e7",
            "assetDeltaWorker": "0x071ac07A287C643b193bc107D29DF4D53BFFAFf7",
            "stableDeltaWorker": "0x3F89B3198cB710248136bbB640e88C1618436d20",
            "oracle": "0x08EA5fB66EA41f236E3001d2655e43A1E735787F",
            "gateway": "0x0256E784f73391797f80a9902c0fD05a718a812a",
            "assetVaultPosId": "54752",
            "stableVaultPosId": "5630"
            """
        except IndexError:
            raise IndexError(f"Could not locate Delta Neutral Vault with address {vault_address}")

        # Get strategy addresses:
        # self.partialCloseMinimizeStrat = {"pancakeswap": "0x8dcEC5e136B6321a50F8567588c2f25738D286C2",
        #                                   "biswap": "0x3739d1E01104b019Ff105B3A8F57BC6ed62F18a4"}
        self.partialCloseMinimizeStrat = {"pancakeswap": r['SharedStrategies']["Pancakeswap"]["StrategyPartialCloseMinimizeTrading"],
                                          "biswap": r['SharedStrategies']["Biswap"]["StrategyPartialCloseMinimizeTrading"]}

    def invest(self, stableTokenAmount: int, assetTokenAmount: int, shareReceiver: str) -> web3.contract.ContractFunction:
        """Invest the specified token into the vault"""

        minShareReceive = 0  # Slippage

        _calldata = encode_abi(
            ["uint256"],
            [25]
        )

        return self.contract.functions.deposit(stableTokenAmount, assetTokenAmount, checksum(shareReceiver),
                                               minShareReceive, _calldata)

    def withdraw(self, shares: int) -> web3.contract.ContractFunction:
        """
        Withdraw the given amount of shares from the Delta Neutral Vault using the 'Minimize Trading' strategy.

        :param shares: The amount of shares to withdraw (in shares/vault token)
        :return: Uncalled prepared ContractFunction
        """
        # All Slippage Controls
        minStableTokenAmount = 0
        minAssetTokenAmount = 0

        # Constant calldata (should not change)
        _calldata = encode_abi(
            ["uint256", "uint256"],
            [25, 1]
        )

        return self.contract.functions.withdraw(shares, minStableTokenAmount, minAssetTokenAmount, _calldata)
    
    def shares(self, user_address: str) -> int:
        """Return the number of shares owned by the given user"""
        return self.contract.functions.balanceOf(checksum(user_address)).call()

    def positionInfo(self) -> list:
        """
        Return total equity and debt value in USD of stable and asset positions

        :return:
            - stablePositionEquity
            - stablePositionDebtValue
            - StableLpAmount
            - assetPositionEquity
            - assetPositionDebtValue
            - assetLpAmount
        """
        return list(self.contract.functions.positionInfo().call())
    
    def sharesToUSD(self, share_amount: int) -> int:
        """Returns the value in USD for the given amount of vault shares"""
        return self.contract.functions.shareToValue(share_amount).call()

    def stableTokenAddress(self) -> str:
        """Returns the address for the delta vault stable token"""
        return self.contract.functions.stableToken().call()

    def assetTokenAddress(self) -> str:
        """Returns the address for the delta vault stable token"""
        return self.contract.functions.assetToken().call()


class DeltaNeutralVaultGateway:
    def __init__(self, gateway_address: str, w3_provider: Web3 = None):
        self.address = gateway_address
        self.contract = get_bsc_contract_instance(contract_address=gateway_address,
                                                  abi_filename="DeltaNeutralVaultGateway.json", w3_provider=w3_provider)

    def withdraw(self, shares: int, stableReturnBps: int) -> web3.contract.ContractFunction:
        """
        Withdraw shares from the vault using the gateway

        :param shares: The amount of share to withdraw from the vault (in vault tokens) (e.g. 10 shares = 10 ** vault token decimals)
        :param stableReturnBps: The percentage of tokens returned that should be stable tokens (in Basis Points)
        :return: uncalled prepared ContractFunction
        """

        # All Slippage Controls
        minWithdrawStableTokenAmount = 0  # Minimum stable token shareOwner expect to receive after withdraw.
        minWithdrawAssetTokenAmount = 0  # Minimum asset token shareOwner expect to receive after withdraw.
        minSwapStableTokenAmount = 0  # Minimum stable token shareOwner expect to receive after swap.
        minSwapAssetTokenAmount = 0  # Minimum asset token shareOwner expect to receive after swap.

        # Constant calldata (should not change)
        _calldata = encode_abi(
            ["uint256", "uint256"],
            [25, 1]
        )

        # stableReturnBps = 10000  # Percentage stable token shareOwner expect to receive in bps (10000 == 100%)
        return self.contract.functions.withdraw(shares, minWithdrawStableTokenAmount, minWithdrawAssetTokenAmount,
                                                minSwapStableTokenAmount, minSwapAssetTokenAmount, _calldata, stableReturnBps)


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
