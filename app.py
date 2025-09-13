import dash
from dash import dcc, html, dash_table, no_update
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
import pandas_ta as ta # Import pandas_ta here
import yfinance as yf

import ai_services as ai # We still use this

# --- All Helper Functions are now INSIDE app.py ---

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
    # --- THE CRITICAL FIX IS NOW DIRECTLY IN THIS FILE ---
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
    competitor_map = {
        "RELIANCE": ["TCS", "INFY", "BHARTIARTL"],
        "TCS": ["INFY", "WIPRO", "HCLTECH"],
        "HDFCBANK": ["ICICIBANK", "SBIN", "KOTAKBANK"]
    }
    return competitor_map.get(ticker.upper(), [])

# --- Main App Initialization ---
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# --- Application Layout ---
app.layout = html.Div([
    html.Div([
        html.H1("AI-Powered Indian Stock Screener"),
        html.P("Enter an NSE stock ticker (e.g., RELIANCE, TCS, HDFCBANK)"),
        dcc.Input(id='stock-input', type='text', value='RELIANCE', style={'marginRight': '10px'}),
        html.Button('Analyze', id='submit-button', n_clicks=0),
    ], className='header'),
    dcc.Loading(
        id="loading-spinner", type="circle",
        children=html.Div(id='dashboard-content', style={'marginTop': '20px'})
    )
], style={'padding': '20px'})


# --- The Single Main Callback ---
@app.callback(
    Output('dashboard-content', 'children'),
    Input('submit-button', 'n_clicks'),
    State('stock-input', 'value')
)
def update_dashboard(n_clicks, ticker):
    if n_clicks == 0:
        return html.Div("Please enter a stock ticker and click 'Analyze'.")

    print(f"--- FETCHING ALL DATA FOR {ticker} ---")
    ticker = ticker.upper()

    try:
        fundamentals, summary = get_stock_info(ticker)
        if not fundamentals:
            return html.Div(f"Could not retrieve fundamental data for {ticker}. Please check the ticker symbol.")

        hist_df = yf.download(f"{ticker}.NS", period="2y", progress=False)
        if hist_df.empty:
            return html.Div(f"Could not retrieve historical price data for {ticker}.")

        # --- THE DEFINITIVE FIX FOR ALL COLUMN ERRORS ---
        # This handles both simple columns and complex "MultiIndex" columns from yfinance.
        if isinstance(hist_df.columns, pd.MultiIndex):
            # If it's a MultiIndex, take the first level, e.g., ('Close', 'RELIANCE.NS') -> 'Close'
            hist_df.columns = hist_df.columns.get_level_values(0)
        
        # Now, standardize all column names to lowercase.
        hist_df.columns = [str(col).lower() for col in hist_df.columns]
        # --- END FIX ---

        tech_df = calculate_technical_indicators(hist_df.copy())
        tech_df.columns = [str(col).lower() for col in tech_df.columns]
        
        pivot_points = calculate_pivot_points(hist_df.copy())
        graham_scan = run_graham_scan(ticker)
        news_articles = ai.get_stock_news(f"{ticker} India")
        ai_report = ai.get_ai_company_report(ticker, news_articles)
        competitors = get_competitors(ticker)

        print("--- DATA FETCHING COMPLETE ---")
        
        # --- ASSEMBLE AND RETURN THE FINAL LAYOUT (with Live Ticker) ---
        return html.Div([
            html.Div([
                html.H2(f"{ticker} - {fundamentals.get('Sector', '')}", style={'flexGrow': 1}),
                html.Div(id='live-price-container', children="Fetching live price...")
            ], style={'display': 'flex', 'alignItems': 'center', 'padding': '10px', 'border': '1px solid #ddd', 'borderRadius': '5px', 'marginBottom': '20px'}),
            
            html.Div(className='tab-content', children=[
                dcc.Tabs(id="main-tabs-final", children=[
                    dcc.Tab(label='Overview', children=create_overview_tab(summary, fundamentals, hist_df)),
                    dcc.Tab(label='Technicals', children=create_technicals_tab(tech_df)),
                    dcc.Tab(label='Scans', children=create_scans_tab(pivot_points, graham_scan)),
                    dcc.Tab(label='AI Report', children=create_ai_report_tab(ai_report)),
                    dcc.Tab(label='News & Sentiment', children=create_news_tab(news_articles)),
                    dcc.Tab(label='Competitors', children=create_competitors_tab(competitors)),
                ])
            ]),
            
            dcc.Interval(
                id='live-price-interval', interval=3 * 1000, n_intervals=0
            )
        ])

    except Exception as e:
        print(f"--- AN UNHANDLED ERROR OCCURRED ---")
        import traceback
        traceback.print_exc()
        return html.Div(f"An error occurred: '{e}'. Please check the ticker symbol and your API keys. More details in the terminal.")

