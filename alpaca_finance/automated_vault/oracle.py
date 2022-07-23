import requests


def get_eth_price() -> float:
    """Returns the realtime price of ETH in USD"""
    return float(requests.get("https://api.binance.com/api/v3/avgPrice?symbol=ETHUSDT").json()["price"])