"""
News fetching service with Perplexity Sonar Pro (via OpenRouter) for search
and GPT-4.1-mini for content generation
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import List, Dict, Optional
from datetime import datetime
import json
import hashlib
import re

from app.config import settings
from app.models.news import NewsItem


def get_current_date_context() -> str:
    """Get current date context string for prompts"""
    now = datetime.now()
    return f"CURRENT DATE: {now.strftime('%B %d, %Y')} (Year: {now.year}). All content should be relevant to {now.year}."


# Digital marketing search queries by category
CATEGORY_QUERIES = {
    "seo": [
        "Google algorithm update 2026",
        "SEO trends January 2026",
        "search engine optimization news",
    ],
    "ppc": [
        "Google Ads Performance Max news 2026",
        "PPC advertising trends",
        "Meta ads platform updates",
    ],
    "social_media": [
        "TikTok marketing news 2026",
        "Instagram algorithm changes",
        "social media marketing trends",
    ],
    "website": [
        "ecommerce website trends 2026",
        "web design UX news",
        "conversion rate optimization",
    ],
}


class NewsService:
    def __init__(self):
        # Layer 1: Perplexity Sonar Pro for real-time web search (via OpenRouter)
        self.search_llm = ChatOpenAI(
            model="perplexity/sonar-pro",
            temperature=0.3,
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )
        
        # Layer 2: GPT-4.1-mini for ranking, cleaning, and catchy titles
        self.content_llm = ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )
        
        # Layer 3: GPT-4.1 for article writing (if needed)
        self.writer_llm = ChatOpenAI(
            model="gpt-4.1",
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )
        
        self.str_parser = StrOutputParser()
        self._news_cache: Dict[str, List[NewsItem]] = {}
        
        print("[OK] NewsService initialized with multi-model approach:")
        print("  - Search: Perplexity Sonar Pro (via OpenRouter)")
        print("  - Ranking & Cleaning: GPT-4.1-mini")
        print("  - Article Writing: GPT-4.1")
    
    def _dedupe_items(self, items: List[NewsItem]) -> List[NewsItem]:
        """Remove duplicate news items based on title similarity"""
        seen_hashes = set()
        unique_items = []
        
        for item in items:
            title_hash = hashlib.md5(
                item.title.lower().strip()[:50].encode()
            ).hexdigest()
            
            if title_hash not in seen_hashes:
                seen_hashes.add(title_hash)
                unique_items.append(item)
        
        return unique_items

    async def fetch_news_with_catchy_titles(
        self,
        category: str,
        num_items: int = 4
    ) -> List[NewsItem]:
        """
        STEP 1: Use Perplexity Sonar Pro to search for REAL news with URLs
        STEP 2: Store original data, send ONLY titles to GPT-4.1-mini for catchy versions
        STEP 3: Merge catchy titles back with preserved original data (URLs, etc.)
        """
        
        date_context = get_current_date_context()
        current_year = datetime.now().year
        
        # STEP 1: Search for real news using Perplexity Sonar Pro
        search_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""{date_context}

You are a digital marketing news researcher with real-time web access.

Search the web and find {{{{num_items}}}} REAL, recent news articles about {{{{category}}}} digital marketing from the last 7 days.

For each article you find, provide:
1. title: The actual headline from the source
2. publisher: The actual publisher name (e.g., Search Engine Journal, Social Media Today)
3. published_date: The actual publication date in YYYY-MM-DD format (should be {current_year})
4. url: The ACTUAL, REAL URL from the web (REQUIRED - must be a real clickable link)
5. summary: 4-5 sentence summary of what the article is about
6. why_it_matters: Why this news is important for digital marketers

CRITICAL RULES:
- You MUST provide real URLs from actual websites
- Do NOT make up or fabricate URLs
- Only include articles that have verifiable URLs
- Return ONLY valid JSON, no markdown or extra text
- All dates should be from {current_year}

Return ONLY this JSON format (no other text):
{{{{"news": [{{{{"title": "...", "publisher": "...", "published_date": "YYYY-MM-DD", "url": "https://...", "summary": "...", "why_it_matters": "..."}}}}]}}}}"""),
            ("user", "Search the web for {num_items} recent {category} digital marketing news articles from " + str(current_year) + ". Return ONLY JSON.")
        ])
        
        search_chain = search_prompt | self.search_llm | self.str_parser
        
        try:
            # Use Perplexity to search for real news
            search_result = await search_chain.ainvoke({
                "num_items": num_items,
                "category": category.upper()
            })
            
            # Clean up response - extract JSON if wrapped in markdown
            clean_result = search_result.strip()
            if clean_result.startswith("```"):
                # Remove markdown code blocks
                clean_result = re.sub(r'^```(?:json)?\s*', '', clean_result)
                clean_result = re.sub(r'\s*```$', '', clean_result)
            
            search_data = json.loads(clean_result)
            raw_articles = search_data.get("news", [])
            
            if not raw_articles:
                print(f"[WARN] Perplexity returned no results for {category}, using fallback")
                return await self._fetch_ai_generated_news(category, num_items)
            
            # STEP 2: Store original data in a dict keyed by index
            # Only send titles to GPT for transformation (preserves URLs)
            original_data = {}
            titles_only = []
            for i, article in enumerate(raw_articles):
                original_data[i] = {
                    "url": article.get("url", ""),
                    "publisher": article.get("publisher", "Industry Source"),
                    "published_date": article.get("published_date", "2026-01-12"),
                    "summary": article.get("summary", ""),
                    "why_it_matters": article.get("why_it_matters", ""),
                }
                titles_only.append({
                    "index": i,
                    "title": article.get("title", "")
                })
            
            # Send ONLY titles to GPT-4.1-mini
            titles_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a newsletter copywriter. Transform these news headlines into catchy, engaging titles.

