from setuptools import setup
import sys

from alpaca_finance import __version__

if sys.version_info < (3, 9):
    sys.exit('Python 3.9+ required to install this package. Install it here: https://www.python.org/downloads/')

setup(
    name='alpaca_finance',
    version=__version__,
    author='Harrison Schick',
    author_email='hschickdevs@gmail.com',
    description='An unofficial Python3.9+ package that models positions on the Alpaca Finance platform to simplify interaction with their smart contracts in your Python projects.',
    url='https://github.com/PathX-Projects/Alpaca-Finance-Python',
    # license='MIT',
    packages=['alpaca_finance'],
    include_package_data=True,
    install_requires=[line.strip() for line in open('requirements.txt').readlines()],
)