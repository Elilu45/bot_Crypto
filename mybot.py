import ccxt
import pandas as pd
import ta
import time
import os

from dotenv import load_dotenv

import ntplib
from time import ctime, sleep
from ccxt.base.errors import RequestTimeout

# Carica le variabili dal file .env

load_dotenv()


# Recupera le chiavi API Binance
# api_key = os.getenv("BINANCE_API_KEY")
# api_secret = os.getenv("BINANCE_API_SECRET")


# Recupera le chiavi API Bybit
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")


# Configura l'exchange con le chiavi caricate
exchange = ccxt.bybit({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
    'options': {
        'adjustForTimeDifference': True  # Aggiungi questa linea
    }
})


# Configurazione dei parametri di trading
symbol = 'BTC/USDT'
timeframe = '5m'  # intervallo di tempo
quantity = 0.000999  # quantità di BTC da acquistare/vendere
max_balance = 100  # budget massimo



def sync_time():
    ntp_client = ntplib.NTPClient()
    response = ntp_client.request('pool.ntp.org')
    print("Current time:", ctime(response.tx_time))


def get_market_data(symbol, timeframe):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df['timestamp'] = df['timestamp'].dt.tz_convert('Europe/Rome')
        # df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=6).rsi()
        return df
    except RequestTimeout as e:
        print(f"Timeout durante il recupero dei dati per {symbol}. Riprovo...")
        time.sleep(5)  # Attendi 5 secondi e poi riprova
        return get_market_data(symbol, timeframe)  # Riprova la richiesta
    except Exception as e:
        print(f"Errore nel recupero dei dati per {symbol}: {str(e)}")
        return None


# def get_latest_price(symbol):

#     ticker = exchange.fetch_ticker(symbol)

#     return {

#         'timestamp': pd.to_datetime(ticker['timestamp'], unit='ms'),

#         'bid': ticker['bid'],

#         'ask': ticker['ask'],

#         'last': ticker['last']

#     }


def get_latest_price(symbol):
    ticker = exchange.fetch_ticker(symbol)
    return {
        # usa il timestamp locale
        'timestamp': pd.to_datetime(time.time() * 1000, unit='ms'),
        'bid': ticker['bid'],
        'ask': ticker['ask'],
        'last': ticker['last']
    }


# Strategia di incrocio delle medie mobili

# def moving_average_strategy(df):

#     df['SMA50'] = df['close'].rolling(window=50).mean()

#     df['SMA200'] = df['close'].rolling(window=200).mean()

#     if df['SMA50'].iloc[-1] > df['SMA200'].iloc[-1]:

#         return "buy"

#     elif df['SMA50'].iloc[-1] < df['SMA200'].iloc[-1]:

#         return "sell"

#     return "hold"


def get_entry_price_from_executed_order(symbol):
    try:
        # Recupera gli ultimi ordini chiusi per il simbolo specifico
        orders = exchange.fetch_closed_orders(symbol)
        # Filtra solo gli ordini di acquisto, considerando l'ultimo ordine eseguito
        for order in reversed(orders):
            if order['side'] == 'buy' and order['status'] == 'closed':
                return order['average']  # Ritorna il prezzo medio dell'ordine
        # Nessun ordine eseguito trovato
        return None
    except ccxt.BaseError as e:
        print(f"Errore durante il recupero degli ordini eseguiti: {e}")
        return None


def apply_strategy(df, latest_price, stop_loss_percent, symbol):
    # Ottieni l'ultimo valore di RSI, l'ultimo prezzo e la media mobile a 50 periodi
    rsi_last = df['rsi'].iloc[-1]
    last_price = latest_price['last']
    moving_avg = df['close'].rolling(window=50).mean().iloc[-1]  # Media mobile a 50 periodi
    print(f"media mobile: {moving_avg}")
    # Ottieni il prezzo di ingresso dell'ordine aperto (se esiste)
    entry_price = get_entry_price_from_executed_order(symbol)
    # Condizioni di acquisto
    if entry_price is None and rsi_last < 30 and last_price > moving_avg and last_price <= df['close'].iloc[-2]:
        print(f"RSI: {rsi_last}, Last Price: {last_price}")
        entry_price = last_price  # Imposta il prezzo di ingresso
        return 'buy', entry_price  # Restituisci solo l'azione e il prezzo di ingresso
    # Condizioni di vendita
    elif entry_price is not None and rsi_last > 75 and last_price > entry_price and last_price < moving_avg:
        # Verifica che RSI sia in zona di ipercomprato e che siamo in profitto rispetto al prezzo di ingresso
        print(f"RSI: {rsi_last}, Last Price: {last_price}, Entry Price: {entry_price}")
        return 'sell', entry_price
    
    # Verifica stop loss e take profit
    elif entry_price is not None:
        stop_loss = entry_price * (1 - stop_loss_percent)
        take_profit = entry_price * 1.05  # Esempio di take profit al 5%

        if last_price <= stop_loss:
            print(f"Stop loss attivato. Prezzo: {last_price}, Entry Price: {entry_price}, Stop Loss: {stop_loss}")
            return 'sell', entry_price
        elif last_price >= take_profit:
            print(f"Take profit attivato. Prezzo: {last_price}, Entry Price: {entry_price}, Take Profit: {take_profit}")
            return 'sell', entry_price

    print(f"RSI: {rsi_last} Last Price: {last_price} and df[close]: {df['close'].iloc[-1]} - Decision: Hold")

    return 'hold', entry_price


# def apply_strategy(df, latest_price, stop_loss_percent, entry_price):

#     # Ottieni l'ultimo valore di RSI, l'ultimo prezzo e la media mobile a 50 periodi

#     rsi_last = df['rsi'].iloc[-1]

#     last_price = latest_price['last']

