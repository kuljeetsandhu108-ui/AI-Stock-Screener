import dash
from dash import dcc, html, dash_table, no_update
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import traceback

import ai_services as ai

# --- All Helper Functions are now INSIDE app.py to guarantee they are the correct version ---

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
    """Calculates technical indicators. Expects lowercase columns."""
    if df.empty: return pd.DataFrame()
    df.ta.rsi(append=True); df.ta.macd(append=True); df.ta.bbands(append=True)
    df.ta.ema(length=50, append=True); df.ta.ema(length=200, append=True)
    return df

def run_graham_scan(ticker):
    """Performs a basic Benjamin Graham value scan."""
    try:
        info = yf.Ticker(f"{ticker}.NS").info
        pe, pb = info.get('trailingPE'), info.get('priceToBook')
        if pe is None or pb is None: return {"Verdict": "Not enough data"}
        verdict = "Potentially Undervalued" if pe < 15 and pb < 1.5 else "Not Meeting Graham Criteria"
        return {"P/E Ratio": f"{pe:.2f}", "P/B Ratio": f"{pb:.2f}", "Verdict": verdict}
    except Exception:
        return {}

def calculate_pivot_points(df):
    """Calculates standard pivot points. This version correctly expects lowercase columns."""
    if df.empty or len(df) < 2: return {}
    last = df.iloc[-2]
    high, low, close = last['high'], last['low'], last['close']
    pivot = (high + low + close) / 3
    return {"R2": pivot + (high-low), "R1": 2*pivot - low, "Pivot": pivot, "S1": 2*pivot - high, "S2": pivot - (high-low)}

def get_competitors(ticker):
    """A placeholder function to get competitor data."""
    competitor_map = {"RELIANCE": ["TCS", "INFY"], "TCS": ["INFY", "WIPRO"], "HDFCBANK": ["ICICIBANK", "SBIN"]}
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

    dcc.Store(id='ticker-store'),
    html.Div(id='market-pulse-display', style={'marginTop': '20px'}),
    html.Div(id='live-price-display', style={'marginTop': '10px'}),
    dcc.Loading(
        id="loading-spinner", type="circle",
        children=html.Div(id='dashboard-tabs-content')
    ),
    dcc.Interval(id='global-interval-timer', interval=5 * 1000, n_intervals=0)
], style={'padding': '20px'})


# --- Callback 1: Fetch data for the main dashboard ---
@app.callback(
    Output('dashboard-tabs-content', 'children'),
    Output('ticker-store', 'data'),
    Input('submit-button', 'n_clicks'),
    State('stock-input', 'value')
)
def update_dashboard_tabs(n_clicks, ticker):
    if n_clicks == 0:
        return html.Div("Please enter a stock ticker and click 'Analyze'."), ""

    print(f"--- FETCHING ALL DATA FOR {ticker} ---")
    ticker = ticker.upper()

    try:
        fundamentals, summary = get_stock_info(ticker)
        if not fundamentals:
            return html.Div(f"Could not retrieve fundamental data for {ticker}."), ticker

        hist_df = yf.download(f"{ticker}.NS", period="2y", progress=False)
        if hist_df.empty:
            return html.Div(f"Could not retrieve historical data for {ticker}."), ticker

        if isinstance(hist_df.columns, pd.MultiIndex):
            hist_df.columns = hist_df.columns.get_level_values(0)
        hist_df.columns = [str(col).lower() for col in hist_df.columns]
        
        tech_df = calculate_technical_indicators(hist_df.copy())
        tech_df.columns = [str(col).lower() for col in tech_df.columns]
        
        pivot_points = calculate_pivot_points(hist_df.copy())
        graham_scan = run_graham_scan(ticker)
        news_articles = ai.get_stock_news(f"{ticker} India")
        ai_report = ai.get_ai_company_report(ticker, news_articles)
        competitors = get_competitors(ticker)

        print("--- DATA FETCHING COMPLETE ---")

        overview_tab = create_overview_tab(summary, fundamentals, hist_df, ticker)
        technicals_tab = create_technicals_tab(tech_df, ticker)
        scans_tab = create_scans_tab(pivot_points, graham_scan)
        ai_report_tab = create_ai_report_tab(ai_report)
        news_tab = create_news_tab(news_articles)
        competitors_tab = create_competitors_tab(competitors)
        
        return html.Div(className='tab-content', children=[
            dcc.Tabs(id="main-tabs-final", children=[
                dcc.Tab(label='Overview', children=overview_tab),
                dcc.Tab(label='Technicals', children=technicals_tab),
                dcc.Tab(label='Scans', children=scans_tab),
                dcc.Tab(label='AI Report', children=ai_report_tab),
                dcc.Tab(label='News & Sentiment', children=news_tab),
                dcc.Tab(label='Competitors', children=competitors_tab),
            ])
        ]), ticker

    except Exception as e:
        traceback.print_exc()
        return html.Div(f"An error occurred: '{e}'."), ticker


