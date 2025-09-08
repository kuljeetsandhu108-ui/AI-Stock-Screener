import os
import google.generativeai as genai
from newsapi import NewsApiClient
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv

load_dotenv()

# Configure APIs
genai.configure(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))
newsapi = NewsApiClient(api_key=os.getenv("NEWS_API_KEY"))

def get_ai_company_report(company_name, news_articles):
    """Generates a comprehensive AI report using Google Gemini."""
    if not news_articles:
        return "Not enough recent news to generate a report."
    
    # Combine headlines for the prompt
    headlines = "\n".join([f"- {article['title']}" for article in news_articles[:10]])
    
    prompt = f"""
    Analyze the current state of {company_name} based on the following recent news headlines:
    {headlines}

    Based on these headlines and your general knowledge, provide a detailed report covering these points:
    1.  **Overall Company Sentiment:** Is the current sentiment positive, negative, or neutral?
    2.  **Key Developments:** What are the most significant recent events or news?
    3.  **Potential Strengths & Weaknesses:** What are the potential strengths and weaknesses highlighted by the news?
    4.  **Future Outlook:** Based on this information, what is the potential future outlook for the company?

    Provide a concise, well-structured report.
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating Gemini report: {e}")
        return "Could not generate AI report at this time."

def get_stock_news(query):
    """Fetches news articles for a given stock query."""
    try:
        all_articles = newsapi.get_everything(
            q=query,
            language='en',
            sort_by='publishedAt',
            page_size=20
        )
        return all_articles['articles']
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

def analyze_sentiment(text):
    """Analyzes the sentiment of a piece of text using VADER."""
    analyzer = SentimentIntensityAnalyzer()
    sentiment = analyzer.polarity_scores(text)
    
    # Classify sentiment based on compound score
    if sentiment['compound'] >= 0.05:
        return 'Positive', sentiment['compound']
    elif sentiment['compound'] <= -0.05:
        return 'Negative', sentiment['compound']
    else:
        return 'Neutral', sentiment['compound']