For each title, create a dramatic hook using:
- Power words (Revolutionary, Game-Changing, Critical, Massive, etc.)
- Numbers when relevant
- Urgency and impact
- Keep it under 80 characters

Return JSON array with index and catchy_title for each:
{{"titles": [{{"index": 0, "catchy_title": "Your Catchy Version Here"}}, ...]}}"""),
                ("user", "Transform these headlines:\n\n{titles}")
            ])
            
            titles_chain = titles_prompt | self.content_llm | self.str_parser
            titles_result = await titles_chain.ainvoke({
                "titles": json.dumps(titles_only, indent=2)
            })
            
            # Clean up titles result
            clean_titles = titles_result.strip()
            if clean_titles.startswith("```"):
                clean_titles = re.sub(r'^```(?:json)?\s*', '', clean_titles)
                clean_titles = re.sub(r'\s*```$', '', clean_titles)
            
            titles_data = json.loads(clean_titles)
            
            # STEP 3: Merge catchy titles with preserved original data
            catchy_map = {}
            for item in titles_data.get("titles", []):
                idx = item.get("index", -1)
                if idx >= 0:
                    catchy_map[idx] = item.get("catchy_title", "")
            
            items = []
            for i, article in enumerate(raw_articles[:num_items]):
                # Get preserved original data
                orig = original_data.get(i, {})
                url = orig.get("url", "").strip()
                
                # Validate URL
                if not url or url == "https://..." or url == "":
                    print(f"[WARN] No valid URL for article index {i}: {article.get('title', 'Unknown')}")
                    continue
                
                if not url.startswith("http"):
                    url = f"https://{url}"
                
                # Get catchy title or fallback to original
                catchy_title = catchy_map.get(i, article.get("title", ""))
                
                item = NewsItem(
                    category=category,
                    title=catchy_title if catchy_title else article.get("title", ""),
                    publisher=orig.get("publisher", "Industry Source"),
                    published_date=orig.get("published_date", "2026-01-12"),
                    url=url,  # PRESERVED from original Perplexity response
                    summary=orig.get("summary", ""),
                    why_it_matters=orig.get("why_it_matters", ""),
                    tags=[category, "digital-marketing"],
                )
                
                if item.title:
                    items.append(item)
            
            print(f"[OK] Fetched {len(items)} news items for {category} with preserved URLs")
            return items
            
        except Exception as e:
            print(f"Perplexity search error for {category}: {e}")
            return await self._fetch_ai_generated_news(category, num_items)
    
    async def _fetch_ai_generated_news(
        self,
        category: str,
        num_items: int = 4
    ) -> List[NewsItem]:
        """Fallback: Generate plausible news using GPT-4.1-mini (without real URLs)"""
        
        date_context = get_current_date_context()
        current_year = datetime.now().year
        current_month = datetime.now().strftime('%B %Y')
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""{date_context}

You are a digital marketing news researcher and copywriter.

Generate {{{{num_items}}}} plausible, recent digital marketing news stories about {{{{category}}}} from {current_month}.

IMPORTANT: We are in {current_year}. All content must be dated {current_year}, NOT 2024 or earlier.

For each story provide:
1. catchy_title: Dramatic hook title (use power words, reference {current_year} if mentioning year)
2. publisher: Real publisher name (Search Engine Journal, Social Media Today, etc.)
3. published_date: YYYY-MM-DD format ({current_month})
4. url: Leave EMPTY ("") - never invent fake URLs
5. summary: 2-3 sentence summary
6. why_it_matters: 1-2 sentences on business impact

Return JSON: {{{{"news": [...]}}}}"""),
            ("user", f"Generate {{num_items}} plausible {{category}} digital marketing news stories from {current_month}.")
        ])
        
        chain = prompt | self.content_llm | self.str_parser
        
        try:
            result = await chain.ainvoke({
                "num_items": num_items,
                "category": category.upper()
            })
            
            # Clean up result
            clean_result = result.strip()
            if clean_result.startswith("```"):
                clean_result = re.sub(r'^```(?:json)?\s*', '', clean_result)
                clean_result = re.sub(r'\s*```$', '', clean_result)
            
            data = json.loads(clean_result)
            items = []
            
            for article in data.get("news", [])[:num_items]:
                item = NewsItem(
                    category=category,
                    title=article.get("catchy_title", article.get("title", "")),
                    publisher=article.get("publisher", "Industry Source"),
                    published_date=article.get("published_date", "2026-01-12"),
                    url=article.get("url", ""),
                    summary=article.get("summary", ""),
                    why_it_matters=article.get("why_it_matters", ""),
                    tags=[category, "digital-marketing"],
                )
                if item.title:
                    items.append(item)
            
            print(f"[FALLBACK] Generated {len(items)} AI news items for {category} (no real URLs)")
            return items
            
        except Exception as e:
            print(f"Fallback news generation error for {category}: {e}")
            return []

    async def fetch_all_categories(self) -> Dict[str, List[NewsItem]]:
        """Fetch news for all digital marketing categories"""
        all_news = {}
        
        for category in ["seo", "ppc", "social_media", "website"]:
            items = await self.fetch_news_with_catchy_titles(category, num_items=4)
            all_news[category] = items
        
        return all_news

    async def rank_and_assign_to_sections(
        self,
        all_news: Dict[str, List[NewsItem]]
    ) -> Dict[str, List[NewsItem]]:
        """AI ranks all news and assigns to newsletter sections (without tomorrow-top)"""
        all_items = []
        for category, items in all_news.items():
            all_items.extend(items)
        
        if not all_items:
            return {}
        
        news_summary = "\n".join([
            f"[{i}] {item.title} ({item.category}) - {item.summary[:100]}..."
            for i, item in enumerate(all_items)
        ])
        
        date_context = get_current_date_context()
        current_year = datetime.now().year
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""{date_context}

