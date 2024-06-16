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
            update_one('config', {'name': 'wallet'}, {'name': 'wallet', 'value': data['wallet']})
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
