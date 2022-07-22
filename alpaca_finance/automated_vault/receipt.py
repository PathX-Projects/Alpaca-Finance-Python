from .oracle import get_eth_price

from dataclasses import dataclass
from hexbytes import HexBytes

@dataclass
class TransactionReceipt:
    """
    Dataclass to model the important receipt return parameters from the Web3.eth.wait_for_transaction_receipt()
    https://web3py.readthedocs.io/en/stable/web3.eth.html#web3.eth.Eth.wait_for_transaction_receipt
    """
    transactionHash: HexBytes  # Access the string by using transactionHash.hex()
    blockHash: HexBytes  # Access the string by using blockHash.hex()
    blockNumber: int
    contractAddress: str
    cumulativeGasUsed: int
    gasSpendUSD: str
    fromAddress: str
    toAddress: str
    status: int
    transactionIndex: int
    type: str
    effectiveGasPrice: int = None


def build_receipt(d: dict) -> TransactionReceipt:
    """
    Prepare the Web3 transaction receipt dictionary to map to the TransactionReceipt class
    :param d: Transaction receipt JSON data as returned by Web3.eth.wait_for_transaction_receipt():
              https://web3py.readthedocs.io/en/stable/web3.eth.html#web3.eth.Eth.wait_for_transaction_receipt
    :return: TransactionReceipt class to model the transaction
    """
    # Account for "from" being unable to map:
    if "from" in d.keys():
        d['fromAddress'] = d.pop("from")
    if "to" in d.keys():
        d['toAddress'] = d.pop("to")

    # Calculate gas price in USD
    if "gasUsed" in d.keys():
        #                  Convert from GWEI to ETH, then mutliply by ETH price:
        d['gasSpendUSD'] = (d.pop('gasUsed') * 0.000000001) * get_eth_price()

    # Clean logs - will not be used:
    for key in d.copy().keys():
        if key.startswith("logs"):
            d.pop(key)

    return TransactionReceipt(**d)

