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
symbol = 'BTC/USDC'
timeframe = '5m'  # intervallo di tempo
quantity = 0.001  # quantità di BTC da acquistare/vendere
max_balance = 100  # budget massimo


def sync_time():
    ntp_client = ntplib.NTPClient()
    response = ntp_client.request('pool.ntp.org')
    print("Current time:", ctime(response.tx_time))


# def get_market_data(symbol, timeframe):
#     # Recupera i dati di mercato
#     bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
#     df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
#     # Converte il timestamp da Unix a datetime in UTC, poi nel fuso orario locale
#     df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
#     df['timestamp'] = df['timestamp'].dt.tz_convert('Europe/Rome')  # Sostituisci con il tuo fuso orario
    
#     # Calcola l'RSI utilizzando i prezzi di chiusura e aggiungilo come colonna 'rsi'
#     df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
    
#     return df


def get_market_data(symbol, timeframe):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df['timestamp'] = df['timestamp'].dt.tz_convert('Europe/Rome')
        #df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=6).rsi()
        return df
    except RequestTimeout as e:
        print(f"Timeout durante il recupero dei dati per {symbol}. Riprovo...")
        time.sleep(5)  # Attendi 5 secondi e poi riprova
        return get_market_data(symbol, timeframe)  # Riprova la richiesta
    except Exception as e:
        print(f"Errore nel recupero dei dati per {symbol}: {str(e)}")
        return None





def get_latest_price(symbol):
    ticker = exchange.fetch_ticker(symbol)
    return {
        'timestamp': pd.to_datetime(ticker['timestamp'], unit='ms'),
        'bid': ticker['bid'],
        'ask': ticker['ask'],
        'last': ticker['last']
    }




# def apply_strategy(df, latest_price):

#     # Ottiene l'ultimo valore di RSI e l'ultimo prezzo
#     rsi_last = df['rsi'].iloc[-1]
#     last_price = latest_price['last']

#     # Condizioni di acquisto e vendita basate su RSI e prezzo attuale
#     if rsi_last < 30 and last_price < df['close'].iloc[-1]:  
#         # RSI indica ipervenduto e l'ultimo prezzo è inferiore al prezzo di chiusura precedente
#         print("RSI:", rsi_last, "Last Price:", last_price, "- Decision: Buy")
#         return 'buy'
#     elif rsi_last > 70 and last_price > df['close'].iloc[-1]:  
#         # RSI indica ipercomprato e l'ultimo prezzo è superiore al prezzo di chiusura precedente
#         print("RSI:", rsi_last, "Last Price:", last_price, "- Decision: Sell")
#         return 'sell'
#     print("RSI:", rsi_last, "Last Price:", last_price, "- Decision: Hold")
#     return 'hold'



def apply_strategy(df, latest_price, stop_loss_percent, entry_price):
    # Ottieni l'ultimo valore di RSI e l'ultimo prezzo
    rsi_last = df['rsi'].iloc[-1]
    last_price = latest_price['last']

    # Condizioni di acquisto e vendita basate su RSI e prezzo attuale
    if rsi_last < 40 and last_price <= df['close'].iloc[-1]:
        # RSI indica ipervenduto e l'ultimo prezzo è inferiore al prezzo di chiusura precedente
        print(f"RSI: {rsi_last}, Last Price: {last_price}")
        entry_price = last_price  # Imposta il prezzo di ingresso
        return 'buy', entry_price  # Restituisci solo l'azione e il prezzo di ingresso

    elif rsi_last > 70 and last_price > df['close'].iloc[-1]:
        # RSI indica ipercomprato e l'ultimo prezzo è superiore al prezzo di chiusura precedente
        print(f"RSI: {rsi_last}, Last Price: {last_price}")
        return 'sell', entry_price  # Non cambiamo l'entry_price perché siamo in uscita

    elif entry_price is not None:
        # Verifica lo stop loss se siamo in posizione
        stop_loss = entry_price * (1 - stop_loss_percent)
        if last_price <= stop_loss:
            print(f"Stop loss attivato. Prezzo: {last_price}, Entry Price: {entry_price}, Stop Loss: {stop_loss}")
            return 'sell', entry_price  # Esegui la vendita se raggiunto lo stop loss

    print("RSI:", rsi_last, "Last Price:", last_price, "- Decision: Hold")
    return 'hold', entry_price  # Ritorna "hold" se nessuna azione viene presa






