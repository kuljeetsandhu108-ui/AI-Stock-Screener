from dash import dcc, html

def create_ai_report_tab(ai_report):
    """Creates the content for the AI Report tab."""
    
    return html.Div(
        dcc.Markdown(ai_report), 
        style={'padding': '20px', 'whiteSpace': 'pre-wrap'}
    )