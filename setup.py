from setuptools import setup, find_packages
import sys

from alpaca_finance import __version__

if sys.version_info < (3, 9):
    sys.exit('Python 3.9+ required to install this package. Install it here: https://www.python.org/downloads/')


def readme():
    with open("README.md") as infile:
        return infile.read().strip()


setup(
    name='alpaca_finance',
    version=__version__,
    author='Harrison Schick',
    author_email='hschickdevs@gmail.com',
    description='An unofficial Python3.9+ package that models positions on the Alpaca Finance platform to simplify interaction with their smart contracts in your Python projects.',
    long_description=readme(),
    long_description_content_type="text/markdown",
    url='https://github.com/PathX-Projects/Alpaca-Finance-Python',
    # license='MIT',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[line.strip() for line in open('requirements.txt').readlines()],
)