# def place_order(order_type, symbol, quantity):
#     if order_type == 'buy':
#         order = exchange.create_market_buy_order(symbol, quantity)
#     elif order_type == 'sell':
#         order = exchange.create_market_sell_order(symbol, quantity)
#     else:
#         order = None
#     return order



def place_order(order_type, symbol, quantity):
    try:
        if order_type == 'buy':
            order = exchange.create_market_buy_order(symbol, quantity)
        elif order_type == 'sell':
            order = exchange.create_market_sell_order(symbol, quantity)
        else:
            raise ValueError("Tipo di ordine non valido. Usa 'buy' o 'sell'.")
        
        # Verifica che l'ordine sia stato eseguito correttamente
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




# def run_bot():
#     balance = max_balance
#     in_position = False
#     entry_price = None
#     while True:
#         df = get_market_data(symbol, timeframe)
#         latest_price = get_latest_price(symbol)
#         print(f"Dati storici: {df}")
#         print(f"Ultimo prezzo: {latest_price}")

#         # Applica la strategia
#         action = apply_strategy(df, latest_price)
#         print(f"Decisione di trading: {action}")
        
#         if action == 'buy' and balance >= quantity:
#             order = place_order('buy', symbol, quantity)
#             print("Compra eseguita:", order)
#             balance -= quantity
#         elif action == 'sell' and balance >= quantity:
#             order = place_order('sell', symbol, quantity)
#             print("Vendita eseguita:", order)
#             balance += quantity
#         else:
#             print("Nessuna azione. Aspetto il prossimo ciclo.")
        
#         print(f"il mio Balance è: {balance}")
#         time.sleep(600)  # Attende 1 ora per il prossimo ciclo


def get_balance(symbol):
    balance_info = exchange.fetch_balance()  # Ottieni i bilanci dell'account
    if symbol in balance_info['total']:
        return balance_info['total'][symbol]  # Restituisci il saldo totale di quel simbolo
    return 0  # Se il simbolo non è trovato, restituisci 0



def run_bot():
    in_position = False
    entry_price = None
    while True:
        df = get_market_data(symbol, timeframe)
        latest_price = get_latest_price(symbol)
        print(f"Dati storici: {df}")
        print(f"Ultimo prezzo: {latest_price}")

        # Applica la strategia con stop loss
        action, entry_price = apply_strategy(
            df, 
            latest_price,
            stop_loss_percent=0.02,  # Definisci la percentuale di stop loss
            entry_price=entry_price,
        )
        print(f"Decisione di trading: possibile {action}")

        # Esegui le azioni di trading in base alla decisione
        if action == 'buy' and not in_position:
            #order = place_order('buy', symbol, quantity)
            #print("Compra eseguita:", order)
            in_position = True  # Ora siamo in posizione
        elif action == 'sell' and in_position:
            order = place_order('sell', symbol, quantity)
            print("Vendita eseguita:", order)
            in_position = False  # Siamo usciti dalla posizione
        elif action == 'hold':
            print("Nessuna azione. Aspetto il prossimo ciclo.")
        

        # Calcola la differenza tra il saldo in USDC e BTC
        usdc_balance = get_balance('USDC')  # Ottieni il saldo in USDC
        btc_balance = get_balance('BTC')  # Ottieni il saldo in BTC
        print(f"Saldo in USDC: {usdc_balance} | Saldo in BTC: {btc_balance}")

        # Se vuoi calcolare il valore in USDC del saldo in BTC
        btc_to_usdc = btc_balance * latest_price['last']  # Prezzo corrente di BTC in USDC
        print(f"Il valore di BTC in USDC è: {btc_to_usdc}")

        # Calcola e stampa la differenza tra USDC e BTC
        total_balance = usdc_balance + btc_to_usdc  # Somma il valore in USDC di BTC al saldo USDC
        print(f"Il mio Balance totale in USDC è: {total_balance}")
        time.sleep(60)  # Attende 1 minuto per il prossimo ciclo




if __name__ == "__main__":
    sync_time()
    run_bot()