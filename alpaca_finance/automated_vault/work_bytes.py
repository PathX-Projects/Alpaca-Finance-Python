from dataclasses import dataclass
from eth_abi import encode_abi


@dataclass
class WithdrawWorkByte:
    posId: int
    vaultAddress: str
    workerAddress: str
    partialCloseMinimizeStrat: str  # expects partialCloseMinimizeStrat.address
    debt: int
    maxLpTokenToLiquidate: int
    maxDebtRepayment: int
    minFarmingToken: int

    def build(self) -> bytes:
        return encode_abi(
            ["address", "uint256", "address", "uint256", "uint256", "uint256", "bytes"],
            [self.vaultAddress,
             self.posId,
             self.workerAddress,
             0, 0,
             self.debt,
             encode_abi(
                 ["address", "bytes"],
                 [
                     self.partialCloseMinimizeStrat,
                     encode_abi(
                         ["uint256", "uint256", "uint256"],
                         [self.maxLpTokenToLiquidate, self.maxDebtRepayment, self.minFarmingToken]
                     )]
             )]
        )


@dataclass
class DepositWorkByte:
    pass