#!/usr/bin/env python3
"""
News Bot Script for GitHub Actions
Fetches news from EventRegistry API and generates articles using Gemini AI
"""

import os
import json
import time
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional

try:
    import google.generativeai as genai
    from eventregistry import *
except ImportError as e:
    print(f"❌ Missing required packages: {e}")
    print("Install with: pip install google-generativeai eventregistry")
    sys.exit(1)

class NewsFetcher:
    """Handles news fetching from EventRegistry API"""
    
    def __init__(self, api_key: str):
        self.er = EventRegistry(apiKey=api_key)
    
    def fetch_latest_news(self, keyword: str = None, category: str = None, 
                         language: str = "eng", max_articles: int = 5) -> List[Dict]:
        """Fetch latest news articles"""
        try:
            query_items = []
            
            if keyword:
                query_items.append(QueryItems.AND([keyword]))
            
            if category:
                category_map = {
                    'technology': 'dmoz/Computers',
                    'business': 'dmoz/Business', 
                    'health': 'dmoz/Health',
                    'science': 'dmoz/Science',
                    'sports': 'dmoz/Sports',
                    'politics': 'dmoz/Society/Politics'
                }
                
                if category.lower() in category_map:
                    query_items.append(QueryItems.AND([CategoryItems.OR([category_map[category.lower()]])]))
            
            # Date range: last 2 days
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=2)
            
            if query_items:
                q = QueryArticles(
                    keywords=QueryItems.AND(query_items),
                    lang=language,
                    dateStart=start_date,
                    dateEnd=end_date
                )
            else:
                q = QueryArticles(
                    lang=language,
                    dateStart=start_date, 
                    dateEnd=end_date
                )
            
            q.setRequestedResult(
                RequestArticlesInfo(
                    page=1,
                    count=max_articles,
                    articleInfo=ArticleInfoFlags(
                        title=True, body=True, url=True, date=True,
                        source=True, authors=True, categories=True
                    )
                )
            )
            
            result = self.er.execQuery(q)
            articles = []
            
            if 'articles' in result and 'results' in result['articles']:
                for article in result['articles']['results']:
                    articles.append({
                        'title': article.get('title', ''),
                        'body': article.get('body', ''),
                        'url': article.get('url', ''),
                        'date': article.get('date', ''),
                        'source': article.get('source', {}).get('title', ''),
                        'authors': article.get('authors', []),
                        'categories': [cat.get('label', '') for cat in article.get('categories', [])]
                    })
            
            return articles
            
        except Exception as e:
            print(f"❌ Error fetching news: {e}")
            return []

class ArticleGenerator:
    """Handles article generation using Gemini AI"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def generate_article(self, news_data: Dict, style: str = "professional") -> Dict:
        """Generate article from news data"""
        
        style_instructions = {
            "professional": "Use a professional, journalistic tone suitable for business publications.",
            "casual": "Write in a conversational, accessible tone for general readers.", 
            "academic": "Use a formal, analytical tone with detailed explanations."
        }
        
        prompt = f"""
        Transform the following news into a well-structured article.
        
        STYLE: {style_instructions.get(style, style_instructions['professional'])}
        
        NEWS DATA:
        Title: {news_data.get('title', 'N/A')}
        Source: {news_data.get('source', 'N/A')}
        Date: {news_data.get('date', 'N/A')}
        Content: {news_data.get('body', 'N/A')[:2000]}...
        
        Create:
        1. An engaging headline 
        2. A compelling lead paragraph
        3. Well-organized body with subheadings
        4. A conclusion
        
        Return as JSON with: headline, lead, body, conclusion, tags, word_count
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(temperature=0.7, max_output_tokens=2000)
            )
            
            article_text = response.text.strip()
            
            # Clean JSON formatting
            if article_text.startswith('```json'):
                article_text = article_text[7:-3].strip()
            elif article_text.startswith('```'):
                article_text = article_text[3:-3].strip()
            
            try:
                article_data = json.loads(article_text)
            except json.JSONDecodeError:
                # Fallback structure
                article_data = {
                    "headline": news_data.get('title', 'Generated Article'),
                    "lead": article_text[:300] + "...",
                    "body": article_text,
                    "conclusion": "",
                    "tags": news_data.get('categories', [])[:5],
                    "word_count": len(article_text.split())
                }
            
            # Add metadata
            article_data.update({
                'original_source': news_data.get('source', ''),
                'original_url': news_data.get('url', ''),
                'original_date': news_data.get('date', ''),
                'generated_at': datetime.now().isoformat()
            })
            
            return article_data
            
        except Exception as e:
            print(f"❌ Error generating article: {e}")
            return {"error": str(e)}

