from dash import dcc, html
import plotly.graph_objects as go

def create_technicals_tab(tech_df):
    """Creates the content for the Technicals tab."""
    
    price_chart_with_indicators = go.Figure(data=[go.Candlestick(
        x=tech_df.index, open=tech_df['open'], high=tech_df['high'],
        low=tech_df['low'], close=tech_df['close']
    )])
    price_chart_with_indicators.add_trace(go.Scatter(x=tech_df.index, y=tech_df['ema_50'], mode='lines', name='50-Day EMA', line={'color': 'orange'}))
    price_chart_with_indicators.add_trace(go.Scatter(x=tech_df.index, y=tech_df['ema_200'], mode='lines', name='200-Day EMA', line={'color': 'purple'}))
    price_chart_with_indicators.update_layout(title=f"Price Chart with Indicators", xaxis_rangeslider_visible=False)

    rsi_chart = go.Figure(go.Scatter(x=tech_df.index, y=tech_df['rsi_14'], mode='lines', name='RSI'))
    rsi_chart.update_layout(title='Relative Strength Index (RSI)')
    
    return html.Div([
        dcc.Graph(figure=price_chart_with_indicators),
        dcc.Graph(figure=rsi_chart)
    ])