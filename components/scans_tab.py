from dash import dcc, html, dash_table

def create_scans_tab(pivot_points, graham_scan):
    """Creates the content for the Scans tab."""
    
    return html.Div([
        html.H3('Pivot Points'),
        dash_table.DataTable(
            data=[{'Level': k, 'Price': f"{v:.2f}"} for k, v in pivot_points.items()],
            columns=[{'name': 'Level', 'id': 'Level'}, {'name': 'Price', 'id': 'Price'}]
        ),
        html.Br(),
        html.H3('Graham Value Scan'),
        dash_table.DataTable(
            data=[{'Metric': k, 'Value': v} for k, v in graham_scan.items()],
            columns=[{'name': 'Metric', 'id': 'Metric'}, {'name': 'Value', 'id': 'Value'}]
        )
    ])