# --- Callback 2: Update the live stock price display ---
@app.callback(
    Output('live-price-display', 'children'),
    Input('global-interval-timer', 'n_intervals'),
    State('ticker-store', 'data')
)
def update_live_price(n, ticker):
    if not ticker:
        return html.Div()

    try:
        stock_info = yf.Ticker(f"{ticker}.NS").info
        live_price = stock_info.get('currentPrice')
        previous_close = stock_info.get('previousClose')
        display_price = live_price if live_price is not None else previous_close
        if display_price is None: return html.Div()

        change = 0
        price_label = "Last Close: "
        if live_price is not None and previous_close is not None:
            change = display_price - previous_close
            price_label = ""
        
        change_percent = (change / previous_close) * 100 if previous_close else 0
        color = '#34A853' if change >= 0 else '#EA4335'
        symbol = '▲' if change >= 0 else '▼'

        return html.Div([
            html.H2(f"{ticker}", style={'flexGrow': 1}),
            html.H2(f"{price_label}₹{display_price:,.2f}", style={'margin': 0, 'marginRight': '20px'}),
            html.H3(f"{symbol} {change:,.2f} ({change_percent:.2f}%)", style={'color': color, 'margin': 0})
        ], style={'display': 'flex', 'alignItems': 'center', 'padding': '10px', 'border': '1px solid #ddd', 'borderRadius': '5px'})

    except Exception:
        return html.Div()


# --- Callback 3: Update Market Pulse Indices ---
@app.callback(
    Output('market-pulse-display', 'children'),
    Input('global-interval-timer', 'n_intervals')
)
def update_market_pulse(n):
    indices = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN"}
    cards = []
    try:
        data = yf.download(tickers=list(indices.values()), period="2d", progress=False)
        for name, symbol in indices.items():
            price = data['Close'][symbol].iloc[-1]
            prev_close = data['Close'][symbol].iloc[-2]
            change = price - prev_close
            change_percent = (change / prev_close) * 100
            color = '#34A853' if change >= 0 else '#EA4335'
            symbol_char = '▲' if change >= 0 else '▼'
            card = html.Div([
                html.H4(name, style={'margin': 0, 'color': '#555'}),
                html.H3(f"{price:,.2f}", style={'margin': 0}),
                html.P(f"{symbol_char} {change:,.2f} ({change_percent:.2f}%)", style={'color': color, 'margin': 0})
            ], className="mini-card", style={'padding': '15px', 'border': '1px solid #ddd', 'borderRadius': '5px', 'textAlign': 'center', 'backgroundColor': '#f9f9f9'})
            cards.append(card)
        return html.Div(cards, style={'display': 'grid', 'gridTemplateColumns': 'repeat(3, 1fr)', 'gap': '20px'})
    except Exception as e:
        print(f"Error fetching market pulse: {e}")
        return html.Div()


# --- Component Creation Functions (Safely inside app.py) ---
def create_overview_tab(summary, fundamentals, hist_df, ticker):
    price_chart = go.Figure(data=[go.Candlestick(x=hist_df.index, open=hist_df['open'], high=hist_df['high'], low=hist_df['low'], close=hist_df['close'])])
    price_chart.update_layout(title=f"{ticker} Price Chart", xaxis_rangeslider_visible=False)
    return html.Div([
        html.H3('Company Overview'), html.P(summary),
        html.H3('Key Fundamentals'),
        dash_table.DataTable(data=[{'Metric': k, 'Value': f"{v:,.2f}" if isinstance(v, (int, float)) else v} for k, v in fundamentals.items() if v is not None], columns=[{'name': 'Metric', 'id': 'Metric'}, {'name': 'Value', 'id': 'Value'}]),
        dcc.Graph(figure=price_chart)
    ])

