import os
import re
from datetime import datetime, timedelta

from modules.cache import cached, cache_up, cache
from lang import translate
from modules.database import insert_one, find_one, update_one
from modules.tron import tron_client
from modules.telegram import send_message, answer_callback_query, edit_message, delete_message, copy_message
from modules.utils import is_number, is_valid_email, generate_key, verify_key

ADMIN_USER_ID = os.getenv('ADMIN_USER_ID', 6343801713)


def parse_data(data):
    if 'callback_query' in data:
        return 'callback_query', data['callback_query']
    elif 'result' in data:
        return 'result', data['result']
    elif 'channel_post' in data:
        return 'channel_post', data['channel_post']
    elif 'message' in data:
        return 'message', data['message']
    elif 'subscription' in data:
        return 'subscription', data['subscription']
    return None, data


def parse_channel_post(data):
    pattern = r'(?:UTC -(\d+)\n\n)?(\w+/\w+(?:-OTC)?);(\d+:\d+);(\w+)\s(🟥|🟩)\n\n👇🏼Em caso de loss👇🏼\n\n1º Proteção ; (\d+:\d+)\n2º Proteção ; (\d+:\d+)'

    match = re.search(pattern, data)

    if match:
        utc_offset = match.group(1)
        symbol = match.group(2)
        first_time = match.group(3)
        option = match.group(4)
        second_time = match.group(6)
        third_time = match.group(7)

        return utc_offset, symbol, first_time, option, second_time, third_time
    else:
        return None, None, None, None, None, None


