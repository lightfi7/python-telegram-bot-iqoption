from dotenv import load_dotenv


load_dotenv()

from flask import Flask, request
import modules.scheduler as scheduler
import modules.cache as cache
from modules.database import update_one
from modules.mastermind import generate_response
from modules.telegram import setup_webhook
from modules.tron import TronClient

app = Flask(__name__)
tron_client = TronClient()


@app.route('/', methods=['GET', 'POST'])
def respond():
    try:
        data = request.get_json(force=True)
        generate_response(data)
        return 'OK'
    except Exception as e:
        return str(e)


@app.route('/config', methods=['POST'])
def config():
    try:
        data = request.get_json(force=True)
        # verify token
        token = data['token']
        if token == '3g4!Hm*jk#9gRX':
            update_one('config', {'name': 'monthly'}, {'name': 'monthly', 'value': data['monthly']})
            update_one('config', {'name': 'annual'}, {'name': 'annual', 'value': data['annual']})
        return 'OK'
    except Exception as e:
        return str(e)

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    s = setup_webhook()
    if s:
        return "webhook setup ok"
    else:
        return "webhook setup failed"


if __name__ == '__main__':
    cache.init()
    scheduler.start()
    app.run(host='0.0.0.0', port=5000, debug=True)


    # # print(tron_client.create_wallet())
    # tron_client.set_private_key('7c77f4038b9b47cbd1ad8ffd22c13c39cb1aaedf8e21c3c490c7601372a9b8cf')
    # print(tron_client.get_balance('TUaAqSLScdZVrb1UeZaxYqKgjNyaoDWetY'))
    # print(tron_client.get_trc20_balance('TUaAqSLScdZVrb1UeZaxYqKgjNyaoDWetY'))
    # # tron_client.send_trx('TRa9HDp9daJHwXF6eWTnXA3XN6FSqjT981', 1, 'TUaAqSLScdZVrb1UeZaxYqKgjNyaoDWetY',
    # #                      '7c77f4038b9b47cbd1ad8ffd22c13c39cb1aaedf8e21c3c490c7601372a9b8cf')
    # # tron_client.send_usdt('TRa9HDp9daJHwXF6eWTnXA3XN6FSqjT981', 1, 'TUaAqSLScdZVrb1UeZaxYqKgjNyaoDWetY',
    # #                       '7c77f4038b9b47cbd1ad8ffd22c13c39cb1aaedf8e21c3c490c7601372a9b8cf')
    # tron_client.monitor_deposits([
    #     {
    #         'uid': '',
    #         'base58check_address': 'TE8y1GmkPE8ktpALtyuw7fC8aahcNun8cc',
    #         'hex_address': '41cc0f03c8a4807a30c86406bbc44f7e11e9e24776',
    #         'private_key': '7c77f4038b9b47cbd1ad8ffd22c13c39cb1aaedf8e21c3c490c7601372a9b8cf',
    #         'public_key': '3b1a7dc59f73fae3d5efecacef227c939d814721488783047812165731a0b9f43b5f65d91a1055f816ff5d93c4cd261554273ea29df85b2cb9fcef49cb7caf9f'
    #      }
    # ], lambda x: print(x))
