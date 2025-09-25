#!/usr/bin/env python3
"""
Clean News Bot Implementation
Based on actual EventRegistry and Google Gemini API documentation
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Import required packages
try:
    import google.generativeai as genai
    from eventregistry import EventRegistry, QueryArticlesIter
except ImportError as e:
    print(f"❌ Missing required packages: {e}")
    print("Install with: pip install google-generativeai eventregistry")
    sys.exit(1)


class NewsBot:
    def __init__(self, eventregistry_key: str, google_key: str):
        """Initialize the news bot with API keys"""
        self.er = EventRegistry(apiKey=eventregistry_key)
        genai.configure(api_key=google_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    def fetch_news(self, keyword: str = None, max_articles: int = 5) -> List[Dict]:
        """
        Fetch news articles using EventRegistry API
        Using the proper QueryArticlesIter approach from documentation
        """
        try:
            # Create query for articles
            if keyword:
                # Search for articles containing the keyword
                q = QueryArticlesIter(
                    keywords=keyword,
                    keywordsLoc="body",  # Search in article body
                    lang="eng",
                    dateStart=datetime.now() - timedelta(days=7),  # Last week
                    dateEnd=datetime.now()
                )
            else:
                # Get latest articles without keyword filter
                q = QueryArticlesIter(
                    lang="eng",
                    dateStart=datetime.now() - timedelta(days=1),  # Yesterday
                    dateEnd=datetime.now()
                )
            
            # Fetch articles
            articles = []
            count = 0
            
            print(f"🔍 Fetching articles with keyword: '{keyword}'...")
            
            for article in q.execQuery(self.er, sortBy="date", maxItems=max_articles):
                articles.append({
                    'title': article.get('title', ''),
                    'body': article.get('body', ''),
                    'url': article.get('url', ''),
                    'date': article.get('date', ''),
                    'source': article.get('source', {}).get('title', '') if article.get('source') else '',
                    'lang': article.get('lang', 'eng')
                })
                count += 1
                print(f"  📰 Found article {count}: {article.get('title', 'No title')[:50]}...")
                
                if count >= max_articles:
                    break
            
            print(f"✅ Successfully fetched {len(articles)} articles")
            return articles
            
        except Exception as e:
            print(f"❌ Error fetching news: {e}")
            return []
    
    def generate_article(self, news_data: Dict, style: str = "professional") -> Dict:
        """
        Generate enhanced article using Gemini API
        Using proper generation approach from documentation
        """
        try:
            # Prepare the prompt based on style
            style_prompts = {
                "professional": "Write in a professional, journalistic tone suitable for business publications.",
                "casual": "Write in a conversational, accessible tone for general readers.",
                "academic": "Use a formal, analytical tone with detailed explanations."
            }
            
            prompt = f"""
Transform this news article into a well-structured, engaging piece.

STYLE: {style_prompts.get(style, style_prompts['professional'])}

ORIGINAL ARTICLE:
Title: {news_data.get('title', 'N/A')}
Source: {news_data.get('source', 'N/A')}
Date: {news_data.get('date', 'N/A')}
Content: {news_data.get('body', 'N/A')[:2000]}

REQUIREMENTS:
1. Create an improved headline
2. Write a compelling lead paragraph
3. Structure the content with clear sections
4. Add context and analysis where appropriate
5. Ensure accuracy while improving readability
6. Keep it concise but informative

Please provide the response in this format:
HEADLINE: [Your improved headline]
LEAD: [Opening paragraph]
BODY: [Main content with proper structure]
CONCLUSION: [Closing thoughts]
"""

            # Generate content using Gemini
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2000,
                    top_p=0.8,
                )
            )
            
            # Parse the response
            content = response.text
            
            # Extract sections (basic parsing)
            headline = self._extract_section(content, "HEADLINE:")
            lead = self._extract_section(content, "LEAD:")
            body = self._extract_section(content, "BODY:")
            conclusion = self._extract_section(content, "CONCLUSION:")
            
            return {
                "headline": headline or news_data.get('title', 'Generated Article'),
                "lead": lead or "Article summary not available",
                "body": body or content,
                "conclusion": conclusion or "",
                "original_title": news_data.get('title', ''),
                "original_source": news_data.get('source', ''),
                "original_url": news_data.get('url', ''),
                "original_date": news_data.get('date', ''),
                "generated_at": datetime.now().isoformat(),
                "word_count": len(content.split())
            }
            
        except Exception as e:
            print(f"❌ Error generating article: {e}")
            return {
                "error": str(e),
                "original_title": news_data.get('title', ''),
                "original_source": news_data.get('source', '')
            }
    
    def _extract_section(self, content: str, marker: str) -> str:
        """Helper method to extract sections from generated content"""
        try:
            if marker in content:
                start = content.find(marker) + len(marker)
                end = content.find('\n\n', start)
                if end == -1:
                    # Find next section marker or end of content
                    markers = ["HEADLINE:", "LEAD:", "BODY:", "CONCLUSION:"]
                    next_marker_pos = len(content)
                    for m in markers:
                        if m != marker and m in content[start:]:
                            pos = content.find(m, start)
                            if pos < next_marker_pos:
                                next_marker_pos = pos
                    end = next_marker_pos
                
                return content[start:end].strip()
            return ""
        except:
            return ""
    
    def save_article(self, article: Dict, filename: str = None) -> str:
        """Save article to markdown file"""
        if "error" in article:
            print(f"❌ Cannot save article with error: {article['error']}")
            return ""
        
        if not filename:
            # Create safe filename
            title = article.get('headline', 'article')
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe_title}_{timestamp}.md"
        
        # Build markdown content
        content = f"""# {article.get('headline', 'Generated Article')}