def generate_response(data):
    uid = ''
    t, query = parse_data(data)
    try:
        if t == 'callback_query':
            [callback_type, callback_data] = query['data'].split('>')
            uid = query['from']['id']
            user = cached(uid, {
                'id': uid,
                'username': query['from']['username'],
                'language': 'en',
                'team_count': 0,
                'subscription': {
                    'status': 'deactive',
                    'plan': None,
                    'start_date': None,
                    'next_payment': None,
                },
                'settings': {
                    'account': {
                        'type': None,
                        'email': None,
                        'password': None,
                    },
                    'amount': {
                        'type': 0,
                        'value': 10
                    },
                    'strategy': 0
                },
                'last_action': None,
                'perm': 'guest',
                'started': False,
                'balance': 0
            })
            answer_callback_query({
                'callback_query_id': query['id'],
                'text': '😊'
            })
            if callback_type == '#option':
                if callback_data == '@start':
                    # check subscription
                    if user['subscription']['status'] != 'active' or user['perm'] != 'user':
                        msg = f'{translate("no_subscription", user["language"])}'
                        json = {
                            'chat_id': uid,
                            'text': msg,
                        }
                        return send_message(json)
                    # check account
                    if user['settings']['account']['type'] is None or user['settings']['account']['email'] is None or \
                            user['settings']['account']['password'] is None:
                        msg = f'{translate("register_account", user["language"])}'
                        json = {
                            'chat_id': uid,
                            'text': msg,
                        }
                        return send_message(json)
                    # check amount, strategy
                    amount = f'{user["settings"]["amount"]["value"]}{"%" if user["settings"]["amount"]["type"] == 1 else ""}'
                    strategy = translate('without_martin_gale', user['language'])
                    if user['settings']['strategy'] == 1:
                        strategy = translate('martin_gale_1', user['language'])
                    elif user['settings']['strategy'] == 2:
                        strategy = translate('martin_gale_2', user['language'])
                    msg = (f'Trading amount: {amount}\n'
                           f'Trading strategy: {strategy}\n'
                           f'Do you want to start bot?')
                    keyboard = [
                        [{'text': opt['label'], 'callback_data': f'{opt["value"]}'} for opt in opts]
                        for opts in [
                            [{'label': translate('yes', user['language']),
                              'value': '#confirm>@yes'},
                             {'label': translate('no', user['language']),
                              'value': '#option>@back_to_main'}
                             ]
                        ]
                    ]
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'message_id': query['message']['message_id'],
                        'reply_markup': {
                            'inline_keyboard': keyboard
                        }
                    }
                    user['last_action'] = 'start'
                    u = cache_up(uid, user)
                    edit_message(json)
                    pass
                elif callback_data == '@stop':
                    # yes/no
                    msg = f'Do you want to stop bot?'
                    keyboard = [
                        [{'text': opt['label'], 'callback_data': f'{opt["value"]}'} for opt in opts]
                        for opts in [
                            [{'label': translate('yes', user['language']),
                              'value': '#confirm>@yes'},
                             {'label': translate('no', user['language']),
                              'value': '#option>@back_to_main'}
                             ]
                        ]
                    ]
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'message_id': query['message']['message_id'],
                        'reply_markup': {
                            'inline_keyboard': keyboard
                        }
                    }
                    user['last_action'] = 'stop'
                    u = cache_up(uid, user)
                    edit_message(json)
                    pass
                elif callback_data == '@settings':
                    msg = f' {translate("welcome", user["language"])}'
                    keyboard = [
                        [{'text': opt['label'], 'callback_data': f'#option>{opt["value"]}'}]
                        for opt in [
                            {'label': f'{translate("account", user["language"])}', 'value': '@account'},
                            {'label': f'{translate("amount", user["language"])}', 'value': '@amount'},
                            {'label': f'{translate("strategy", user["language"])}', 'value': '@strategy'},
                            {'label': f'{translate("back", user["language"])}', 'value': '@back_to_main'},
                        ]
                    ]
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'message_id': query['message']['message_id'],
                        'reply_markup': {
                            'inline_keyboard': keyboard
                        }
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    edit_message(json)
                    pass
                elif callback_data == '@subscribe':
                    msg = ''
                    if user['subscription']['status'] == 'active':
                        msg += f'{translate("subscription_expiry", user["language"])}\n'.format(
                            user['subscription']['plan'], user['subscription']['next_payment'])
                        pass
                    msg += f'{translate("choose_plan", user["language"])}'
                    keyboard = [
                        [{'text': opt['label'], 'callback_data': f'#option>{opt["value"]}'}]
                        for opt in [
                            {'label': f'{translate("monthly", user["language"])}', 'value': '@monthly'},
                            {'label': f'{translate("annual", user["language"])}', 'value': '@annual'},
                        ]
                    ]
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'reply_markup': {
                            'inline_keyboard': keyboard
                        }
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    send_message(json)
                    pass
                elif callback_data == '@monthly':
                    wallet = None
                    if 'wallet' in user:
                        wallet = user['wallet']
                    else:
                        wallet = tron_client.create_wallet()
                        user['wallet'] = wallet
                        u = cache_up(uid, user)
                    # get price from database,
                    cfg = find_one('config', {'name': 'monthly'})
                    price = cfg['value']
                    msg = f'{translate("deposit", user["language"])}'.format('monthly', price,
                                                                             wallet['base58check_address'])
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'parse_mode': 'markdown'
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    send_message(json)
                    pass
                elif callback_data == '@annual':
                    wallet = None
                    if 'wallet' in user:
                        wallet = user['wallet']
                    else:
                        wallet = tron_client.create_wallet()
                        user['wallet'] = wallet
                        u = cache_up(uid, user)
                    # get price from database,
                    cfg = find_one('config', {'name': 'annual'})
                    price = cfg['value']
                    msg = f'{translate("deposit", user["language"])}'.format('annual', price,
                                                                             wallet['base58check_address'])
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'parse_mode': 'markdown'
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    send_message(json)
                    pass
                elif callback_data == '@redeem_code':
                    # Generate new redeem_code
                    msg = f' {translate("welcome", user["language"])}'
                    keyboard = [
                        [{'text': opt['label'], 'callback_data': f'#option>{opt["value"]}'}]
                        for opt in ([
                                        {'label': f'{translate("my_redeem_code", user["language"])}',
                                         'value': '@my_redeem_code'},
                                        {'label': f'{translate("register_redeem_code", user["language"])}',
                                         'value': '@register_redeem_code'},
                                    ] if 'parent' not in user else [
                            {'label': f'{translate("my_redeem_code", user["language"])}', 'value': '@my_redeem_code'}])
                    ]
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'reply_markup': {
                            'inline_keyboard': keyboard
                        }
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    send_message(json)
                    pass
                elif callback_data == '@my_redeem_code':
                    redeem_code = generate_key(f'{uid}')
                    json = {
                        'chat_id': uid,
                        'text': f'`{redeem_code}`',
                        'parse_mode': 'markdown'
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    send_message(json)
                    pass
                elif callback_data == '@register_redeem_code':
                    json = {
                        'chat_id': uid,
                        'text': f'{translate("enter_promo_code", user["language"])}',
                    }
                    user['last_action'] = 'register_redeem_code'
                    u = cache_up(uid, user)
                    send_message(json)
                    pass
                elif callback_data == '@contact_admin':
                    json = {
                        'chat_id': uid,
                        'text': f' {translate("send_me_message", user["language"])}',
                    }
                    user['last_action'] = 'contact_admin'
                    u = cache_up(uid, user)
                    send_message(json)
                    pass
                elif callback_data == '@help':
                    json = {
                        'chat_id': uid,
                        'text': f'{translate("manual", user["language"])}',
                        'parse_mode': 'markdown'
                    }
                    send_message(json)
                    pass
                elif callback_data == '@account':
                    msg = f' {translate("welcome", user["language"])}'
                    keyboard = [
                        [{'text': opt['label'], 'callback_data': f'#option>{opt["value"]}'}]
                        for opt in [
                            {'label': f'{translate("real_account", user["language"])}', 'value': '@real_account'},
                            {'label': f'{translate("practice_account", user["language"])}',
                             'value': '@practice_account'},
                            {'label': f'{translate("back", user["language"])}', 'value': '@back_to_settings'},
                        ]
                    ]
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'reply_markup': {
                            'inline_keyboard': keyboard
                        }
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    send_message(json)
                    pass
                elif callback_data == '@amount':
                    msg = f' {translate("welcome", user["language"])}'
                    keyboard = [
                        [{'text': opt['label'], 'callback_data': f'#option>{opt["value"]}'}]
                        for opt in [
                            {'label': f'{translate("fix_amount", user["language"])}', 'value': '@fix_amount'},
                            {'label': f'{translate("percent_balance", user["language"])}',
                             'value': '@percent_balance'},
                            {'label': f'{translate("back", user["language"])}', 'value': '@back_to_settings'},
                        ]
                    ]
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'reply_markup': {
                            'inline_keyboard': keyboard
                        }
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    send_message(json)
                    pass
                elif callback_data == '@strategy':
                    msg = f' {translate("welcome", user["language"])}'
                    keyboard = [
                        [{'text': opt['label'], 'callback_data': f'#option>{opt["value"]}'}]
                        for opt in [
                            {'label': f'{translate("without_martin_gale", user["language"])}',
                             'value': '@without_martin_gale'},
                            {'label': f'{translate("martin_gale_1", user["language"])}',
                             'value': '@martin_gale_1'},
                            {'label': f'{translate("martin_gale_2", user["language"])}',
                             'value': '@martin_gale_2'},
                            {'label': f'{translate("back", user["language"])}', 'value': '@back_to_settings'},
                        ]
                    ]
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'reply_markup': {
                            'inline_keyboard': keyboard
                        }
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    send_message(json)
                    pass
                elif callback_data == '@real_account':
                    json = {
                        'chat_id': uid,
                        'text': f'{translate("set_account_type_real", user["language"])}',
                        'parse_mode': 'markdown'
                    }
                    user['last_action'] = 'account_email'
                    user['settings']['account']['type'] = 0
                    u = cache_up(uid, user)
                    send_message(json)
                    pass
                elif callback_data == '@practice_account':
                    json = {
                        'chat_id': uid,
                        'text': f'{translate("set_account_type_practice", user["language"])}',
                        'parse_mode': 'markdown'
                    }
                    user['last_action'] = 'account_email'
                    user['settings']['account']['type'] = 1
                    u = cache_up(uid, user)
                    send_message(json)
                    pass
                elif callback_data == '@fix_amount':
                    # amount
                    json = {
                        'chat_id': uid,
                        'text': f'{translate("enter_fix_amount", user["language"])}',
                    }
                    user['settings']['amount']['type'] = 0
                    user['last_action'] = 'amount_type_fix'
                    u = cache_up(uid, user)
                    send_message(json)
                    pass
                elif callback_data == '@percent_balance':
                    # amount
                    json = {
                        'chat_id': uid,
                        'text': f'{translate("enter_fix_amount", user["language"])}',
                    }
                    user['settings']['amount']['type'] = 1
                    user['last_action'] = 'amount_type_percent'
                    u = cache_up(uid, user)
                    send_message(json)
                    pass
                elif callback_data == '@without_martin_gale':
                    user['settings']['strategy'] = 0
                    u = cache_up(uid, user)
                    pass
                elif callback_data == '@martin_gale_1':
                    user['settings']['strategy'] = 1
                    u = cache_up(uid, user)
                    pass
                elif callback_data == '@martin_gale_2':
                    user['settings']['strategy'] = 2
                    u = cache_up(uid, user)
                    pass
                elif callback_data == '@back_to_main':
                    msg = f' {translate("welcome", user["language"])}'
                    keyboard = [
                        [{'text': opt['label'], 'callback_data': f'#option>{opt["value"]}'}]
                        for opt in [
                            {'label': f'{translate("start", user["language"])}', 'value': '@start'} if user[
                                                                                                           'started'] is False else {
                                'label': f'{translate("stop", user["language"])}', 'value': '@stop'},
                            {'label': f'{translate("settings", user["language"])}', 'value': '@settings'},
                            {'label': f'{translate("subscribe", user["language"])}', 'value': '@subscribe'},
                            {'label': f'{translate("redeem_code", user["language"])}', 'value': '@redeem_code'},
                            {'label': f'{translate("contact_admin", user["language"])}', 'value': '@contact_admin'},
                            {'label': f'{translate("help", user["language"])}', 'value': '@help'}
                        ]
                    ]
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'message_id': query['message']['message_id'],
                        'reply_markup': {
                            'inline_keyboard': keyboard
                        }
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    edit_message(json)
                    pass
                elif callback_data == '@back_to_settings':
                    msg = f' {translate("welcome", user["language"])}'
                    keyboard = [
                        [{'text': opt['label'], 'callback_data': f'#option>{opt["value"]}'}]
                        for opt in [
                            {'label': f'{translate("account", user["language"])}', 'value': '@account'},
                            {'label': f'{translate("amount", user["language"])}', 'value': '@amount'},
                            {'label': f'{translate("strategy", user["language"])}', 'value': '@strategy'},
                            {'label': f'{translate("back", user["language"])}', 'value': '@back_to_main'},
                        ]
                    ]
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'message_id': query['message']['message_id'],
                        'reply_markup': {
                            'inline_keyboard': keyboard
                        }
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    edit_message(json)
                    pass
            elif callback_type == '#confirm':
                if callback_data == '@yes':
                    msg = '😊'
                    if user['last_action'] == 'start':
                        user['started'] = True
                        msg = f'{translate("started", user["language"])}'
                    if user['last_action'] == 'stop':
                        user['started'] = False
                        msg = f'{translate("stopped", user["language"])}'
                    json = {
                        'chat_id': uid,
                        'text': msg,
                        'message_id': query['message']['message_id'],
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    edit_message(json)
                elif callback_data == '@no':
                    msg = f'{translate("stopped", user["language"])}'
                    json = {
                        'chat_id': uid,
                        'text': msg,
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    send_message(json)
        elif t == 'result':
            pass
        elif t == 'channel_post':
            for uid in cache.keys():
                user = cache[uid]
                if user['perm'] == 'guest' or user['started'] is not True:
                    continue
                # json = {
                #     'chat_id': uid,
                #     'from_chat_id': query['chat']['id'],
                #     'message_id': query['message_id'],
                # }
                # copy_message(json)
                utc_offset, symbol, first_time, option, second_time, third_time = parse_channel_post(query['text'])
                if utc_offset is None:
                    return
                msg = f'{symbol}\n{option}\nDIRECT:     {first_time}\nM.GALE1:  {second_time}\nM.GALE2:  {third_time}';
                json = {
                    'chat_id': uid,
                    'text': msg,
                }
                send_message(json)
                insert_one('tasks', {
                    'uid': uid,
                    'utc_offset': utc_offset,
                    'symbol': f'{symbol}'.replace('/', ''),
                    'amount': user['settings']['amount']['value'],
                    'amount_type': user['settings']['amount']['type'],
                    'time': first_time,
                    'second_time': second_time,
                    'third_time': third_time,
                    'option': option,
                    'martin_gale': 0,
                    'checked': False
                })
                # msg = f'{translate("scheduled", user["language"])}'.format(first_time, utc_offset)
                # send_message({
                #     'chat_id': uid,
                #     'text': msg
                # })
            pass
        elif t == 'message':
            uid = query['from']['id']
            text = query['text']
            user = cached(uid, {
                'id': uid,
                'username': query['from']['username'],
                'language': 'en',
                'team_count': 0,
                'subscription': {
                    'status': 'deactive',
                    'plan': None,
                    'start_date': None,
                    'next_payment': None,
                },
                'settings': {
                    'account': {
                        'type': None,
                        'email': None,
                        'password': None,
                    },
                    'amount': {
                        'type': 0,
                        'value': 10
                    },
                    'strategy': 0
                },
                'last_action': None,
                'perm': 'guest',
                'started': False,
                'balance': 0
            })
            if 'start' in text.lower():
                msg = f' {translate("welcome", user["language"])}'
                keyboard = [
                    [{'text': opt['label'], 'callback_data': f'#option>{opt["value"]}'}]
                    for opt in [
                        {'label': f'{translate("start", user["language"])}', 'value': '@start'} if user[
                                                                                                       'started'] is False else {
                            'label': f'{translate("stop", user["language"])}', 'value': '@stop'},
                        {'label': f'{translate("settings", user["language"])}', 'value': '@settings'},
                        {'label': f'{translate("subscribe", user["language"])}', 'value': '@subscribe'},
                        {'label': f'{translate("redeem_code", user["language"])}', 'value': '@redeem_code'},
                        {'label': f'{translate("contact_admin", user["language"])}', 'value': '@contact_admin'},
                        {'label': f'{translate("help", user["language"])}', 'value': '@help'}
                    ]
                ]
                json = {
                    'chat_id': uid,
                    'text': msg,
                    'reply_markup': {
                        'inline_keyboard': keyboard
                    }
                }
                user['last_action'] = None
                u = cache_up(uid, user)
                send_message(json)
            elif 'about' in text.lower():
                json = {
                    'chat_id': uid,
                    'text': f'{translate("description", user["language"])}',
                }
                user['last_action'] = None
                u = cache_up(uid, user)
                send_message(json)
                pass
            else:
                if user['last_action'] == 'amount_type_fix':
                    if not is_number(text):
                        json = {
                            'chat_id': uid,
                            'text': f'{translate("invalid_number", user["language"])}',
                            'parse_mode': 'markdown'
                        }
                        return send_message(json)
                    json = {
                        'chat_id': uid,
                        'text': f'{translate("fix_amount_set", user["language"])}'.format(text),
                        'parse_mode': 'markdown',
                    }
                    user['settings']['amount']['value'] = int(text)
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    return send_message(json)
                elif user['last_action'] == 'amount_type_percent':
                    if not is_number(text):
                        json = {
                            'chat_id': uid,
                            'text': f'{translate("invalid_number", user["language"])}',
                            'parse_mode': 'markdown'
                        }
                        return send_message(json)
                    json = {
                        'chat_id': uid,
                        'text': f'{translate("percent_balance_set", user["language"])}'.format(
                            text),
                        'parse_mode': 'markdown',
                    }
                    user['settings']['amount']['value'] = int(text)
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    return send_message(json)
                elif user['last_action'] == 'account_email':
                    if is_valid_email(text) is False:
                        json = {
                            'chat_id': uid,
                            'text': f'{translate("invalid_email", user["language"])}',
                            'parse_mode': 'markdown'
                        }
                        return send_message(json)
                    json = {
                        'chat_id': uid,
                        'text': f'{translate("register_email", user["language"])}',
                        'parse_mode': 'markdown'
                    }
                    user['last_action'] = 'account_password'
                    user['settings']['account']['email'] = text
                    u = cache_up(uid, user)
                    return send_message(json)
                elif user['last_action'] == 'account_password':
                    if user['settings']['account']['email'] is not None:
                        user['settings']['account']['password'] = text
                    else:
                        json = {
                            'chat_id': uid,
                            'text': f'{translate("account_not_found", user["language"])}\n{translate("enter_account_email", user["language"])}'
                        }
                        user['last_action'] = 'account_email'
                        u = cache_up(uid, user)
                        return send_message(json)
                    delete_message({
                        'chat_id': uid,
                        'message_id': query['message_id'],
                    })
                    send_message({
                        'chat_id': uid,
                        'text': ''.join(['*' for i in range(len(text))])
                    })
                    json = {
                        'chat_id': uid,
                        'message_id': query['message_id'],
                        'text': f'{translate("account_registered", user["language"])}\n',
                        'parse_mode': 'markdown',
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    return send_message(json)
                elif user['last_action'] == 'register_redeem_code':
                    if 'parent' in user:
                        json = {
                            'chat_id': uid,
                            'text': f'{translate("promo_code_already_registered", user["language"])}',
                        }
                        user['last_action'] = None
                        u = cache_up(uid, user)
                        return send_message(json)
                    parent_user_id = int(verify_key(bytes.fromhex(text)))
                    if parent_user_id == uid:
                        json = {
                            'chat_id': uid,
                            'text': f'{translate("promo_code_not_applicable", user["language"])}',
                        }
                        user['last_action'] = None
                        u = cache_up(uid, user)
                        return send_message(json)
                    parent_user = find_one('users', {'id': parent_user_id})
                    if parent_user is not None:
                        update_one('users', {'id': uid}, {
                            'parent': parent_user_id
                        })
                        update_one('users', {'id': parent_user_id}, {
                            'team_count': parent_user['team_count'] + 1,
                        })
                        if user['subscription']['next_payment'] is not None:
                            next_payment = datetime.strptime(user['subscription']['next_payment'],
                                                             "%Y-%m-%d").date()
                        else:
                            next_payment = datetime.today()
                        next_payment += timedelta(days=3)
                        if user['subscription']['status'] == 'deactive':
                            update_one('users', {'id': uid}, {
                                'subscription.status': 'active',
                                'subscription.plan': 'trial',
                                'subscription.start_date': datetime.today().strftime("%Y-%m-%d"),
                            })
                        update_one('users', {'id': uid}, {
                            'subscription.next_payment': next_payment.strftime("%Y-%m-%d"),
                        })
                        json = {
                            'chat_id': uid,
                            'text': f'{translate("promo_code_registered", user["language"])}',
                        }
                        user['parent'] = parent_user_id
                        user['last_action'] = None
                        u = cache_up(uid, user)
                        return send_message(json)
                    else:
                        json = {
                            'chat_id': uid,
                            'text': f'{translate("invalid_promo_code", user["language"])}',
                        }
                        user['last_action'] = None
                        u = cache_up(uid, user)
                        return send_message(json)
                    pass
                elif user['last_action'] == 'contact_admin':
                    json = {
                        'chat_id': ADMIN_USER_ID,
                        'text': f'`{user["username"]}`:\n'
                                f'\"{text}\"',
                        'parse_mode': 'markdown'
                    }
                    user['last_action'] = None
                    u = cache_up(uid, user)
                    return send_message(json)
                # delete_message({
                #     'chat_id': uid,
                #     'message_id': query['message_id'],
                # })
                json = {
                    'chat_id': uid,
                    'text': '😊'
                }
                send_message(json)
            pass
    except Exception as e:
        print(e)
    pass
