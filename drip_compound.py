from web3 import Web3
import os
import logging
import sys
import time
#from settings import *
from utils import eth2wei, wei2eth, pancakeswap_api_get_price, read_json_file, to_checksum


DRIP_TOKEN_ADDRESS = "0xFFE811714ab35360b67eE195acE7C10D93f89D8C"
DRIP_FAUCET_ABI_FILE = "./abis/Faucet.json"
VERSION = '0.2'

class DripCompundClass:
    def __init__(self, private_key, txn_timeout=120, gas_price=5, rpc_host="https://bsc-dataseed.binance.org:443",min_balance=0.015,rounding=3):
        self.private_key = private_key
        self.rounding = rounding
        self.min_balance = min_balance
        self.txn_timeout = txn_timeout
        self.gas_price = gas_price
        self.rpc_host = rpc_host
        # Initialize web3, and load the smart contract objects.
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_host))
        self.account = self.w3.eth.account.privateKeyToAccount(self.private_key)
        self.address = self.account.address
        self.w3.eth.default_account = self.address

        self.drip_contract = self.w3.eth.contract(
            to_checksum(DRIP_TOKEN_ADDRESS), 
            abi=read_json_file(DRIP_FAUCET_ABI_FILE))

        self.getDripBalance()
        self.getAvailableClaims()
        self.getBNBbalance()
        self.checkAvailableBNBBalance()

    def getDripBalance(self):
        self.userInfo = self.drip_contract.functions.userInfo(self.address).call()
        self.DripBalance = round(wei2eth((self.userInfo[2])),self.rounding)

    def getAvailableClaims(self):
        self.claimsAvailable = round(wei2eth(self.drip_contract.functions.claimsAvailable(self.address).call()),self.rounding)

    def getBNBbalance(self):
        self.BNBbalance = self.w3.eth.getBalance(self.address)
        self.BNBbalance = round(wei2eth(self.BNBbalance),self.rounding)

    def checkAvailableBNBBalance(self):
        if self.BNBbalance > self.min_balance:
            logging.info('BNB Balance is %s' % round(self.BNBbalance,self.rounding))
        else:
            logging.info('Your current BNB balance(%s) is below min required (%s)' % (self.BNBbalance, self.min_balance))
            sys.exit()
    
    def nonce(self):
        return self.w3.eth.getTransactionCount(self.address)            

    def compundDrip(self):        
        tx = self.drip_contract.functions.roll().buildTransaction({
                            "gasPrice": eth2wei(self.gas_price, "gwei"), "nonce": self.nonce()})

        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        txn = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        logging.info("Transaction: %s" % (self.w3.toHex(txn)))
        time.sleep(5)
        self.getDripBalance()
        logging.info("Updated Drip balance is: %s" % self.DripBalance)


def main():
    # Setup logger.
    log_format = '%(asctime)s: %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format, stream=sys.stdout)
    logging.info('Dripping Work v%s Started!' % VERSION)
    logging.info('----------------')
    #logging.info('Strategy: %s.' % ACTION_LIST)

    MANDATORY_ENV_VARS = ["PRIVATE_KEY"]

    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            raise EnvironmentError("Failed because {} is not set.".format(var))

    PRIVATE_KEY = os.environ['PRIVATE_KEY']
        
    drip1wallet = DripCompundClass(private_key=PRIVATE_KEY)

    logging.info("Current Balance %s" % drip1wallet.DripBalance)
    logging.info("Available to compund %s" % drip1wallet.claimsAvailable)

    # Actually do the compound step
    #drip1wallet.compundDrip()


main()



