import time
import multiprocessing
from iqoptionapi.stable_api import IQ_Option

from lang import translate
from modules.database import find_one, delete_one
from modules.telegram import send_message


class Iqoption:
    def __init__(self, task):
        self.uid = task['uid']
        user = find_one('users', {'id': self.uid})
        if not user:
            print(f'not found a user: {self.uid}')
            return

        account = user.get('settings', {}).get('account', {})
        if not account.get('email') or not account.get('password'):
            send_message({
                'chat_id': self.uid,
                'text': f'{translate("account_credentials_not_found", user["language"])}'
            })
            return

        mode = 'REAL' if user['settings']['account']['type'] == 0 else 'PRACTICE'
        self.task = task
        self.user = user
        self.email = account['email']
        self.symbol = task['symbol']
        self.amount = task['amount']
        self.amount_type = task['amount_type']
        self.mode = mode
        self.duration = 5
        self.option = task['option']
        self.password = account['password']
        self.process = multiprocessing.Process(target=self.connect)
        self.process.start()

    def connect(self):
        self.API = IQ_Option(self.email, self.password)

        self.API.connect()
        n = 0
        while True:
            if n > 2:
                print('Connection error')
                return False, None, None
            if self.API.check_connect():
                print(f'Connected to {self.email}')
                break
            else:
                print(f'Failed to connect to {self.email}')
            n += 1
            time.sleep(2)
        self.API.change_balance(self.mode)
        balance = self.API.get_balance()

        amount = self.amount

        if self.amount_type == 1:
            amount = int(int(balance) * self.amount / 100.0)
        else:
            amount = int(amount)

        martin_gale = 0

        while martin_gale <= int(self.user['settings']['strategy']):

            if martin_gale == 1:
                amount *= 1.5
                scheduled_time_str = self.task['second_time']
            elif martin_gale == 2:
                amount *= 1.75
                scheduled_time_str = self.task['third_time']

            buy_check, id = (self.API.buy_digital_spot(self.symbol, amount, self.option, self.duration))
            print(id, buy_check)

            if not buy_check:
                send_message({
                    'chat_id': self.uid,
                    'text': f'{translate("trade_unsuccessful", self.user["language"])}'.format(self.task['symbol']),
                })
                break
            else:
                while True:
                    check, win = self.API.check_win_digital_v2(id)
                    if check:
                        break
                if win < 0:
                    print("Loss " + str(win) + "$")
                    if martin_gale == int(self.user['settings']['strategy']):
                        msg = 'LOSS🔻'
                        msg = f'{translate("trade_success", self.user["language"])}'.format('LOSS',
                                                                                                          f'{win:6.2f}')
                        # send_message({
                        #     'chat_id': self.uid,
                        #     'text': msg
                        # })
                    martin_gale += 1
                else:
                    print("Win " + str(win) + "$")
                    msg = ''
                    if martin_gale == 0:
                        msg = 'Direct WIN ✅'
                        msg = f'{translate("trade_success", self.user["language"])}'.format('WIN',
                                                                                                          f'{win:6.2f}')
                    elif martin_gale == 1:
                        msg = 'WIN GALE 1 ✅'
                        msg = f'{translate("trade_success", self.user["language"])}'.format('WIN',
                                                                                                          f'{win:6.2f}')
                    elif martin_gale == 2:
                        msg = 'WIN GALE 2 ✅'
                        msg = f'{translate("trade_success", self.user["language"])}'.format('WIN',
                                                                                                          f'{win:6.2f}')
                    send_message({
                        'chat_id': self.uid,
                        'text': msg
                    })
                    break

        delete_one('tasks', {'_id': self.task['_id']})
