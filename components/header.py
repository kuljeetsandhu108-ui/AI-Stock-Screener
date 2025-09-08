from dash import dcc, html

def create_header():
    """Creates the header section of the dashboard."""
    return html.Div([
        html.H1("AI-Powered Indian Stock Screener"),
        html.P("Enter an NSE stock ticker (e.g., RELIANCE, TCS, HDFCBANK)"),
        dcc.Input(id='stock-input', type='text', value='RELIANCE', style={'marginRight': '10px'}),
        html.Button('Analyze', id='submit-button', n_clicks=0),
    ], className='header')