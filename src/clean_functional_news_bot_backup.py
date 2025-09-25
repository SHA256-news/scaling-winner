#!/usr/bin/env python3
"""
CLEAN FUNCTIONAL NEWS BOT
Ultra-simple, working implementation using real packages
"""

import os
import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional

def test_dependencies():
    """Test if all required packages are available"""
    try:
        import google.generativeai as genai
        from eventregistry import EventRegistry, QueryArticlesIter
        return True, genai, EventRegistry, QueryArticlesIter
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Install with: pip install -r clean_requirements.txt")
        return False, None, None, None

def fetch_simple_news(event_registry_key: str, keyword: str = "AI", max_articles: int = 3) -> List[Dict]:
    """Fetch news using EventRegistry 9.1"""
    try:
        from eventregistry import EventRegistry, QueryArticlesIter
        
        er = EventRegistry(apiKey=event_registry_key)
        
        # Create query using v9.1 patterns
        q = QueryArticlesIter(
            keywords=keyword,
            lang='eng',
            dateStart=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            dateEnd=datetime.now().strftime('%Y-%m-%d')
        )
        
        articles = []
        count = 0
        
        for article in q.execQuery(er, sortBy="date", maxItems=max_articles):
            if count >= max_articles:
                break
                
            articles.append({
                'title': article.get('title', 'No title'),
                'body': article.get('body', 'No content')[:500] + '...',
                'source': article.get('source', {}).get('title', 'Unknown source'),
                'url': article.get('url', ''),
                'date': article.get('date', '')
            })
            count += 1
            
        return articles
        
    except Exception as e:
        print(f"❌ Error fetching news: {e}")
        return []

def generate_simple_summary(google_key: str, articles: List[Dict]) -> str:
    """Generate summary using Google Generative AI"""
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=google_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Create prompt
        articles_text = "\n\n".join([
            f"Title: {art['title']}\nSource: {art['source']}\nContent: {art['body']}"
            for art in articles
        ])
        
        prompt = f"""
        Create a brief news summary from these articles:
        
        {articles_text}
        
        Write a 2-3 paragraph summary highlighting the key points.
        """
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        return "Could not generate summary"

def demo_mode():
    """Demo mode when API keys are not available"""
    print("\n📋 Demo News Articles Structure:\n")
    
    demo_articles = [
        {
            "title": "AI Breakthrough in Healthcare",
            "source": "Tech News",
            "body": "Major advancement in AI-powered medical diagnostics..."
        },
        {
            "title": "New Machine Learning Framework",
            "source": "Dev Today", 
            "body": "Revolutionary ML framework promises faster training..."
        }
    ]
    
    for i, article in enumerate(demo_articles, 1):
        print(f"{i}. {article['title']}")
        print(f"   Source: {article['source']}\n")
    
    print("💡 To use real APIs:")
    print("   export GOOGLE_API_KEY='your-key'")
    print("   export EVENTREGISTRY_API_KEY='your-key'")
    print("   python3 clean_functional_news_bot.py")

def main():
    """Main function - works with or without API keys"""
    print("🤖 CLEAN FUNCTIONAL NEWS BOT")
    print("=" * 40)
    
    # Test imports first
    try:
        import google.generativeai as genai
        from eventregistry import EventRegistry, QueryArticlesIter
        print("✅ All packages imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Check API keys
    google_key = os.getenv('GOOGLE_API_KEY')
    event_key = os.getenv('EVENTREGISTRY_API_KEY')
    
    # Debug secret availability in GitHub Actions
    print("\n� Secret availability check:")
    if google_key:
        print(f"✅ GOOGLE_API_KEY found ({len(google_key)} chars)")
    else:
        print("❌ GOOGLE_API_KEY not found")
        
    if event_key:
        print(f"✅ EVENTREGISTRY_API_KEY found ({len(event_key)} chars)")
    else:
        print("❌ EVENTREGISTRY_API_KEY not found")
    
    if not google_key or not event_key:
        print("\n⚠️ API keys not set. Using demo mode...")
        print("💡 In GitHub Actions, ensure secrets are properly configured:")
        print("   - Go to Settings > Secrets and variables > Actions")
        print("   - Add GOOGLE_API_KEY and EVENTREGISTRY_API_KEY")
        demo_mode()
        return True

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)