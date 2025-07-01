import requests
import time
import threading
from flask import Flask
import telebot

# === Your keys ===
TELEGRAM_TOKEN = '7456382541:AAFfUzCP0gitzPn5lPkw4Y23hZT2vi29XCk'
ODDS_API_KEY = 'c028fea0f900c2d881d4617c49ed2922'
USER_CHAT_ID = None

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

previous_odds = {}

@bot.message_handler(commands=['start'])
def start(message):
    global USER_CHAT_ID
    USER_CHAT_ID = message.chat.id
    print(f"User started bot: {message.chat.id}")
    bot.send_message(USER_CHAT_ID, "🔔 Odds Monitor Activated!\nYou'll receive alerts for changes in match odds, over/under, BTTS, and corners.")

@bot.message_handler(commands=['status'])
def status(message):
    bot.send_message(message.chat.id, "📊 Monitoring is active.\nChecking every 30 mins for odds changes.")

@bot.message_handler(commands=['stop'])
def stop(message):
    global USER_CHAT_ID
    USER_CHAT_ID = None
    bot.send_message(message.chat.id, "🔕 Alerts have been stopped.")

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
        
        # Fix the slicing error - ensure data is a list
        if isinstance(data, list):
            data = data[:30]  # Only process first 30 games to stay within API limits
        else:
            print("API response is not a list:", data)
            return

        for game in data:
            if "soccer" not in game["sport_key"]:
                continue

            teams = f"{game['home_team']} vs {game['away_team']}"
            for bookie in game['bookmakers']:
                name = bookie['title']
                for market in bookie['markets']:
                    market_key = market['key']
                    for outcome in market['outcomes']:
                        label = outcome['name']
                        price = float(outcome['price'])
                        key = f"{teams} - {label} @ {name} ({market_key})"

                        if key in previous_odds:
                            old_price = previous_odds[key]
                            change = price - old_price

                            if abs(change) >= 0.3 and USER_CHAT_ID:
                                emoji = "📉" if change < 0 else "📈"
                                msg = (
                                    f"{emoji} Odds Movement Alert\n\n"
                                    f"🏟 Match: {teams}\n"
                                    f"📊 Market: {label} ({market_key})\n"
                                    f"🏢 Bookmaker: {name}\n"
                                    f"Old Odds: {old_price}\n"
                                    f"New Odds: {price}\n"
                                    f"Change: {'+' if change > 0 else ''}{round(change, 2)}"
                                )
                                bot.send_message(USER_CHAT_ID, msg)

                        previous_odds[key] = price

    except Exception as e:
        print("Error:", e)

def monitor_loop():
    while True:
        fetch_and_alert()
        time.sleep(1800)  # Check every 30 minutes

def start_bot():
    """Start the Telegram bot polling"""
    print("Starting Telegram bot...")
    bot.polling(none_stop=True, interval=1)

# Background threads
threading.Thread(target=monitor_loop, daemon=True).start()
threading.Thread(target=start_bot, daemon=True).start()

# Keep Replit awake
@app.route('/')
def home():
    return "✅ Odds Bot Running"

# Start Flask server
if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=8080)
