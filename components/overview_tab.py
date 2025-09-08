from dash import dcc, html, dash_table
import plotly.graph_objects as go

def create_overview_tab(summary, fundamentals, hist_df):
    """Creates the content for the Overview tab."""
    
    price_chart = go.Figure(data=[go.Candlestick(
        x=hist_df.index, open=hist_df['open'], high=hist_df['high'],
        low=hist_df['low'], close=hist_df['close']
    )])
    price_chart.update_layout(title=f"Price Chart", xaxis_rangeslider_visible=False)
    
    return html.Div([
        html.H3('Company Overview'),
        html.P(summary),
        html.H3('Key Fundamentals'),
        dash_table.DataTable(
            data=[{'Metric': k, 'Value': f"{v:,.2f}" if isinstance(v, (int, float)) else v} for k, v in fundamentals.items() if v is not None],
            columns=[{'name': 'Metric', 'id': 'Metric'}, {'name': 'Value', 'id': 'Value'}]
        ),
        dcc.Graph(figure=price_chart)
    ])