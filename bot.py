import os
import requests
from datetime import datetime
import pandas as pd
import schedule
import time
import matplotlib.pyplot as plt
from zipfile import ZipFile

# === Пути ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
GRAPH_DIR = os.path.join(BASE_DIR, 'graphs')

history_file = os.path.join(DATA_DIR, 'history.csv')
excel_file = os.path.join(DATA_DIR, 'weekly_report.xlsx')
graph_zip = os.path.join(BASE_DIR, 'graphs.zip')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(GRAPH_DIR, exist_ok=True)

# === Telegram Bot настройки ===
TOKEN = os.getenv('TELEGRAM_TOKEN')  # в Railway укажи переменную
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')  # в Railway укажи переменную

# === Параметры поиска ===
query_list = [
    'пижама мужская',
    'пижама мужская со штанами',
    'джерси',
    'джерси мужской'
]
max_page = 3
brand = 'Rebel River'

id_to_sku = {
    260800583: 'RRPPSBK0924',
    260897865: 'RRPPKLBK0924',
    293878560: 'RRPPKLWT1224',
    375740835: 'RRPPKLBE0325',
    375742309: 'RRPPKLBKSS0425',
    375744765: 'RRPPKLWTSS0425',
    332051245: 'RRJGREYS010225',
    332082880: 'RRJLTGREYP020225',
    332084081: 'RRJGREEN030225',
    332084082: 'RRJBKORP040225',
    332084083: 'RRJGREYP050225'
}

def get_card_positions():
    arr = []
    for query in query_list:
        for page in range(1, max_page + 1):
            url = f"https://search.wb.ru/exactmatch/ru/common/v13/search?ab_testing=false&appType=1&curr=rub&dest=-1257484&hide_dtype=13&lang=ru&page={page}&query={query}&resultset=catalog&sort=popular&spp=30&suppressSpellcheck=false"
            res = requests.get(url)
            if res.status_code != 200:
                continue
            try:
                for card in res.json()['data']['products']:
                    if card.get('log') and card['brand'] == brand:
                        card_id = card['id']
                        sku = id_to_sku.get(card_id, str(card_id))
                        arr.append([
                            card['log']['position'],
                            card['log']['promoPosition'],
                            datetime.now().strftime('%Y-%m-%d %H:%M'),
                            query,
                            sku
                        ])
            except Exception as e:
                print(f"Ошибка JSON: {e}")
    return arr

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': text
    }
    requests.post(url, data=payload)

def job():
    results = get_card_positions()
    if not results:
        send_to_telegram("Карточки не найдены.")
        return

    df_new = pd.DataFrame(results, columns=['Position', 'PromoPosition', 'Time', 'Query', 'SKU'])

    if os.path.exists(history_file):
        df_old = pd.read_csv(history_file)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new
    df_all.to_csv(history_file, index=False)

    message = "📦 Позиции карточек:\n\n"
    for _, row in df_new.iterrows():
        message += f"🔍 Запрос: {row['Query']}\n🆔 Артикул: {row['SKU']}\n📍 Позиция: {row['Position']}, Промо: {row['PromoPosition']}\n🕓 Время: {row['Time']}\n\n"

    alerts = []
    if os.path.exists(history_file):
        for sku in df_new['SKU'].unique():
            last = df_all[df_all['SKU'] == sku].sort_values('Time', ascending=False)
            if len(last) >= 2:
                try:
                    prev_pos = int(last.iloc[1]['Position'])
                    curr_pos = int(last.iloc[0]['Position'])
                    if curr_pos - prev_pos >= 20:
                        alerts.append(f"⚠️ Артикул {sku}: позиция упала с {prev_pos} до {curr_pos}")
                except:
                    pass

    if alerts:
        message += "\n📉 Обнаружены резкие падения позиций:\n" + "\n".join(alerts)

    send_to_telegram(message)

def export_to_excel():
    if not os.path.exists(history_file):
        return

    df = pd.read_csv(history_file)
    df['Time'] = pd.to_datetime(df['Time'])
    df.to_excel(excel_file, index=False)

    for f in os.listdir(GRAPH_DIR):
        os.remove(os.path.join(GRAPH_DIR, f))

    for sku in df['SKU'].unique():
        df_sku = df[df['SKU'] == sku].sort_values('Time')
        plt.figure()
        plt.plot(df_sku['Time'], df_sku['Position'], marker='o')
        plt.title(f'Позиции по {sku}')
        plt.xlabel('Время')
        plt.ylabel('Позиция')
        plt.gca().invert_yaxis()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(GRAPH_DIR, f"{sku}.png"))
        plt.close()

    with ZipFile(graph_zip, 'w') as zipf:
        for f in os.listdir(GRAPH_DIR):
            zipf.write(os.path.join(GRAPH_DIR, f), arcname=f)

    print("✅ Еженедельный отчет и графики сохранены.")

# === Планировщик ===
schedule.every(4).hours.do(job)
schedule.every().sunday.at("10:00").do(export_to_excel)

job()
print("⏳ Бот запущен. Ожидание задач...")

while True:
    schedule.run_pending()
    time.sleep(1)
