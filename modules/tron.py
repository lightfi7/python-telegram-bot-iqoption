import requests
from tronpy import Tron
from tronpy.keys import PrivateKey
from datetime import datetime, timedelta
import time

TRONWEB_API_KEY = "your_api_key_here"
# USDT_CONTRACT_ADDRESS = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # Ensure this is correct for the network you're using
USDT_CONTRACT_ADDRESS = "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj"  # Ensure this is correct for the network you're using


class TronClient:
    def __init__(self):
        self.tron = Tron(network='nile')
        self.private_key = None

    def set_private_key(self, private_key):
        self.private_key = private_key

    def create_wallet(self):
        try:
            account = self.tron.generate_address()
            return account
        except Exception as e:
            print(f"Failed to create a new Tron wallet: {e}")
            return None

    def get_trc20_balance(self, address):
        try:
            contract = self.tron.get_contract(USDT_CONTRACT_ADDRESS)
            balance = contract.functions.balanceOf(address) / 10 ** 6
            return balance
        except Exception as e:
            print(f"Error getting TRC20 balance: {e}")

    def get_balance(self, address):
        try:
            balance = self.tron.get_account_balance(address)
            return balance
        except Exception as e:
            print(e)
            return None

    def send_trx(self, to_address, amount, from_address, from_private_key):
        try:
            private_key = PrivateKey(bytes.fromhex(from_private_key))
            token_decimals = 6
            amount_with_decimals = int(amount * (10 ** token_decimals))
            txn = (
                self.tron.trx.transfer(from_address, to_address, amount_with_decimals)
                .memo('')
                .build()
                .sign(private_key)

            )
            receipt = txn.broadcast().wait()
            print("Transaction receipt:", receipt)
            return True
        except Exception as e:
            print(f"Error sending TRX: {e}")
            return False

    def send_usdt(self, to_address, amount, from_address, from_private_key):
        try:
            token_decimals = 6
            amount_with_decimals = int(amount * (10 ** token_decimals))
            private_key = PrivateKey(bytes.fromhex(from_private_key))
            contract = self.tron.get_contract(USDT_CONTRACT_ADDRESS)
            txn = (
                contract.functions.transfer(to_address, amount_with_decimals)
                .with_owner(from_address)
                .fee_limit(40000000)
                .build()
                .sign(private_key)
            )
            receipt = txn.broadcast().wait()
            print("Transaction receipt:", receipt)
            return receipt
        except Exception as e:
            print(f"Error sending USDT: {e}")
            return e

    def request_transactions(self, wallet_address, min_timestamp, max_timestamp, limit=100):
        url = f"https://api.trongrid.io/v1/accounts/{wallet_address}/transactions/trc20?contract_address={USDT_CONTRACT_ADDRESS}&only_to=true&only_confirmed=true&limit={limit}&min_timestamp={min_timestamp}&max_timestamp={max_timestamp}"
        headers = {"accept": "application/json"}

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "data": [],
                    "success": False,
                    "meta": {
                        "at": datetime.now().timestamp(),
                        "page_size": 0,
                    },
                }
        except Exception as e:
            print(f"Error fetching transactions: {e}")
            return {
                "data": [],
                "success": False,
                "meta": {
                    "at": datetime.now().timestamp(),
                    "page_size": 0,
                },
            }

    def remove_duplicates(self, transactions):
        seen_items = set()
        new_list = []

        for obj in transactions:
            if obj["transaction_id"] not in seen_items:
                new_list.append(obj)
                seen_items.add(obj["transaction_id"])

        return new_list

    def get_transactions(self, wallet_address, min_timestamp, max_timestamp):
        transactions = []
        has_more = True
        last_timestamp = max_timestamp

        while has_more:
            res = self.request_transactions(wallet_address, min_timestamp, last_timestamp)
            transactions.extend(res.get("data", []))
            if res.get("data") and len(res["data"]) > 0:
                last_timestamp = res["data"][-1]["block_timestamp"]
                has_more = len(res["data"]) == 100  # Assuming 100 is the limit per request
            else:
                has_more = False

        transactions = self.remove_duplicates(transactions)
        return transactions

    def monitor_deposits(self, wallets, cb):
        transactions = []
        for w in wallets:
            st = datetime.now() - timedelta(hours=6)
            et = datetime.now()
            min_timestamp = int(st.timestamp() * 1000)
            max_timestamp = int(et.timestamp() * 1000)
            wallet_address = w["base58check_address"]
            transactions_ = self.get_transactions(wallet_address, min_timestamp, max_timestamp)
            transactions.append({
                "uid": w["uid"],
                "data": [transaction for transaction in transactions_ if transaction["to"] == wallet_address],
            })
            time.sleep(0.8)
        if cb:
            cb(transactions)


tron_client = TronClient()
