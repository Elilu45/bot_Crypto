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
timeframe = '5m'  # intervallo di tempo
quantity = 0.001  # quantità di BTC da acquistare/vendere
max_balance = 100  # budget massimo




def get_market_data(symbol, timeframe):
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Converte 'timestamp' in datetime UTC e poi nel fuso orario locale
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df['timestamp'] = df['timestamp'].dt.tz_convert('Europe/Rome')  # Sostituisci con il tuo fuso orario, se diverso
    
    return df





def get_latest_price(symbol):
    ticker = exchange.fetch_ticker(symbol)
    return {
        'timestamp': pd.to_datetime(ticker['timestamp'], unit='ms'),
        'bid': ticker['bid'],
        'ask': ticker['ask'],
        'last': ticker['last']
    }




def apply_strategy(df, latest_price):
    # Calcola l'RSI e lo aggiunge al DataFrame
    df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
    
    # Ottiene l'ultimo valore di RSI e l'ultimo prezzo
    rsi_last = df['rsi'].iloc[-1]
    last_price = latest_price['last']

    # Condizioni di acquisto e vendita basate su RSI e prezzo attuale
    if rsi_last < 30 and last_price < df['close'].iloc[-1]:  
        # RSI indica ipervenduto e l'ultimo prezzo è inferiore al prezzo di chiusura precedente
        return 'buy'
    elif rsi_last > 70 and last_price > df['close'].iloc[-1]:  
        # RSI indica ipercomprato e l'ultimo prezzo è superiore al prezzo di chiusura precedente
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
        latest_price = get_latest_price(symbol)
        print(f"Dati storici: {df}")
        print(f"Ultimo prezzo: {latest_price}")

        # Applica la strategia
        action = apply_strategy(df, latest_price)
        print(f"Decisione di trading: {action}")
        
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