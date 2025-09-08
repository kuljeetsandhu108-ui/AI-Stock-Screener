from dash import html, dash_table
import data_processor as dp # We need this to get competitor info

def create_competitors_tab(competitors_list):
    """Creates the content for the Competitors tab."""
    
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
        dash_table.DataTable(
            data=competitor_data,
            columns=[{'name': i, 'id': i} for i in ['Ticker', 'Market Cap', 'P/E Ratio']]
        )
    ])