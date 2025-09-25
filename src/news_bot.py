"""
AI News Bot - Fetch news and generate articles using EventRegistry + Google Gemini

A clean, Python-based news bot that:
1. Fetches recent news articles from EventRegistry API
2. Uses Google Gemini AI to rewrite them into engaging articles
3. Creates GitHub issues with article previews
4. Generates downloadable markdown files

Usage:
    python src/news_bot.py --keyword "artificial intelligence" --max-articles 3
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests
import google.generativeai as genai
from eventregistry import EventRegistry, QueryArticlesIter, QueryArticles
try:
    from eventregistry import RequestArticlesInfo, ReturnInfo, ArticleInfoFlags
except ImportError:
    # Fallback if some classes aren't available in the version
    RequestArticlesInfo = ReturnInfo = ArticleInfoFlags = None


class NewsBot:
    """Main news bot class handling API interactions and article generation."""
    
    def __init__(self, eventregistry_key: str, google_key: str):
        """Initialize with API credentials."""
        self.er = EventRegistry(apiKey=eventregistry_key)
        genai.configure(api_key=google_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    def fetch_news(self, keyword: str, max_articles: int = 3) -> List[Dict]:
        """
        Fetch recent news articles from EventRegistry.
        
        Args:
            keyword: Search term for news articles
            max_articles: Maximum number of articles to fetch
            
        Returns:
            List of article dictionaries with title, body, url, etc.
        """
        print(f"🔍 Searching for news about '{keyword}'...")
        
        try:
            # Create query for recent articles using the correct API
            from eventregistry import QueryArticlesIter, QueryArticles
            
            # Use QueryArticles for simple queries
            q = QueryArticles(
                keywords=keyword,
                keywordsLoc="body,title",  # Search in title and body
                lang="eng",
                dateStart=datetime.now() - timedelta(days=7),  # Last week
                dateEnd=datetime.now()
            )
            
            # Request article details
            q.setRequestedResult(
                RequestArticlesInfo(
                    page=1,
                    count=max_articles * 2,  # Get extra to filter
                    articleBodyLen=-1,  # Full body
                    returnInfo=ReturnInfo(
                        articleInfo=ArticleInfoFlags(
                            title=True,
                            body=True,
                            url=True,
                            date=True,
                            source=True,
                            authors=True
                        )
                    )
                )
            )
            
            # Execute the query
            result = self.er.execQuery(q)
            
            articles = []
            if 'articles' in result and 'results' in result['articles']:
                for article in result['articles']['results']:
                    # Extract article data
                    if article.get('body') and article.get('title'):
                        articles.append({
                            'title': article.get('title', '').strip(),
                            'body': article.get('body', '').strip()[:2000],  # Limit body length
                            'url': article.get('url', ''),
                            'source': article.get('source', {}).get('title', 'Unknown'),
                            'date': article.get('dateTime', ''),
                            'authors': [author.get('name', '') for author in article.get('authors', [])]
                        })
                        
                        if len(articles) >= max_articles:
                            break
            
            print(f"✅ Found {len(articles)} articles")
            return articles
            
        except ImportError:
            print("❌ Missing EventRegistry imports, falling back to simple approach")
            return self._fetch_news_fallback(keyword, max_articles)
        except Exception as e:
            print(f"❌ Error fetching news: {e}")
            return self._fetch_news_fallback(keyword, max_articles)
    
    def _fetch_news_fallback(self, keyword: str, max_articles: int) -> List[Dict]:
        """Fallback method using direct API calls."""
        try:
            # Use EventRegistry's direct API approach
            articles = []
            
            # Simple query using the ER object
            query_params = {
                "action": "getArticles", 
                "keyword": keyword,
                "articlesPage": 1,
                "articlesCount": max_articles,
                "articlesSortBy": "date", 
                "articlesSortByAsc": False,
                "articlesArticleBodyLen": -1,
                "resultType": "articles",
                "dataType": ["news"],
                "lang": "eng"
            }
            
            # Make the request using EventRegistry's method
            result = self.er.jsonRequest(query_params)
            
            if result and 'articles' in result and 'results' in result['articles']:
                for article in result['articles']['results']:
                    if article.get('body') and article.get('title'):
                        articles.append({
                            'title': article.get('title', '').strip(),
                            'body': article.get('body', '').strip()[:2000],
                            'url': article.get('url', ''),
                            'source': article.get('source', {}).get('title', 'Unknown'),
                            'date': article.get('dateTime', ''),
                            'authors': []
                        })
            
            print(f"✅ Fallback method found {len(articles)} articles")
            return articles
            
        except Exception as e:
            print(f"❌ Fallback method also failed: {e}")
            return []
    
    def generate_article(self, source_article: Dict, style: str = "professional") -> Optional[Dict]:
        """
        Use Gemini AI to rewrite a news article.
        
        Args:
            source_article: Original article data
            style: Writing style (professional, casual, academic)
            
        Returns:
            Generated article data or None if failed
        """
        print(f"✍️ Generating article from: {source_article['title'][:50]}...")
        
        style_prompts = {
            "professional": "Write in a professional, journalistic tone suitable for business readers.",
            "casual": "Write in a conversational, engaging tone for general audiences.",
            "academic": "Write in a formal, analytical tone with deeper insights."
        }
        
        prompt = f"""
