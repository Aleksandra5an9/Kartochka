import requests

TOKEN = '8194698138:AAHVx7E_Tr0Ef22LFtwGSzKTCen9zOpDJu8'
CHAT_ID = '866640587'

def send_test():
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': '👋 Привет! Это тест от Railway.'
    }
    r = requests.post(url, data=payload)
    print(f"Status: {r.status_code}")
    print(r.text)

send_test()
