#!/usr/bin/env python3
"""
Free Web Scraper for AgentCo
Uses: requests, beautifulsoup4 (both FREE)
APIs: Wikipedia API (FREE), Google Custom Search (100 free/day)
"""

import requests
from bs4 import BeautifulSoup
import hashlib
from typing import List, Dict, Optional

class FreeWebScraper:
    """Real web scraping using free technologies"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (AgentCo Research Bot)'
        })
    
    def fetch_wikipedia_api(self, topic: str) -> Optional[Dict]:
        """
        Fetch Wikipedia using OFFICIAL API (no key needed, completely free)
        """
        try:
            # Wikipedia REST API endpoint
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'url': data.get('content_urls', {}).get('desktop', {}).get('page', url),
                    'title': data.get('title', topic),
                    'content': data.get('extract', ''),
                    'source': 'wikipedia_api',
                    'status': 200
                }
        except Exception as e:
            print(f"    [Error] Wikipedia: {e}")
        return None
    
    def fetch_hacker_news(self) -> List[Dict]:
        """
        Fetch Hacker News (completely free, no API key)
        Real content from real website
        """
        try:
            response = self.session.get('https://news.ycombinator.com/newest', timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                items = []
                
                for row in soup.find_all('tr', class_='athing')[:5]:
                    try:
                        title_elem = row.find('span', class_='titleline')
                        if title_elem:
                            a = title_elem.find('a')
                            if a:
                                items.append({
                                    'title': a.get_text(),
                                    'url': a.get('href', ''),
                                    'source': 'hacker_news'
                                })
                    except:
                        pass
                
                return items
        except Exception as e:
            print(f"    [Error] Hacker News: {e}")
        return []
    
    def fetch_github_trending(self) -> List[Dict]:
        """
        Fetch GitHub trending repositories (free, no auth needed)
        """
        try:
            url = 'https://github.com/trending?spoken_language_code=&since=daily'
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                repos = []
                
                for article in soup.find_all('article', class_='Box-row')[:5]:
                    try:
                        h2 = article.find('h2')
                        if h2:
                            link = h2.find('a')
                            if link:
                                repos.append({
                                    'title': link.get_text(strip=True),
                                    'url': 'https://github.com' + link.get('href', ''),
                                    'source': 'github_trending'
                                })
                    except:
                        pass
                
                return repos
        except Exception as e:
            print(f"    [Error] GitHub Trending: {e}")
        return []
    
    def fetch_real_page(self, url: str) -> Optional[Dict]:
        """
        Fetch a real webpage and extract content
        """
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get title
            title = soup.title.string if soup.title else url.split('/')[-1]
            
            # Get text
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Content hash
            content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
            
            return {
                'url': url,
                'title': title,
                'content': text[:500],
                'content_hash': content_hash,
                'status': response.status_code,
                'content_size': len(text)
            }
            
        except Exception as e:
            print(f"    [Error] Fetch '{url}': {e}")
            return None


def test_scraper():
    """Test the scraper"""
    scraper = FreeWebScraper()
    
    print("\n" + "="*70)
    print("TESTING FREE WEB SCRAPER")
    print("="*70)
    
    # Test 1: Wikipedia API
    print("\n[TEST 1] Wikipedia API (Official, FREE)")
    wiki = scraper.fetch_wikipedia_api("Artificial intelligence")
    if wiki:
        print(f"✓ Wikipedia fetched: {wiki['title']}")
        print(f"  Content: {wiki['content'][:100]}...")
    
    # Test 2: Hacker News
    print("\n[TEST 2] Hacker News (Scraping, FREE)")
    hn_items = scraper.fetch_hacker_news()
    if hn_items:
        print(f"✓ Hacker News: Found {len(hn_items)} items")
        for item in hn_items[:2]:
            print(f"  - {item['title'][:50]}")
    
    # Test 3: GitHub Trending
    print("\n[TEST 3] GitHub Trending (Scraping, FREE)")
    gh_items = scraper.fetch_github_trending()
    if gh_items:
        print(f"✓ GitHub Trending: Found {len(gh_items)} repos")
        for item in gh_items[:2]:
            print(f"  - {item['title'][:50]}")
    
    # Test 4: Fetch real page
    print("\n[TEST 4] Fetch Real Webpage")
    page = scraper.fetch_real_page("https://en.wikipedia.org/wiki/Machine_learning")
    if page:
        print(f"✓ Fetched: {page['title']}")
        print(f"  Size: {page['content_size']} chars")
        print(f"  Hash: {page['content_hash']}")
    
    print("\n" + "="*70)
    print("ALL TESTS COMPLETE")
    print("="*70 + "\n")


if __name__ == '__main__':
    test_scraper()
