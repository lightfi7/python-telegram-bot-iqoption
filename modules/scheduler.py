import time
import threading
from datetime import datetime, time as time_t, timedelta

from modules.tron import tron_client
from modules.database import find_many, delete_one, find_one, db
from modules.iqoption import Iqoption


def buy_order(task):
    return Iqoption(task)


def scheduled(pytz=None):
    tasks = find_many('tasks', {})
    n = 0
    for task in tasks:
        n += 1
        utc_offset = task['utc_offset']
        scheduled_time_str = task['time']
        hour, minute = map(int, scheduled_time_str.split(':'))
        time_zone = pytz.timezone(f'Etc/GMT+{utc_offset}')

        current_datetime = datetime.now(time_zone)
        scheduled_datetime = datetime.combine(current_datetime.date(), time_t(hour, minute), tzinfo=time_zone)
        current_datetime_without_tz = datetime(current_datetime.year, current_datetime.month, current_datetime.day,
                                               current_datetime.hour, current_datetime.minute, current_datetime.second,
                                               tzinfo=time_zone)

        if scheduled_datetime == current_datetime_without_tz:
            threading.Thread(target=buy_order, args=[task]).start()
        elif scheduled_datetime < current_datetime_without_tz - timedelta(minutes=30):
            delete_one('tasks', {'_id': task['_id']})


def schedule_checker():
    while True:
        scheduled()
        time.sleep(1)


def deposit_callback(transactions):
    try:
        cfg = find_one('config', {'name': 'annual'})
        annual_price = cfg['value']
        cfg = find_one('config', {'name': 'monthly'})
        monthly_price = cfg['value']

        # should complete
        hash_list = db['deposits'].distinct('transaction_id', {
            'sort': [('created_at', -1)],
            'skip': 0,
            'limit': 5000
        })

        for _transaction in transactions:
            transactions_ = filter(lambda x: x['transaction_id'] not in hash_list, _transaction['data'])
            for transaction in transactions_:
                value = transaction['value'] / 1000000
                if value == annual_price:
                    # annual period add
                    pass
                elif value == monthly_price:
                    # monthly period add
                    pass
            pass

        # end
    except Exception as e:
        print(e)


def payment_checker():
    while True:
        try:
            users = find_many('users', {})

            wallets = []
            for user in users:
                wallet = user['wallet']
                print(wallet)
                wallet['uid'] = user['id']
                wallets.append(wallet)
                pass
            print(wallets)
            tron_client.monitor_deposits(wallets, deposit_callback)
        except Exception as e:
            print(e)
        time.sleep(3600)


def start():
    threading.Thread(target=schedule_checker, args=()).start()
    threading.Thread(target=payment_checker, args=()).start()
