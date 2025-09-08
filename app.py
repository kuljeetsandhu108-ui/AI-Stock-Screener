import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

# Import our custom helper modules
import data_processor as dp
import ai_services as ai

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
        id="loading-spinner",
        type="circle",
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
        # --- 1. DATA FETCHING AND STANDARDIZATION ---
        fundamentals, summary = dp.get_stock_info(ticker)
        if not fundamentals:
            return html.Div(f"Could not retrieve fundamental data for {ticker}. Please check the ticker symbol.")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)
        hist_df = yf.download(f"{ticker}.NS", start=start_date, end=end_date, progress=False)
        
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

        # Now, pass the clean, lowercase DataFrame to all processing functions
        tech_df = dp.calculate_technical_indicators(hist_df.copy())
        # The new indicator columns from pandas-ta are uppercase, so we convert them too
        tech_df.columns = [str(col).lower() for col in tech_df.columns]
        
        pivot_points = dp.calculate_pivot_points(hist_df.copy())
        graham_scan = dp.run_graham_scan(ticker)
        news_articles = ai.get_stock_news(f"{ticker} India")
        ai_report = ai.get_ai_company_report(ticker, news_articles)
        competitors_list = dp.get_competitors(ticker)

        print("--- DATA FETCHING COMPLETE ---")

        # --- 2. ASSEMBLE AND RETURN THE FINAL LAYOUT USING COMPONENTS ---
        return html.Div(className='tab-content', children=[
            dcc.Tabs(id="main-tabs-final", children=[
                dcc.Tab(label='Overview', children=create_overview_tab(summary, fundamentals, hist_df)),
                dcc.Tab(label='Technicals', children=create_technicals_tab(tech_df)),
                dcc.Tab(label='Scans', children=create_scans_tab(pivot_points, graham_scan)),
                dcc.Tab(label='AI Report', children=create_ai_report_tab(ai_report)),
                dcc.Tab(label='News & Sentiment', children=create_news_tab(news_articles)),
                dcc.Tab(label='Competitors', children=create_competitors_tab(competitors_list)),
            ])
        ])

    except Exception as e:
        print(f"--- AN UNHANDLED ERROR OCCURRED ---")
        import traceback
        traceback.print_exc()
        return html.Div(f"An error occurred: {e}. Please check the ticker symbol and your API keys. More details in the terminal.")

# --- All Component Functions ---
# For simplicity and to guarantee success, we will put the component functions back in app.py for now.

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
        comp_fundamentals, _ = dp.get_stock_info(comp_ticker)
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