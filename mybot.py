import ccxt
import pandas as pd
import ta
import time
import os
from dotenv import load_dotenv

# Carica le variabili dal file .env
load_dotenv()

# Recupera le chiavi API
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

# Configura l'exchange con le chiavi caricate
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True
})

# Configurazione dei parametri di trading
symbol = 'BTC/USDT'
timeframe = '1h'  # intervallo di tempo
quantity = 0.001  # quantità di BTC da acquistare/vendere
max_balance = 100  # budget massimo


def get_market_data(symbol, timeframe):
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df


def apply_strategy(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
    # Condizioni di acquisto e vendita
    if df['rsi'].iloc[-1] < 30:  # livello di ipervenduto
        return 'buy'
    elif df['rsi'].iloc[-1] > 70:  # livello di ipercomprato
        return 'sell'
    return 'hold'


def place_order(order_type, symbol, quantity):
    if order_type == 'buy':
        order = exchange.create_market_buy_order(symbol, quantity)
    elif order_type == 'sell':
        order = exchange.create_market_sell_order(symbol, quantity)
    else:
        order = None
    return order


def run_bot():
    balance = max_balance
    while True:
        df = get_market_data(symbol, timeframe)
        action = apply_strategy(df)
        
        if action == 'buy' and balance >= quantity:
            order = place_order('buy', symbol, quantity)
            print("Compra eseguita:", order)
            balance -= quantity
        elif action == 'sell' and balance >= quantity:
            order = place_order('sell', symbol, quantity)
            print("Vendita eseguita:", order)
            balance += quantity
        else:
            print("Nessuna azione. Aspetto il prossimo ciclo.")
        
        time.sleep(3600)  # Attende 1 ora per il prossimo ciclo



if __name__ == "__main__":
    run_bot()