#     moving_avg = df['close'].rolling(window=50).mean().iloc[-1]  # Media mobile a 50 periodi

#     print(f"media mobile: {moving_avg}")


#     # Condizioni di acquisto con trend e volume

#     # RSI indica ipervenduto e l'ultimo prezzo è inferiore al prezzo di chiusura precedente

#     if rsi_last < 30 and last_price <= df['close'].iloc[-1] and last_price > moving_avg:

#         print(f"RSI: {rsi_last}, Last Price: {last_price}")

#         entry_price = last_price # Imposta il prezzo di ingresso

#         return 'buy', entry_price # Restituisci solo l'azione e il prezzo di ingresso


#     # Condizioni di vendita con trend e volume

#     # RSI indica ipercomprato e l'ultimo prezzo è superiore al prezzo di chiusura precedente

#     elif rsi_last > 75 and last_price >= df['close'].iloc[-1] and last_price < moving_avg:

#         print(f"RSI: {rsi_last}, Last Price: {last_price}")

#         return 'sell', entry_price


#     # Verifica stop loss e take profit se siamo in posizione

#     elif entry_price is not None:

#         # Verifica lo stop loss se siamo in posizione

#         stop_loss = entry_price * (1 - stop_loss_percent)

#         take_profit = entry_price * 1.05  # Esempio take profit al 5%


#         if last_price <= stop_loss:

#             print(f"Stop loss attivato. Prezzo: {last_price}, Entry Price: {entry_price}, Stop Loss: {stop_loss}")

#             return 'sell', entry_price


#         elif last_price >= take_profit:

#             print(f"Take profit attivato. Prezzo: {last_price}, Entry Price: {entry_price}, Take Profit: {take_profit}")

#             return 'sell', entry_price


#     print(f"RSI: {rsi_last} Last Price: {last_price} and df[close]: {df['close'].iloc[-1]} - Decision: Hold")

#     return 'hold', entry_price # Ritorna "hold" se nessuna azione viene presa


def place_order(order_type, symbol, quantity):
    try:
        # Esegue l'ordine se i fondi sono sufficienti
        if order_type == 'buy':
            order = exchange.create_market_buy_order(symbol, quantity)
        elif order_type == 'sell':
            order = exchange.create_market_sell_order(symbol, quantity)
        else:
            raise ValueError("Tipo di ordine non valido. Usa 'buy' o 'sell'.")

        if order:
            print(f"Ordine {order_type} eseguito per {quantity} {symbol}. Dettagli: {order}")

        return order

    except ccxt.NetworkError as e:
        print(f"Errore di rete: {str(e)}")
    except ccxt.ExchangeError as e:
        print(f"Errore nell'Exchange: {str(e)}")
    except Exception as e:
        print(f"Errore generico: {str(e)}")
    return None


def get_balance(symbol):
    balance_info = exchange.fetch_balance()  # Ottieni i bilanci dell'account

    if symbol in balance_info['total']:
        # Restituisci il saldo totale di quel simbolo
        return balance_info['total'][symbol]
    
    return 0  # Se il simbolo non è trovato, restituisci 0


def run_bot():
    entry_price = None

    while True:
        df = get_market_data(symbol, timeframe)
        latest_price = get_latest_price(symbol)
        # print(f"Dati storici: {df}")
        print(f"Ultimo prezzo: {latest_price}")

        # Controlla il saldo prima di piazzare l'ordine
        balance_info = exchange.fetch_balance()
        usdt_balance = balance_info['total'].get('USDT', 0)
        btc_balance = balance_info['total'].get('BTC', 0)

        # Applica la strategia con stop loss
        action, entry_price = apply_strategy(df, latest_price, stop_loss_percent=0.02, symbol=symbol)
        print(f"Entry price: {entry_price}")

        if action == "hold":
            print(f"Nessuna decisione di trading perchè action: {action}")
        else:
            print(f"Decisione di trading: possibile {action}")
        # in_position = True

        # Esegui le azioni di trading in base alla decisione
        if action == 'buy' and entry_price is None:
            if usdt_balance < quantity * get_latest_price(symbol)['last']:
                print("Fondi USDT insufficienti per completare l'ordine di acquisto.")
            else:
                print(f"Acquisto in corso perchè non c'è una entry price: {entry_price}")
                order = place_order('buy', symbol, quantity)
                print("Compra eseguita:", order)
        elif action == 'sell' and entry_price is not None:
            print(f"Vendita in corso perchè c'è una entry price: {entry_price}")
            order = place_order('sell', symbol, quantity)
            print("Vendita eseguita:", order)
        elif action == 'hold':
            print("Nessuna azione. Aspetto il prossimo ciclo.")

        # Calcola la differenza tra il saldo in USDT e BTC
        usdt_balance = get_balance('USDT')  # Ottieni il saldo in USDT
        btc_balance = get_balance('BTC')  # Ottieni il saldo in BTC

        print(f"Saldo in USDT: {usdt_balance} | Saldo in BTC: {btc_balance}")

        # Calcolo il valore in USDT del saldo in BTC
        # Prezzo corrente di BTC in USDT
        btc_to_usdt = btc_balance * latest_price['last']

        print(f"Il valore di BTC in USDT è: {btc_to_usdt} con prezzo di acquisto: {entry_price}")

        # Calcola e stampa la differenza tra USDT e BTC
        # Somma il valore in USDT di BTC al saldo USDT
        total_balance = usdt_balance + btc_to_usdt

        print(f"Il mio Residuo totale in USDT è: {usdt_balance}")
        print(f"Il mio Balance totale in USDT è: {total_balance}")

        time.sleep(120)  # Attende 2 minuti per il prossimo ciclo


if __name__ == "__main__":
    sync_time()
    run_bot()