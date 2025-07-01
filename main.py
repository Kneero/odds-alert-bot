import requests
import time
import threading
from flask import Flask
import telebot

# === Your credentials ===
TELEGRAM_TOKEN = '7456382541:AAFfUzCP0gitzPn5lPkw4Y23hZT2vi29XCk'
ODDS_API_KEY = 'c028fea0f900c2d881d4617c49ed2922'

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

USER_CHAT_ID = None
previous_odds = {}

ALLOWED_SPORTS = ["Soccer", "Basketball", "Tennis"]
KEY_OVER_MARKETS = ["Over 1.5", "Over 8.5", "Over 9.5"]
HIGH_PROB_THRESHOLD = 1.70

@bot.message_handler(commands=['start'])
def start(message):
    global USER_CHAT_ID
    USER_CHAT_ID = message.chat.id
    bot.send_message(USER_CHAT_ID, "✅ SportyBet Value Bot is LIVE!\nMonitoring Football, Basketball & Tennis.\nFocus: Over 1.5, Corners, High-Confidence Picks.\n📢 Only from *SportyBet*!")

@bot.message_handler(commands=['stop'])
def stop(message):
    global USER_CHAT_ID
    USER_CHAT_ID = None
    bot.send_message(message.chat.id, "🛑 Alerts paused.")

@bot.message_handler(commands=['status'])
def status(message):
    bot.send_message(message.chat.id, "📊 Running 24/7\nSports: Football, Basketball, Tennis\nBookie: *SportyBet Only*\nEvery 5 min")

def fetch_and_alert():
    global previous_odds
    url = "https://api.the-odds-api.com/v4/sports/upcoming/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "match_odds,totals,btts,corners",
        "oddsFormat": "decimal"
    }

    try:
        res = requests.get(url, params=params)
        data = res.json()
        data = data[:40]  # stay within API quota

        for game in data:
            sport = game.get("sport_title", "")
            if sport not in ALLOWED_SPORTS:
                continue

            teams = f"{game['home_team']} vs {game['away_team']}"
            for bookie in game['bookmakers']:
                if "Sporty" not in bookie['title']:
                    continue

                bookie_name = bookie['title']
                for market in bookie['markets']:
                    market_key = market['key']
                    for outcome in market['outcomes']:
                        label = outcome['name']
                        price = float(outcome['price'])
                        key = f"{teams}_{bookie_name}_{market_key}_{label}"

                        is_key_market = any(x in label for x in KEY_OVER_MARKETS)

                        if key in previous_odds:
                            old_price = previous_odds[key]
                            if price < old_price:
                                drop_pct = ((old_price - price) / old_price) * 100

                                if drop_pct >= 10 and price >= 2.50:
                                    alert_type = "🔥 Value Drop"
                                    if is_key_market:
                                        alert_type = "💡 Over/Corners"
                                    elif price <= HIGH_PROB_THRESHOLD:
                                        alert_type = "🔒 High Confidence"

                                    if USER_CHAT_ID:
                                        msg = (
                                            f"{alert_type} Alert from *SportyBet*!\n\n"
                                            f"🏟 *{teams}*\n"
                                            f"🎯 *Sport:* {sport}\n"
                                            f"📊 *Market:* {label} ({market_key})\n"
                                            f"💸 *Old Odds:* {old_price}\n"
                                            f"💰 *New Odds:* {price}\n"
                                            f"📉 *Drop:* {round(drop_pct, 2)}%"
                                        )
                                        bot.send_message(USER_CHAT_ID, msg, parse_mode="Markdown")

                        previous_odds[key] = price

    except Exception as e:
        print("❌ Error:", e)

def monitor_loop():
    while True:
        fetch_and_alert()
        time.sleep(300)  # every 5 minutes

threading.Thread(target=monitor_loop).start()

@app.route('/')
def home():
    return "✅ SportyBet Odds Bot is running."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
