import pandas as pd
import pandas_ta as ta
import yfinance as yf

def get_stock_info(ticker):
    """Fetches fundamental data using yfinance."""
    try:
        stock = yf.Ticker(f"{ticker}.NS")
        info = stock.info
        fundamentals = {
            "Market Cap": info.get('marketCap'), "P/E Ratio": info.get('trailingPE'),
            "P/B Ratio": info.get('priceToBook'), "Dividend Yield": info.get('dividendYield'),
            "52 Week High": info.get('fiftyTwoWeekHigh'), "52 Week Low": info.get('fiftyTwoWeekLow'),
            "Sector": info.get('sector'), "Industry": info.get('industry')
        }
        return fundamentals, info.get('longBusinessSummary')
    except Exception:
        return {}, None

def calculate_technical_indicators(df):
    """Calculates technical indicators. Expects a DataFrame with lowercase columns."""
    if df.empty: return pd.DataFrame()
    df.ta.rsi(append=True)
    df.ta.macd(append=True)
    df.ta.bbands(append=True)
    df.ta.ema(length=50, append=True)
    df.ta.ema(length=200, append=True)
    return df

def run_graham_scan(ticker):
    """Performs a basic Benjamin Graham value scan."""
    try:
        info = yf.Ticker(f"{ticker}.NS").info
        pe = info.get('trailingPE')
        pb = info.get('priceToBook')
        if pe is None or pb is None: return {"Verdict": "Not enough data"}
        verdict = "Potentially Undervalued" if pe < 15 and pb < 1.5 else "Not Meeting Graham Criteria"
        return {"P/E Ratio": f"{pe:.2f}", "P/B Ratio": f"{pb:.2f}", "Verdict": verdict}
    except Exception:
        return {}

def calculate_pivot_points(df):
    """Calculates standard pivot points. This version now correctly expects lowercase columns."""
    if df.empty or len(df) < 2: return {}
    
    last_candle = df.iloc[-2]
    high = last_candle['high']
    low = last_candle['low']
    close = last_candle['close']
    
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    
    return {
        "Resistance 2 (R2)": r2, "Resistance 1 (R1)": r1, "Pivot Point": pivot,
        "Support 1 (S1)": s1, "Support 2 (S2)": s2
    }

def get_competitors(ticker):
    """A placeholder function to get competitor data."""
    # --- THIS IS THE CRITICAL FIX ---
    # Corrected the variable name from 'competitor_' to 'competitor_map'
    competitor_map = {
        "RELIANCE": ["TCS", "INFY", "BHARTIARTL"],
        "TCS": ["INFY", "WIPRO", "HCLTECH"],
        "HDFCBANK": ["ICICIBANK", "SBIN", "KOTAKBANK"]
    }
    # --- END FIX ---
    return competitor_map.get(ticker.upper(), [])