**Generated:** {article.get('generated_at', 'N/A')}  
**Original Source:** {article.get('original_source', 'N/A')}  
**Original URL:** {article.get('original_url', 'N/A')}  
**Word Count:** {article.get('word_count', 'N/A')}  

---

## Summary

{article.get('lead', 'N/A')}

## Article

{article.get('body', 'N/A')}

## Conclusion

{article.get('conclusion', 'N/A')}

---

*Generated by News Bot using EventRegistry API and Google Gemini AI*
"""
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Article saved: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Error saving article: {e}")
            return ""
    
    def create_summary_report(self, articles: List[Dict], keyword: str) -> Dict:
        """Create a JSON summary report"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "keyword": keyword,
            "total_articles": len(articles),
            "successful_articles": len([a for a in articles if "error" not in a]),
            "failed_articles": len([a for a in articles if "error" in a]),
            "articles": articles
        }
        return report
    
    def run(self, keyword: str = "artificial intelligence", 
            style: str = "professional", 
            max_articles: int = 3) -> Dict:
        """
        Main execution method
        """
        print(f"🤖 Starting News Bot...")
        print(f"📝 Keyword: {keyword}")
        print(f"🎨 Style: {style}")
        print(f"📊 Max articles: {max_articles}")
        print("-" * 50)
        
        # Fetch news articles
        news_articles = self.fetch_news(keyword, max_articles)
        
        if not news_articles:
            print("❌ No articles found")
            return {
                "error": "No articles found",
                "keyword": keyword,
                "generated_at": datetime.now().isoformat()
            }
        
        # Generate enhanced articles
        generated_articles = []
        saved_files = []
        
        for i, news in enumerate(news_articles, 1):
            print(f"\n📝 Processing article {i}/{len(news_articles)}")
            
            # Generate enhanced article
            enhanced = self.generate_article(news, style)
            generated_articles.append(enhanced)
            
            # Save article if successful
            if "error" not in enhanced:
                filename = self.save_article(enhanced, f"article_{i}_{keyword.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.md")
                if filename:
                    saved_files.append(filename)
            
            # Rate limiting
            time.sleep(2)
        
        # Create summary report
        report = self.create_summary_report(generated_articles, keyword)
        
        # Save summary
        summary_file = f"summary_{keyword.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json"
        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"✅ Summary saved: {summary_file}")
        except Exception as e:
            print(f"❌ Error saving summary: {e}")
        
        print(f"\n🎉 News Bot completed!")
        print(f"📊 Total articles processed: {len(generated_articles)}")
        print(f"✅ Successful: {report['successful_articles']}")
        print(f"❌ Failed: {report['failed_articles']}")
        print(f"📁 Files saved: {len(saved_files)}")
        
        return report


def main():
    """Main entry point for GitHub Actions"""
    
    # Get API keys
    eventregistry_key = os.getenv('EVENTREGISTRY_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')
    
    if not eventregistry_key or not google_key:
        print("❌ Missing required API keys!")
        print("Set EVENTREGISTRY_API_KEY and GOOGLE_API_KEY environment variables")
        sys.exit(1)
    
    # Get parameters
    keyword = os.getenv('INPUT_KEYWORD', 'artificial intelligence')
    style = os.getenv('INPUT_STYLE', 'professional')
    max_articles = int(os.getenv('MAX_ARTICLES', '3'))
    
    # Create and run the bot
    try:
        bot = NewsBot(eventregistry_key, google_key)
        result = bot.run(keyword, style, max_articles)
        
        if "error" in result:
            print(f"❌ Bot execution failed: {result['error']}")
            sys.exit(1)
        else:
            print("✅ Bot execution completed successfully")
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()