# --- NEW: CALLBACK FOR LIVE PRICE UPDATES ---
@app.callback(
    Output('live-price-container', 'children'),
    Input('live-price-interval', 'n_intervals'),
    State('stock-input', 'value')
)
def update_live_price(n, ticker):
    if not ticker:
        return no_update

    try:
        # We use the full .info call here as it's more reliable for closing prices
        stock_info = yf.Ticker(f"{ticker.upper()}.NS").info
        
        # Try multiple keys to find the price, starting with the most likely
        live_price = stock_info.get('currentPrice')
        previous_close = stock_info.get('previousClose')

        # --- NEW BULLETPROOF LOGIC ---
        display_price = None
        price_label = ""
        change = 0

        if live_price is not None:
            # We have a live price
            display_price = live_price
            change = display_price - previous_close if previous_close else 0
        elif previous_close is not None:
            # No live price, but we have the last close
            display_price = previous_close
            price_label = "Last Close: "
            change = 0 # Change is zero when showing closing price
        
        if display_price is None:
            # If we still have no price, show a clear message
            return html.P("Price data not available.", style={'color': 'gray', 'margin': 0, 'marginLeft': 'auto'})
        # --- END LOGIC ---

        change_percent = (change / previous_close) * 100 if previous_close else 0
        
        color = '#34A853' if change >= 0 else '#EA4335'
        symbol = '▲' if change >= 0 else '▼'

        return html.Div([
            html.H2(f"{price_label}₹{display_price:,.2f}", style={'margin': 0, 'marginRight': '20px'}),
            html.H3(
                f"{symbol} {change:,.2f} ({change_percent:.2f}%)",
                style={'color': color, 'margin': 0}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'textAlign': 'right', 'marginLeft': 'auto'})

    except Exception:
        return html.P("Price data not available.", style={'color': 'orange', 'margin': 0, 'marginLeft': 'auto'})


# --- All Component Creation Functions (Now safely inside app.py) ---
def create_overview_tab(summary, fundamentals, hist_df):
    price_chart = go.Figure(data=[go.Candlestick(
        x=hist_df.index, open=hist_df['open'], high=hist_df['high'],
        low=hist_df['low'], close=hist_df['close']
    )])
    price_chart.update_layout(title=f"Price Chart", xaxis_rangeslider_visible=False)
    return html.Div([
        html.H3('Company Overview'), html.P(summary),
        html.H3('Key Fundamentals'),
        dash_table.DataTable(
            data=[{'Metric': k, 'Value': f"{v:,.2f}" if isinstance(v, (int, float)) else v} for k, v in fundamentals.items() if v is not None],
            columns=[{'name': 'Metric', 'id': 'Metric'}, {'name': 'Value', 'id': 'Value'}]
        ),
        dcc.Graph(figure=price_chart)
    ])

def create_technicals_tab(tech_df):
    price_chart_with_indicators = go.Figure(data=[go.Candlestick(
        x=tech_df.index, open=tech_df['open'], high=tech_df['high'],
        low=tech_df['low'], close=tech_df['close']
    )])
    price_chart_with_indicators.add_trace(go.Scatter(x=tech_df.index, y=tech_df['ema_50'], mode='lines', name='50-Day EMA', line={'color': 'orange'}))
    price_chart_with_indicators.add_trace(go.Scatter(x=tech_df.index, y=tech_df['ema_200'], mode='lines', name='200-Day EMA', line={'color': 'purple'}))
    price_chart_with_indicators.update_layout(title=f"Price Chart with Indicators", xaxis_rangeslider_visible=False)
    rsi_chart = go.Figure(go.Scatter(x=tech_df.index, y=tech_df['rsi_14'], mode='lines', name='RSI'))
    rsi_chart.update_layout(title='Relative Strength Index (RSI)')
    return html.Div([dcc.Graph(figure=price_chart_with_indicators), dcc.Graph(figure=rsi_chart)])

def create_scans_tab(pivot_points, graham_scan):
    return html.Div([
        html.H3('Pivot Points'),
        dash_table.DataTable(
            data=[{'Level': k, 'Price': f"{v:.2f}"} for k, v in pivot_points.items()],
            columns=[{'name': 'Level', 'id': 'Level'}, {'name': 'Price', 'id': 'Price'}]
        ),
        html.Br(), html.H3('Graham Value Scan'),
        dash_table.DataTable(
            data=[{'Metric': k, 'Value': v} for k, v in graham_scan.items()],
            columns=[{'name': 'Metric', 'id': 'Metric'}, {'name': 'Value', 'id': 'Value'}]
        )
    ])

def create_ai_report_tab(ai_report):
    return html.Div(dcc.Markdown(ai_report), style={'padding': '20px', 'whiteSpace': 'pre-wrap'})

def create_news_tab(news_articles):
    if not news_articles: return html.Div("No recent news articles found.")
    news_elements = []
    total_sentiment_score = 0
    for article in news_articles:
        sentiment, score = ai.analyze_sentiment(article['title'])
        total_sentiment_score += score
        news_elements.append(html.Div([
            html.H5(html.A(article['title'], href=article['url'], target='_blank')),
            html.P(f"Sentiment: {sentiment}", className=f"{sentiment.lower()}-sentiment")
        ], className='news-item'))
    avg_sentiment = total_sentiment_score / len(news_articles)
    return html.Div([
        dcc.Graph(figure=go.Figure(go.Indicator(
            mode="gauge+number", value=avg_sentiment, title={'text': "Overall News Sentiment"},
            gauge={'axis': {'range': [-1, 1]}, 'steps': [
                {'range': [-1, -0.05], 'color': "#EA4335"}, {'range': [-0.05, 0.05], 'color': "#FBBC04"},
                {'range': [0.05, 1], 'color': "#34A853"}]}))),
        html.Hr(), *news_elements
    ])

def create_competitors_tab(competitors_list):
    competitor_data = []
    for comp_ticker in competitors_list:
        comp_fundamentals, _ = get_stock_info(comp_ticker)
        market_cap = comp_fundamentals.get('Market Cap')
        pe_ratio = comp_fundamentals.get('P/E Ratio')
        competitor_data.append({
            'Ticker': comp_ticker,
            'Market Cap': f"{market_cap / 1_00_00_000:,.2f} Cr" if market_cap else "N/A",
            'P/E Ratio': f"{pe_ratio:.2f}" if pe_ratio else "N/A"
        })
    return html.Div([
        html.H3('Competitor Analysis'),
        dash_table.DataTable(data=competitor_data, columns=[{'name': i, 'id': i} for i in ['Ticker', 'Market Cap', 'P/E Ratio']])
    ])

# --- Main execution block ---
if __name__ == '__main__':
    app.run(debug=True)