def create_technicals_tab(tech_df, ticker):
    price_chart_with_indicators = go.Figure(data=[go.Candlestick(x=tech_df.index, open=tech_df['open'], high=tech_df['high'], low=tech_df['low'], close=tech_df['close'])])
    price_chart_with_indicators.add_trace(go.Scatter(x=tech_df.index, y=tech_df['ema_50'], mode='lines', name='50-Day EMA', line={'color': 'orange'}))
    price_chart_with_indicators.add_trace(go.Scatter(x=tech_df.index, y=tech_df['ema_200'], mode='lines', name='200-Day EMA', line={'color': 'purple'}))
    price_chart_with_indicators.update_layout(title=f"{ticker} Price Chart with Indicators", xaxis_rangeslider_visible=False)
    rsi_chart = go.Figure(go.Scatter(x=tech_df.index, y=tech_df['rsi_14'], mode='lines', name='RSI'))
    rsi_chart.update_layout(title='Relative Strength Index (RSI)')
    return html.Div([dcc.Graph(figure=price_chart_with_indicators), dcc.Graph(figure=rsi_chart)])

def create_scans_tab(pivot_points, graham_scan):
    return html.Div([
        html.H3('Pivot Points'),
        dash_table.DataTable(data=[{'Level': k, 'Price': f"{v:.2f}"} for k, v in pivot_points.items()], columns=[{'name': 'Level', 'id': 'Level'}, {'name': 'Price', 'id': 'Price'}]),
        html.Br(), html.H3('Graham Value Scan'),
        dash_table.DataTable(data=[{'Metric': k, 'Value': v} for k, v in graham_scan.items()], columns=[{'name': 'Metric', 'id': 'Metric'}, {'name': 'Value', 'id': 'Value'}])
    ])

def create_ai_report_tab(ai_report):
    return html.Div(dcc.Markdown(ai_report), style={'padding': '20px', 'whiteSpace': 'pre-wrap'})

def create_news_tab(news_articles):
    if not news_articles: return html.Div("No recent news articles found.")
    news_elements = [html.Div([html.H5(html.A(a['title'], href=a['url'], target='_blank')), html.P(f"Sentiment: {ai.analyze_sentiment(a['title'])[0]}", className=f"{ai.analyze_sentiment(a['title'])[0].lower()}-sentiment")], className='news-item') for a in news_articles]
    avg_sentiment = sum(ai.analyze_sentiment(a['title'])[1] for a in news_articles) / len(news_articles) if news_articles else 0
    return html.Div([
        dcc.Graph(figure=go.Figure(go.Indicator(mode="gauge+number", value=avg_sentiment, title={'text': "Overall News Sentiment"}, gauge={'axis': {'range': [-1, 1]}, 'steps': [{'range': [-1, -0.05], 'color': "#EA4335"}, {'range': [-0.05, 0.05], 'color': "#FBBC04"}, {'range': [0.05, 1], 'color': "#34A853"}]}))),
        html.Hr(), *news_elements
    ])

def create_competitors_tab(competitors_list):
    competitor_data = []
    for comp_ticker in competitors_list:
        comp_fundamentals, _ = get_stock_info(comp_ticker)
        mc, pe = comp_fundamentals.get('Market Cap'), comp_fundamentals.get('P/E Ratio')
        competitor_data.append({'Ticker': comp_ticker, 'Market Cap': f"{mc / 1e7:,.2f} Cr" if mc else "N/A", 'P/E Ratio': f"{pe:.2f}" if pe else "N/A"})
    return html.Div([html.H3('Competitor Analysis'), dash_table.DataTable(data=competitor_data, columns=[{'name': i, 'id': i} for i in ['Ticker', 'Market Cap', 'P/E Ratio']])])


# --- Main execution block ---
if __name__ == '__main__':
    app.run(debug=True)