Rewrite this news article in a {style} style. Make it engaging and well-structured.

Original Article:
Title: {source_article['title']}
Source: {source_article['source']}
Content: {source_article['body']}

Instructions:
- {style_prompts.get(style, style_prompts['professional'])}
- Create an engaging headline
- Structure with clear paragraphs
- Add insights or analysis where appropriate
- Keep it between 300-800 words
- Include relevant context
- End with a brief conclusion

Format the response as a complete article ready for publication.
"""

        try:
            response = self.model.generate_content(prompt)
            
            if response.text:
                return {
                    'title': self._extract_title(response.text),
                    'content': response.text,
                    'original_source': source_article['source'],
                    'original_url': source_article['url'],
                    'generated_at': datetime.now().isoformat(),
                    'style': style
                }
            else:
                print(f"❌ No content generated for article")
                return None
                
        except Exception as e:
            print(f"❌ Error generating article: {e}")
            return None
    
    def _extract_title(self, content: str) -> str:
        """Extract title from generated content."""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Remove markdown formatting
                title = line.replace('**', '').replace('*', '').replace('#', '').strip()
                if len(title) > 10:  # Reasonable title length
                    return title
        return "Generated News Article"
    
    def save_article(self, article: Dict, keyword: str) -> str:
        """
        Save article to markdown file.
        
        Args:
            article: Generated article data
            keyword: Search keyword for filename
            
        Returns:
            Filename of saved article
        """
        # Create safe filename
        safe_title = "".join(c for c in article['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"article_{safe_title}_{timestamp}.md"
        
        # Create markdown content
        markdown_content = f"""# {article['title']}

**Generated:** {article['generated_at']}  
**Style:** {article['style']}  
**Original Source:** {article['original_source']}  
**Source URL:** {article['original_url']}  

---

{article['content']}

---

*Generated by AI News Bot using EventRegistry API + Google Gemini AI*
"""
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"💾 Saved article: {filename}")
        return filename
    
    def create_github_issue(self, articles: List[str], keyword: str, run_number: str = "local") -> bool:
        """
        Create GitHub issue with article summaries using GitHub API.
        
        Args:
            articles: List of article filenames
            keyword: Search keyword
            run_number: Workflow run number
            
        Returns:
            True if successful, False otherwise
        """
        github_token = os.getenv('GITHUB_TOKEN')
        github_repo = os.getenv('GITHUB_REPOSITORY')  # format: owner/repo
        
        if not github_token or not github_repo:
            print("⚠️ GitHub credentials not found, skipping issue creation")
            return False
        
        print(f"🐙 Creating GitHub issue for {len(articles)} articles...")
        
        # Build issue body
        issue_body = f"""# 📰 AI News Bot Results

