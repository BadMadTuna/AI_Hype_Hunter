import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("TIINGO_API_KEY")

print("--- TESTING TIINGO NEWS API ---")
try:
    news_url = "https://api.tiingo.com/tiingo/news?tickers=AAPL&limit=5"
    headers = {'Authorization': f'Token {api_key}'}
    res = requests.get(news_url, headers=headers, timeout=10)
    print(f"Status Code: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        print(f"Success! Found {len(data)} articles. First article title: {data[0].get('title', 'No Title')}")
    else:
        print(f"Error Response: {res.text}")
except Exception as e:
    print(f"Python Crash: {e}")

print("\n--- TESTING REDDIT SENTIMENT API ---")
try:
    # Testing the original URL
    reddit_url = "https://tradestie.com/api/v1/apps/reddit"
    res = requests.get(reddit_url, timeout=10)
    print(f"Status Code: {res.status_code}")
    
    if res.status_code == 200:
        data = res.json()
        print(f"Success! Found {len(data)} trending tickers. First ticker: {data[0].get('ticker')}")
    elif res.status_code in [301, 302, 308]:
        print(f"API Moved! It is redirecting to: {res.headers.get('Location')}")
    else:
        print(f"Error Response: {res.text}")
except Exception as e:
    print(f"Python Crash: {e}")