You are a newsletter editor for a digital marketing publication in {current_year}.

SECTIONS TO FILL:
1. main-story: THE biggest, most impactful story (1 item)
2. main-story-summary: Summary for the main story (1 item)
3. second-story: Strong supporting story (1 item)
4. third-story: Additional interesting story (1 item)
5. trendsetter: Forward-looking, emerging trend (1-2 items)
6. top-news: Top industry headlines (2-3 items)
7. links: Valuable resources/guides (2-3 items)

RULES:
- Each item can only be used ONCE
- Pick the MOST impactful story for main-story
- Ensure variety across categories
- Prioritize stories relevant to {current_year}

Return JSON: {{"assignments": {{"main-story": [0], "second-story": [1], ...}}, "reasoning": "..."}}"""),
            ("user", "Here are {count} news stories to assign:\n\n{news_summary}")
        ])
        
        try:
            chain = prompt | self.content_llm | self.str_parser
            result = await chain.ainvoke({
                "count": len(all_items),
                "news_summary": news_summary
            })
            
            # Clean up result
            clean_result = result.strip()
            if clean_result.startswith("```"):
                clean_result = re.sub(r'^```(?:json)?\s*', '', clean_result)
                clean_result = re.sub(r'\s*```$', '', clean_result)
            
            data = json.loads(clean_result)
            assignments = data.get("assignments", {})
            
            section_items = {}
            used_indices = set()
            
            for section_key, indices in assignments.items():
                section_items[section_key] = []
                for idx in indices:
                    if isinstance(idx, int) and 0 <= idx < len(all_items) and idx not in used_indices:
                        section_items[section_key].append(all_items[idx])
                        used_indices.add(idx)
            
            return section_items
            
        except Exception as e:
            print(f"Ranking error: {e}")
            return self._simple_distribution(all_items)

    def _simple_distribution(self, items: List[NewsItem]) -> Dict[str, List[NewsItem]]:
        """Fallback simple distribution if AI ranking fails"""
        sections = {
            "main-story": items[:1] if len(items) > 0 else [],
            "main-story-summary": items[:1] if len(items) > 0 else [],
            "second-story": items[1:2] if len(items) > 1 else [],
            "third-story": items[2:3] if len(items) > 2 else [],
            "trendsetter": items[3:5] if len(items) > 3 else [],
            "top-news": items[5:8] if len(items) > 5 else [],
            "links": items[8:11] if len(items) > 8 else [],
        }
        return sections

    async def generate_newsletter_recommendations(self) -> Dict[str, List[NewsItem]]:
        """Main method: Fetch news, rank, and assign to sections"""
        all_news = await self.fetch_all_categories()
        section_assignments = await self.rank_and_assign_to_sections(all_news)
        return section_assignments

    async def search_news_for_section(
        self,
        section_title: str,
        section_description: str,
        num_items: int = 3
    ) -> List[NewsItem]:
        """Search for news specifically suited for a newsletter section.
        If description contains 'Find news related to:', search for related news.
        """
        
        # Check if this is a "related news" search
        is_related_search = "Find news related to:" in section_description
        print(f"[DEBUG] search_news_for_section called:")
        print(f"  - section_title: {section_title}")
        print(f"  - is_related_search: {is_related_search}")
        print(f"  - description: {section_description[:100]}...")
        
        if is_related_search:
            # Extract the topic from the description
            # Format: 'Find news related to: "TOPIC". Original description'
            match = re.search(r'Find news related to: "([^"]+)"', section_description)
            topic = match.group(1) if match else section_description
            print(f"[DEBUG] Searching for related news on topic: {topic[:80]}...")
            
            date_context = get_current_date_context()
            current_year = datetime.now().year
            
            # Use Perplexity to search for related news
            search_prompt = ChatPromptTemplate.from_messages([
                ("system", f"""{date_context}

