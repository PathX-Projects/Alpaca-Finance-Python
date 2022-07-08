from setuptools import setup, find_packages
import sys

if sys.version_info < (3, 9):
    sys.exit('Python 3.9+ required to install this package. Install it here: https://www.python.org/downloads/')

setup(
    name='alpaca_finance',
    version='0.0.1',
    author='Harrison Schick',
    author_email='hschickdevs@gmail.com',
    description='An unofficial Python3.9+ package that models positions on the Alpaca Finance platform to simplify interaction with their smart contracts in your Python projects.',
    url='https://github.com/PathX-Projects/Alpaca-Finance-Python',
    # license='MIT',
    packages=['alpaca_finance'],
    include_package_data=True,
    install_requires=[line.strip() for line in open('requirements.txt').readlines()],
)