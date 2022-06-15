import json

import requests

def refactor_json_file(filepath: str):
    with open(filepath, "r") as infile:
        data = json.loads(infile.read())
    with open(filepath, "w") as outfile:
        outfile.write(json.dumps(data, indent=2))


if __name__ == "__main__":
    r = requests.get("https://alpaca-static-api.alpacafinance.org/bsc/v1/landing/summary.json")