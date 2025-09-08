import os
from dotenv import load_dotenv
from SmartApi import SmartConnect
import pandas as pd

load_dotenv()

API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP = os.getenv("ANGEL_TOTP")

smart_api = SmartConnect(API_KEY)

def login():
    """Establishes a session with Angel One."""
    try:
        data = smart_api.generateSession(CLIENT_ID, PASSWORD, TOTP)
        if data['status'] and data['data']['jwtToken']:
            print("Login Successful!")
            return smart_api
        else:
            print("Login Failed:", data['message'])
            return None
    except Exception as e:
        print(f"An error occurred during login: {e}")
        return None

def get_historical_data(symbol_token, from_date, to_date, interval='ONE_DAY'):
    """Fetches historical candle data."""
    try:
        params = {
            "exchange": "NSE",
            "symboltoken": symbol_token,
            "interval": interval,
            "fromdate": from_date,
            "todate": to_date
        }
        hist_data = smart_api.getCandleData(params)
        if hist_data['status']:
            df = pd.DataFrame(hist_data['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching historical data for {symbol_token}: {e}")
        return pd.DataFrame()

def get_ltp(symbol_token):
    """Gets the Last Traded Price for a symbol."""
    try:
        params = {"exchange": "NSE", "tradingsymbol": "SBIN-EQ", "symboltoken": symbol_token} # tradingsymbol is a dummy here
        ltp_data = smart_api.ltpData("NSE", params['tradingsymbol'], params['symboltoken'])
        if ltp_data['status']:
            return ltp_data['data']
        return {}
    except Exception as e:
        print(f"Error fetching LTP for {symbol_token}: {e}")
        return {}