
<!-- PROJECT HEADER -->
<div align="center">
  <a href ="https://www.alpacafinance.org//"><img src="https://pbs.twimg.com/profile_images/1481749291379081217/KGzK2UQS_400x400.png" alt="Alpaca Finance Logo" height="200"></a>
  <br></br>
  <h2 align="center"><strong>Alpaca-Finance-Python</strong></h2>
  <img src="https://img.shields.io/badge/Python-3.9%2B-yellow"/>&nbsp&nbsp<img src="https://img.shields.io/badge/Chain-BSC-yellow"></img>
    <p align="center">
        An unofficial Python3.9+ package that models positions on the Alpaca Finance platform to simplify interaction with their smart contracts in your Python projects.
    </p>
    <h3><strong>Supported Position Types</strong></h3>
    <i>Automated Vaults</i><br>
</div>
<br>

> NOTE: Codebase is currently in development and incomplete

<!-- TABLE OF CONTENTS -->
### Table of Contents
<details>
  <ol>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#uninstallation">Uninstallation</a></li>
    <!-- <li><a href="#roadmap">Roadmap</a></li> -->
  </ol>
</details>

___

## Installation

This package is set up to be installed using the `pip` package manager.

1. Install the package using pip (you must use the git+url as this project is private and not listed on PyPi):
    ```bash
    pip install git+https://github.com/PathX-Projects/Alpaca-Finance-Python.git
    ```

    ***Note:*** You may need to provide your git credentials depending on the repository privacy settings. In the event, if you need help generating a personal access token see [here](https://catalyst.zoho.com/help/tutorials/githubbot/generate-access-token.html)

2. After install, the package will be available to you in your local Python environment as ***alpaca_finance***

When updates are made to the package, the version will automatically be incremented so that in order to get the newest version on your end, you can simply use the same installation command and your pip will detect and update to the newest version.

___

## Usage

How to use the package:

1. Import the package into your Python script:
    ```python
    from alpaca_finance.positions import AutomatedVaultPosition
    ```

2. ***(Optional)*** Create your Web3 provider object to interact with the network (By default, the BSC RPC URL is used):
    ```python
    from alpaca_finance.util import get_web3_provider

    provider = get_provider("your_rpc_url")
    ```

### Automated Vaults:

3. Creating an [AutomatedVaultPosition](alpaca_finance/positions.py) instance requires the following:
    - Your position key (string)
        - This key should match your position key on Alpaca Finance's webapp
        - ![demo](img/demo.png)
  
    - Your public wallet key (string)

    - ***(Optional)*** Your private wallet key (string)
        - Your private key is required to sign transactions, but can be left as None if you are only going to be using the informational methods.

    Once you've gathered all of these variables, you can create the position instance like this example below:
    ```python
    position = AutomatedVaultPosition(position_key="n3x-BNBBUSD-PCS1", owner_wallet_address="0x...", owner_private_key="123abc456efg789hij...")
    ```
4. Use your position instance to interact with Alpaca Finance:
    ```python
    """ Informational Methods (Private Key not Required) """

    # Get the current yields for the vault:
    position.yields()

    # Get the current vault TVL:
    position.tvl()

    # Get the current vault capacity:
    position.capacity()

    # get the full vault summary (See the documentation alpaca_fiance/positions.py for more details):
    position.get_vault_summary()
    ```

___

## Uninstallation:

Uninstall the package like any other Python package using the pip uninstall command:
```bash
pip uninstall alpaca-finance
```

## Contributions:

*Coming soon...*