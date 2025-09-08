from dash import dcc, html
import plotly.graph_objects as go
import ai_services as ai # We need this to call the sentiment function

def create_news_tab(news_articles):
    """Creates the content for the News & Sentiment tab."""
    
    if not news_articles:
        return html.Div("No recent news articles found.")
        
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
            mode="gauge+number",
            value=avg_sentiment,
            title={'text': "Overall News Sentiment"},
            gauge={
                'axis': {'range': [-1, 1]},
                'bar': {'color': "#CCCCCC"},
                'steps': [
                    {'range': [-1, -0.05], 'color': "#EA4335"},
                    {'range': [-0.05, 0.05], 'color': "#FBBC04"},
                    {'range': [0.05, 1], 'color': "#34A853"}
                ]
            }
        ))),
        html.Hr(),
        *news_elements
    ])