You are a digital marketing news researcher with real-time web access.

Search the web and find {{{{num_items}}}} REAL, recent news articles RELATED to this topic:
"{{{{topic}}}}"

Find news that:
- Covers similar themes or subjects
- Is from the same industry/niche
- Provides additional context or different perspectives
- Is recent (last 7 days preferred, from {current_year})

IMPORTANT: We are in {current_year}. All dates should be from {current_year}.

For each article provide:
1. title: The actual headline from the source
2. publisher: The actual publisher name
3. published_date: YYYY-MM-DD format (should be {current_year})
4. url: The ACTUAL, REAL URL (REQUIRED)
5. summary: 2-3 sentence summary
6. why_it_matters: Why this is relevant

Return ONLY valid JSON: {{{{"news": [...]}}}}"""),
                ("user", f"Find {{num_items}} news articles from {current_year} related to: {{topic}}")
            ])
            
            search_chain = search_prompt | self.search_llm | self.str_parser
            
            try:
                print(f"[DEBUG] Calling Perplexity for related news...")
                search_result = await search_chain.ainvoke({
                    "num_items": num_items,
                    "topic": topic
                })
                print(f"[DEBUG] Perplexity response received, length: {len(search_result)}")
                
                # Clean up response
                clean_result = search_result.strip()
                if clean_result.startswith("```"):
                    clean_result = re.sub(r'^```(?:json)?\s*', '', clean_result)
                    clean_result = re.sub(r'\s*```$', '', clean_result)
                
                # Additional cleanup: try to extract JSON if there's text before/after
                json_match = re.search(r'\{.*\}', clean_result, re.DOTALL)
                if json_match:
                    clean_result = json_match.group(0)
                
                print(f"[DEBUG] Cleaned result preview: {clean_result[:200]}...")
                
                try:
                    search_data = json.loads(clean_result)
                except json.JSONDecodeError as json_err:
                    print(f"[ERROR] JSON parsing failed: {json_err}")
                    print(f"[ERROR] Raw response: {search_result[:500]}...")
                    print(f"[ERROR] Cleaned result: {clean_result[:500]}...")
                    raise
                raw_articles = search_data.get("news", [])
                
                if raw_articles:
                    items = []
                    for article in raw_articles[:num_items]:
                        url = article.get("url", "").strip()
                        if url and url != "https://..." and url.startswith("http"):
                            item = NewsItem(
                                category="related",
                                title=article.get("title", ""),
                                publisher=article.get("publisher", "Industry Source"),
                                published_date=article.get("published_date", "2026-01-12"),
                                url=url,
                                summary=article.get("summary", ""),
                                why_it_matters=article.get("why_it_matters", ""),
                                tags=["related", "digital-marketing"],
                            )
                            if item.title:
                                items.append(item)
                    
                    if items:
                        print(f"[OK] Found {len(items)} related news items for: {topic[:50]}...")
                        return items
                    else:
                        print(f"[WARN] No valid items from Perplexity related search, falling back to categories")
                        
            except Exception as e:
                print(f"Related news search error: {e}")
        
        # Default behavior: fetch from multiple categories
        print(f"[DEBUG] Using default category-based search for: {section_title}")
        section_key = section_title.lower().replace(" ", "-").replace("'", "")
        
        items = []
        categories = ["seo", "ppc", "social_media", "website"]
        items_per_cat = max(1, num_items // len(categories))
        
        for cat in categories:
            cat_items = await self.fetch_news_with_catchy_titles(cat, num_items=items_per_cat)
            items.extend(cat_items)
        
        return self._dedupe_items(items)[:num_items]
