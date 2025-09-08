import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

import data_processor as dp
import ai_services as ai

app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

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
            hist_df.columns = hist_df.columns.get_level_values(0)
        # Now, standardize all column names to lowercase.
        hist_df.columns = [str(col).lower() for col in hist_df.columns]
        # --- END FIX ---

        tech_df = dp.calculate_technical_indicators(hist_df.copy())
        pivot_points = dp.calculate_pivot_points(hist_df.copy())
        graham_scan = dp.run_graham_scan(ticker)
        news_articles = ai.get_stock_news(f"{ticker} India")
        ai_report = ai.get_ai_company_report(ticker, news_articles)
        competitors = dp.get_competitors(ticker)

        print("--- DATA FETCHING COMPLETE ---")

        price_chart = go.Figure(data=[go.Candlestick(
            x=hist_df.index, open=hist_df['open'], high=hist_df['high'],
            low=hist_df['low'], close=hist_df['close']
        )])
        price_chart.update_layout(title=f'{ticker} Price Chart', xaxis_rangeslider_visible=False)

        overview_tab = html.Div([
            html.H3('Company Overview'), html.P(summary),
            html.H3('Key Fundamentals'),
            dash_table.DataTable(
                data=[{'Metric': k, 'Value': f"{v:,.2f}" if isinstance(v, (int, float)) else v} for k, v in fundamentals.items() if v is not None],
                columns=[{'name': 'Metric', 'id': 'Metric'}, {'name': 'Value', 'id': 'Value'}]
            ),
            dcc.Graph(figure=price_chart)
        ])

        price_chart_tech = go.Figure(price_chart)
        # After pandas-ta runs, the new columns are uppercase. We must access them with uppercase names.
        price_chart_tech.add_trace(go.Scatter(x=tech_df.index, y=tech_df['EMA_50'], mode='lines', name='50-Day EMA', line={'color': 'orange'}))
        price_chart_tech.add_trace(go.Scatter(x=tech_df.index, y=tech_df['EMA_200'], mode='lines', name='200-Day EMA', line={'color': 'purple'}))
        rsi_chart = go.Figure(go.Scatter(x=tech_df.index, y=tech_df['RSI_14'], mode='lines', name='RSI'))
        rsi_chart.update_layout(title='Relative Strength Index (RSI)')
        technicals_tab = html.Div([dcc.Graph(figure=price_chart_tech), dcc.Graph(figure=rsi_chart)])

        scans_tab = html.Div([
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

        news_elements = [html.Div([
            html.H5(html.A(a['title'], href=a['url'], target='_blank')),
            html.P(f"Sentiment: {ai.analyze_sentiment(a['title'])[0]}", className=f"{ai.analyze_sentiment(a['title'])[0].lower()}-sentiment")
        ], className='news-item') for a in news_articles]
        avg_sentiment = sum(ai.analyze_sentiment(a['title'])[1] for a in news_articles) / len(news_articles) if news_articles else 0
        news_tab = html.Div([
            dcc.Graph(figure=go.Figure(go.Indicator(
                mode="gauge+number", value=avg_sentiment, title={'text': "Overall News Sentiment"},
                gauge={'axis': {'range': [-1, 1]}, 'steps': [
                    {'range': [-1, -0.05], 'color': "#EA4335"}, {'range': [-0.05, 0.05], 'color': "#FBBC04"},
                    {'range': [0.05, 1], 'color': "#34A853"}]}))),
            html.Hr(), *news_elements
        ])
        
        competitor_data = []
        for ct in competitors:
            cf, _ = dp.get_stock_info(ct)
            mc, pe = cf.get('Market Cap'), cf.get('P/E Ratio')
            competitor_data.append({
                'Ticker': ct,
                'Market Cap': f"{mc / 1e7:,.2f} Cr" if mc else "N/A",
                'P/E Ratio': f"{pe:.2f}" if pe else "N/A"
            })
        competitors_tab = html.Div([
            html.H3('Competitor Analysis'),
            dash_table.DataTable(data=competitor_data, columns=[{'name': i, 'id': i} for i in ['Ticker', 'Market Cap', 'P/E Ratio']])
        ])

        return html.Div(className='tab-content', children=[
            dcc.Tabs(id="main-tabs-final", children=[
                dcc.Tab(label='Overview', children=overview_tab),
                dcc.Tab(label='Technicals', children=technicals_tab),
                dcc.Tab(label='Scans', children=scans_tab),
                dcc.Tab(label='AI Report', children=html.Div(dcc.Markdown(ai_report), style={'padding': '20px'})),
                dcc.Tab(label='News & Sentiment', children=news_tab),
                dcc.Tab(label='Competitors', children=competitors_tab),
            ])
        ])

    except Exception as e:
        print(f"--- AN UNHANDLED ERROR OCCURRED ---")
        import traceback
        traceback.print_exc()
        return html.Div(f"An error occurred: {e}. Please check the ticker symbol and your API keys. More details in the terminal.")

if __name__ == '__main__':
    app.run(debug=True)