def save_article_to_markdown(article: Dict, filename: str = None) -> str:
    """Save article as Markdown file"""
    if "error" in article:
        return ""
    
    if not filename:
        safe_title = "".join(c for c in article.get('headline', 'article') 
                           if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
        filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    content = f"""# {article.get('headline', 'Generated Article')}
    # Pre-build conclusion section to avoid backslashes in f-string
    conclusion_section = f"## Conclusion\n\n{article.get('conclusion', '')}" if article.get('conclusion') else ""

**Generated:** {article.get('generated_at', 'N/A')}  
**Source:** {article.get('original_source', 'N/A')}  
**Word Count:** {article.get('word_count', 'N/A')}  
**Tags:** {', '.join(article.get('tags', []))}  

---

## Summary

{article.get('lead', 'N/A')}

## Article

{article.get('body', 'N/A')}

{conclusion_section}

---

*Generated by News Bot using EventRegistry API and Google Gemini*
**Original URL:** {article.get('original_url', 'N/A')}
"""
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return filename
    except Exception as e:
        print(f"❌ Error saving article: {e}")
        return ""

def main():
    """Main function for GitHub Actions"""
    
    # Get API keys from environment
    eventregistry_key = os.getenv('EVENTREGISTRY_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')
    
    if not eventregistry_key or not google_key:
        print("❌ Missing required API keys!")
        print("Set EVENTREGISTRY_API_KEY and GOOGLE_API_KEY environment variables")
        sys.exit(1)
    
    # Get parameters from GitHub Actions inputs or environment
    keyword = os.getenv('INPUT_KEYWORD', os.getenv('KEYWORD', 'artificial intelligence'))
    style = os.getenv('INPUT_STYLE', os.getenv('STYLE', 'professional'))
    category = os.getenv('INPUT_CATEGORY', os.getenv('CATEGORY', 'technology'))
    
    print(f"🤖 News Bot Starting...")
    print(f"🔍 Keyword: {keyword}")
    print(f"🎨 Style: {style}")
    print(f"📂 Category: {category}")
    
    # Initialize components
    try:
        news_fetcher = NewsFetcher(eventregistry_key)
        article_generator = ArticleGenerator(google_key)
        print("✅ APIs initialized")
    except Exception as e:
        print(f"❌ Failed to initialize APIs: {e}")
        sys.exit(1)
    
    # Generate articles
    generated_files = []
    
    # 1. Keyword-based article
    if keyword:
        print(f"\n📰 Fetching news for: {keyword}")
        news_articles = news_fetcher.fetch_latest_news(keyword=keyword, max_articles=2)
        
        for i, news in enumerate(news_articles):
            print(f"  📝 Generating article {i+1}/{len(news_articles)}")
            article = article_generator.generate_article(news, style=style)
            
            if "error" not in article:
                filename = save_article_to_markdown(
                    article, 
                    f"keyword_{keyword.replace(' ', '_')}_{i+1}_{datetime.now().strftime('%Y%m%d')}.md"
                )
                if filename:
                    generated_files.append(filename)
                    print(f"    ✅ Saved: {filename}")
            else:
                print(f"    ❌ Error: {article['error']}")
            
            time.sleep(2)  # Rate limiting
    
    # 2. Category-based articles
    print(f"\n📊 Fetching news for category: {category}")
    category_news = news_fetcher.fetch_latest_news(category=category, max_articles=3)
    
    category_articles = []
    for i, news in enumerate(category_news):
        print(f"  📝 Generating category article {i+1}/{len(category_news)}")
        article = article_generator.generate_article(news, style=style)
        
        if "error" not in article:
            filename = save_article_to_markdown(
                article,
                f"category_{category}_{i+1}_{datetime.now().strftime('%Y%m%d')}.md"
            )
            if filename:
                generated_files.append(filename)
                category_articles.append(article)
                print(f"    ✅ Saved: {filename}")
        else:
            print(f"    ❌ Error: {article['error']}")
        
        time.sleep(2)  # Rate limiting
    
    # 3. Generate summary report
    if category_articles:
        summary_data = {
            "date": datetime.now().strftime('%Y-%m-%d'),
            "keyword": keyword,
            "category": category,
            "style": style,
            "articles_generated": len(generated_files),
            "files": generated_files,
            "articles": category_articles
        }
        
        summary_filename = f"news_summary_{datetime.now().strftime('%Y%m%d')}.json"
        try:
            with open(summary_filename, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Summary saved: {summary_filename}")
        except Exception as e:
            print(f"❌ Error saving summary: {e}")
    
    print(f"\n🎉 News bot completed!")
    print(f"📊 Generated {len(generated_files)} articles")
    print(f"📁 Files: {', '.join(generated_files)}")

if __name__ == "__main__":
    main()