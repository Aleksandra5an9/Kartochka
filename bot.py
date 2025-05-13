import requests
from datetime import datetime
import pandas as pd
import schedule
import time
import os
import matplotlib.pyplot as plt
from zipfile import ZipFile

# === Telegram Bot настройки ===
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === Параметры поиска ===
query_list = [
    'пижама мужская',
    'пижама мужская со штанами',
    'костюм для дома мужской',
    'пижама мужская шелковая'
    'джерси для рыбалки',
    'одежда для рыбалки',
    'джерси мужской'
]
max_page = 3
brand = 'Rebel River'

# === Соответствие ID → Артикул ===
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

# === Пути ===
history_file = 'data/history.csv'
excel_file = 'data/weekly_report.xlsx'
graph_dir = 'graphs/'
graph_zip = 'graphs.zip'

os.makedirs('data', exist_ok=True)
os.makedirs('graphs', exist_ok=True)

# === Telegram сообщение ===
def send_to_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {'chat_id': CHAT_ID, 'text': text}
        r = requests.post(url, data=payload)
        print(f"Telegram status: {r.status_code}")
        print(r.text)
    except Exception as e:
        print(f"Ошибка отправки Telegram: {e}")

# === Получение данных ===
def get_card_positions():
    arr = []
    for query in query_list:
        for page in range(1, max_page + 1):
            url = f"https://search.wb.ru/exactmatch/ru/common/v13/search?ab_testing=false&appType=1&curr=rub&dest=-1257484&hide_dtype=13&lang=ru&page={page}&query={query}&resultset=catalog&sort=popular&spp=30&suppressSpellcheck=false"
            try:
                res = requests.get(url)
                if res.status_code != 200:
                    continue
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
                print(f"Ошибка запроса: {e}")
    return arr

# === Главная задача ===
def job():
    print("🟡 Выполняется задача job...")
    send_to_telegram("🚀 Бот запущен. Сбор данных начат.")

    results = get_card_positions()
    if not results:
        send_to_telegram("❗Карточки не найдены.")
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
        message += f"🔍 {row['Query']}\n🆔 {row['SKU']}\n📍 {row['Position']} (Промо: {row['PromoPosition']})\n🕓 {row['Time']}\n\n"

    send_to_telegram(message)

# === Графики и Excel ===
def export_to_excel():
    print("📊 Экспорт в Excel начат...")
    if not os.path.exists(history_file):
        return
    df = pd.read_csv(history_file)
    df['Time'] = pd.to_datetime(df['Time'])
    df.to_excel(excel_file, index=False)

    for f in os.listdir(graph_dir):
        os.remove(os.path.join(graph_dir, f))

    for sku in df['SKU'].unique():
        df_sku = df[df['SKU'] == sku].sort_values('Time')
        plt.figure()
        plt.plot(df_sku['Time'], df_sku['Position'], marker='o')
        plt.title(f'Позиции: {sku}')
        plt.gca().invert_yaxis()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(graph_dir, f'{sku}.png'))
        plt.close()

    with ZipFile(graph_zip, 'w') as zipf:
        for f in os.listdir(graph_dir):
            zipf.write(os.path.join(graph_dir, f), arcname=f)

    send_to_telegram("📈 Еженедельный отчёт и графики обновлены.")

# === Планировщик ===
schedule.every(4).hours.do(job)
schedule.every().sunday.at("10:00").do(export_to_excel)

# Вызов сразу при старте
job()

print("⏳ Бот запущен. Ожидание задач...")

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        print(f"❗ Ошибка в основном цикле: {e}")
        send_to_telegram(f"❗ Ошибка в цикле: {e}")
