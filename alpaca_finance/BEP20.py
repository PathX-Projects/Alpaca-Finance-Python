from .util import get_contract_instance


class BEP20Token:
    def __init__(self, token_address):
        self.contract = get_contract_instance(token_address, "BEP20Token.json")
        self.decimals = self.contract.functions.pas

    def approve
