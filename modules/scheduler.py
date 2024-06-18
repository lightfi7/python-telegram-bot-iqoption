import time
import pytz
import threading
from datetime import datetime, time as time_t, timedelta
from lang import translate
from modules.telegram import send_message
from modules.tron import tron_client
from modules.database import find_many, delete_one, find_one, db, update_one, insert_many, update_many
from modules.iqoption import Iqoption


def buy_order(task):
    return Iqoption(task)


def scheduled():
    tasks = find_many('tasks', {"checked": False})
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
            update_one('tasks', {'_id': task['_id']}, {'checked': True})
            threading.Thread(target=buy_order, args=[task]).start()
        elif scheduled_datetime < current_datetime_without_tz - timedelta(minutes=30):
            delete_one('tasks', {'_id': task['_id']})


def schedule_checker():
    while True:
        scheduled()
        time.sleep(2)


def deposit_callback(transactions):
    try:
        print(transactions)
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
            insert_many('deposits', transactions_)
            for transaction in transactions_:
                uid = _transaction['uid']
                value = float(transaction['value']) / 1000000
                user = find_one('users', {'id': uid})

                if user['subscription']['status'] == 'active':
                    update_one('users', {'id': uid}, {
                        'balance': value + user['balance'],
                    })
                    continue
                today = datetime.today()
                if value >= annual_price:
                    # annual period add
                    next_payment = today + timedelta(days=365)
                    update_one('users', {'id': uid}, {
                        'subscription': {
                            'status': 'active',
                            'plan': 'annual',
                            'start_date': today.strftime('%Y-%m-%d'),
                            'next_payment': next_payment.strftime('%Y-%m-%d'),
                        },
                        'balance': value - annual_price + user['balance'],
                    })
                    # send msg
                    msg = f'{translate("subscribed", user["language"])}'.format('annual')
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'parse_mode': 'markdown',
                    }
                    send_message(json)
                elif value >= monthly_price:
                    # monthly period add
                    next_payment = today + timedelta(days=30)
                    update_one('users', {'id': uid}, {
                        'subscription': {
                            'status': 'active',
                            'plan': 'monthly',
                            'start_date': today.strftime('%Y-%m-%d'),
                            'next_payment': next_payment.strftime('%Y-%m-%d'),
                        },
                        'balance': value - monthly_price + user['balance'],
                    })
                    # send msg
                    msg = f'{translate("subscribed", user["language"])}'.format('monthly')
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'parse_mode': 'markdown',
                    }
                    send_message(json)

                parent_user = find_one('users', {'id': user['parent']})
                if parent_user is not None:
                    # plus user's expiration date
                    if parent_user['subscription']['next_payment'] is not None:
                        next_payment = datetime.strptime(parent_user['subscription']['next_payment'], "%Y-%m-%d").date()
                    else:
                        next_payment = datetime.today()
                    next_payment += timedelta(days=3)
                    if parent_user['subscription']['status'] == 'deactive':
                        update_one('users', {'id': parent_user['id']}, {
                            'subscription.status': 'active',
                        })
                    update_one('users', {'id': parent_user['id']}, {
                        'subscription.next_payment': next_payment.strftime("%Y-%m-%d"),
                    })

        pass
        # end
    except Exception as e:
        print(e)


def wallet_checker():
    while True:
        try:
            wallets = db['users'].find().sort('_id', -1).skip(0).limit(1000).distinct('wallet')
            admin_wallet = find_one('config', {'name': 'wallet'})
            if admin_wallet is not None:
                admin_wallet = admin_wallet['value']
                for wallet in wallets:
                    trx_balance = tron_client.get_balance(wallet['base58check_address'])
                    trc20_balance = tron_client.get_trc20_balance(wallet['base58check_address'])
                    admin_trx_balance = tron_client.get_balance(admin_wallet['base58check_address'])
                    # check
                    if trc20_balance > 0:
                        if trx_balance < 40:
                            if admin_trx_balance < 40 - trx_balance:
                                continue
                            tron_client.send_trx(wallet['base58check_address'], 40 - trx_balance,
                                                 admin_wallet['base58check_address'],
                                                 admin_wallet['private_key'])
                        tron_client.send_usdt(admin_wallet['base58check_address'], trc20_balance,
                                              wallet['base58check_address'],
                                              wallet['private_key'])
                        print(f'{wallet["base58check_address"]}, {trc20_balance}')
                    else:
                        # if trx_balance > 2:
                        #     tron_client.send_trx(admin_wallet['base58check_address'], trx_balance - 1.1, wallet['base58check_address'],
                        #                       wallet['private_key'])
                        # elif trx_balance >= 0.002:
                        #     tron_client.send_trx(admin_wallet['base58check_address'], trx_balance - 0.001, wallet['base58check_address'],
                        #                       wallet['private_key'])
                        print(f'{wallet["base58check_address"]}, {trx_balance}')
                    time.sleep(1)
        except Exception as e:
            print(e)
        time.sleep(60 * 5)


def payment_checker():
    while True:
        try:
            # membership checker
            update_many('users', {
                'subscription.next_payment': {
                    '$lt': datetime.today().strftime('%Y-%m-%d')
                }
            }, {
                'subscription.status': 'deactive',
                'started': False
            }, False)
            # new payment checker
            users = find_many('users', {})
            wallets = []
            for user in users:
                wallet = user['wallet']
                wallet['uid'] = user['id']
                wallets.append(wallet)
            tron_client.monitor_deposits(wallets, deposit_callback)
        except Exception as e:
            print(e)
        time.sleep(60 * 15)


def start():
    threading.Thread(target=schedule_checker, args=(), daemon=True).start()
    threading.Thread(target=payment_checker, args=(), daemon=True).start()
    threading.Thread(target=wallet_checker, args=(), daemon=True).start()
    pass