**Keyword:** `{keyword}`  
**Run:** {run_number}  
**Articles Generated:** {len(articles)}  
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}  

---

## 📋 Generated Articles

"""
        
        # Add preview of each article
        for i, filename in enumerate(articles, 1):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract title
                title_line = next((line for line in content.split('\n') if line.startswith('# ')), f"Article {i}")
                title = title_line.replace('# ', '').strip()
                
                # Get preview (first few paragraphs)
                lines = content.split('\n')
                preview_lines = []
                for line in lines[8:]:  # Skip metadata
                    if line.strip() and not line.startswith('---'):
                        preview_lines.append(line)
                        if len(preview_lines) >= 10:  # Limit preview length
                            break
                
                preview = '\n'.join(preview_lines[:5])  # First 5 lines of content
                
                issue_body += f"""### 📄 {title}

{preview}

*[Full article available in workflow artifacts]*

---

"""
            except Exception as e:
                print(f"⚠️ Error reading {filename}: {e}")
        
        # Add footer
        issue_body += f"""
## 📊 Summary

- **Search Keyword:** {keyword}
- **Articles Generated:** {len(articles)}
- **Workflow Run:** {run_number}

> 🤖 *Generated by AI News Bot using EventRegistry API + Google Gemini AI*
"""
        
        # Create issue via GitHub API
        try:
            url = f"https://api.github.com/repos/{github_repo}/issues"
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            data = {
                'title': f"📰 AI News: {keyword} (Run {run_number})",
                'body': issue_body,
                'labels': ['ai-news-bot', 'automated']
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 201:
                issue_data = response.json()
                print(f"✅ Created GitHub issue #{issue_data['number']}")
                return True
            else:
                print(f"❌ Failed to create issue: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating GitHub issue: {e}")
            return False


def main():
    """Main function to run the news bot."""
    parser = argparse.ArgumentParser(description='AI News Bot')
    parser.add_argument('--keyword', default=os.getenv('INPUT_KEYWORD', 'artificial intelligence'),
                       help='News search keyword')
    parser.add_argument('--max-articles', type=int, default=int(os.getenv('MAX_ARTICLES', '3')),
                       help='Maximum number of articles to generate')
    parser.add_argument('--style', default=os.getenv('INPUT_STYLE', 'professional'),
                       choices=['professional', 'casual', 'academic'],
                       help='Writing style for generated articles')
    
    args = parser.parse_args()
    
    # Get API keys
    eventregistry_key = os.getenv('EVENTREGISTRY_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')
    
    if not eventregistry_key or not google_key:
        print("❌ Missing API keys!")
        print("Set EVENTREGISTRY_API_KEY and GOOGLE_API_KEY environment variables")
        sys.exit(1)
    
    print(f"🚀 Starting AI News Bot...")
    print(f"   Keyword: {args.keyword}")
    print(f"   Max Articles: {args.max_articles}")
    print(f"   Style: {args.style}")
    
    # Initialize bot
    bot = NewsBot(eventregistry_key, google_key)
    
    # Fetch news
    articles = bot.fetch_news(args.keyword, args.max_articles)
    if not articles:
        print("❌ No articles found")
        sys.exit(1)
    
    # Generate and save articles
    generated_files = []
    for article in articles:
        generated = bot.generate_article(article, args.style)
        if generated:
            filename = bot.save_article(generated, args.keyword)
            generated_files.append(filename)
    
    if not generated_files:
        print("❌ No articles were generated")
        sys.exit(1)
    
    # Create GitHub issue if running in CI
    run_number = os.getenv('GITHUB_RUN_NUMBER', 'local')
    bot.create_github_issue(generated_files, args.keyword, run_number)
    
    print(f"✅ Generated {len(generated_files)} articles successfully!")
    print("Files:", generated_files)


if __name__ == "__main__":
    main()