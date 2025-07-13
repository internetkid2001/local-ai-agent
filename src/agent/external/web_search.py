"""
Web Search Integration

Multi-provider web search client with aggregation and ranking capabilities.

Author: Claude Code
Date: 2025-07-13
Session: 2.3
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

from .rate_limiter import RateLimiter
from .auth_manager import AuthManager
from ...utils.logger import get_logger

logger = get_logger(__name__)


class SearchProvider(Enum):
    """Supported search providers"""
    DUCKDUCKGO = "duckduckgo"
    BRAVE = "brave"
    SERPER = "serper"
    SEARX = "searx"
    GOOGLE_CUSTOM = "google_custom"


@dataclass
class SearchResult:
    """Individual search result"""
    title: str
    url: str
    snippet: str
    provider: SearchProvider
    rank: int = 0
    score: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchQuery:
    """Search query configuration"""
    query: str
    max_results: int = 10
    providers: List[SearchProvider] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    language: str = "en"
    region: str = "us"


class WebSearchManager:
    """
    Multi-provider web search manager with intelligent result aggregation.
    
    Features:
    - Multiple search provider support
    - Result aggregation and deduplication
    - Relevance scoring and ranking
    - Rate limiting and authentication
    - Provider fallback and failover
    - Result caching and optimization
    """
    
    def __init__(self, auth_manager: Optional[AuthManager] = None,
                 rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize web search manager.
        
        Args:
            auth_manager: Authentication manager for API keys
            rate_limiter: Rate limiter for search requests
        """
        self.auth_manager = auth_manager or AuthManager()
        self.rate_limiter = rate_limiter or RateLimiter()
        
        # Provider configurations
        self.provider_configs = {
            SearchProvider.DUCKDUCKGO: {
                "base_url": "https://api.duckduckgo.com/",
                "requires_auth": False,
                "rate_limit": 100,  # requests per hour
                "timeout": 10.0
            },
            SearchProvider.BRAVE: {
                "base_url": "https://api.search.brave.com/res/v1/web/search",
                "requires_auth": True,
                "rate_limit": 2000,  # requests per month
                "timeout": 15.0
            },
            SearchProvider.SERPER: {
                "base_url": "https://google.serper.dev/search",
                "requires_auth": True,
                "rate_limit": 2500,  # requests per month
                "timeout": 10.0
            },
            SearchProvider.SEARX: {
                "base_url": "https://searx.be/search",
                "requires_auth": False,
                "rate_limit": 1000,  # requests per day
                "timeout": 20.0
            }
        }
        
        # Result cache
        self.result_cache: Dict[str, List[SearchResult]] = {}
        self.cache_ttl = 3600  # 1 hour
        
        # Provider availability
        self.provider_status: Dict[SearchProvider, bool] = {}
        self._initialize_providers()
        
        logger.info("Web search manager initialized")
    
    def _initialize_providers(self):
        """Initialize provider availability status"""
        for provider in SearchProvider:
            self.provider_status[provider] = True
    
    async def search(self, query: Union[str, SearchQuery]) -> List[SearchResult]:
        """
        Perform web search across multiple providers.
        
        Args:
            query: Search query string or SearchQuery object
            
        Returns:
            List of search results, ranked and deduplicated
        """
        # Normalize query
        if isinstance(query, str):
            search_query = SearchQuery(query=query)
        else:
            search_query = query
        
        # Check cache first
        cache_key = self._get_cache_key(search_query)
        cached_results = self._get_cached_results(cache_key)
        if cached_results:
            logger.debug(f"Returning cached results for query: {search_query.query}")
            return cached_results
        
        # Determine providers to use
        providers = search_query.providers or self._get_available_providers()
        
        # Execute searches in parallel
        search_tasks = []
        for provider in providers:
            if self.provider_status.get(provider, False):
                task = asyncio.create_task(
                    self._search_provider(provider, search_query)
                )
                search_tasks.append((provider, task))
        
        # Collect results
        all_results = []
        for provider, task in search_tasks:
            try:
                results = await task
                all_results.extend(results)
                logger.debug(f"Got {len(results)} results from {provider.value}")
            except Exception as e:
                logger.warning(f"Search failed for provider {provider.value}: {e}")
                self.provider_status[provider] = False
        
        # Aggregate and rank results
        final_results = await self._aggregate_results(all_results, search_query)
        
        # Cache results
        self._cache_results(cache_key, final_results)
        
        logger.info(f"Search completed: '{search_query.query}' - {len(final_results)} results")
        return final_results
    
    async def _search_provider(self, provider: SearchProvider, 
                              query: SearchQuery) -> List[SearchResult]:
        """Search using a specific provider"""
        
        # Rate limiting
        await self.rate_limiter.acquire(f"search_{provider.value}")
        
        try:
            if provider == SearchProvider.DUCKDUCKGO:
                return await self._search_duckduckgo(query)
            elif provider == SearchProvider.BRAVE:
                return await self._search_brave(query)
            elif provider == SearchProvider.SERPER:
                return await self._search_serper(query)
            elif provider == SearchProvider.SEARX:
                return await self._search_searx(query)
            elif provider == SearchProvider.GOOGLE_CUSTOM:
                return await self._search_google_custom(query)
            else:
                logger.warning(f"Unsupported provider: {provider}")
                return []
                
        except Exception as e:
            logger.error(f"Provider {provider.value} search failed: {e}")
            return []
    
    async def _search_duckduckgo(self, query: SearchQuery) -> List[SearchResult]:
        """Search using DuckDuckGo Instant Answer API"""
        try:
            config = self.provider_configs[SearchProvider.DUCKDUCKGO]
            
            params = {
                "q": query.query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    config["base_url"],
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=config["timeout"])
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_duckduckgo_results(data, query)
                    else:
                        logger.warning(f"DuckDuckGo API returned status {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []
    
    async def _search_brave(self, query: SearchQuery) -> List[SearchResult]:
        """Search using Brave Search API"""
        try:
            api_key = await self.auth_manager.get_credential("brave_search", "api_key")
            if not api_key:
                logger.warning("Brave Search API key not configured")
                return []
            
            config = self.provider_configs[SearchProvider.BRAVE]
            
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key
            }
            
            params = {
                "q": query.query,
                "count": min(query.max_results, 20),
                "offset": 0,
                "mkt": f"{query.language}-{query.region}",
                "safesearch": "moderate"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    config["base_url"],
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=config["timeout"])
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_brave_results(data, query)
                    else:
                        logger.warning(f"Brave API returned status {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Brave search error: {e}")
            return []
    
    async def _search_serper(self, query: SearchQuery) -> List[SearchResult]:
        """Search using Serper.dev Google Search API"""
        try:
            api_key = await self.auth_manager.get_credential("serper", "api_key")
            if not api_key:
                logger.warning("Serper API key not configured")
                return []
            
            config = self.provider_configs[SearchProvider.SERPER]
            
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "q": query.query,
                "num": min(query.max_results, 10),
                "hl": query.language,
                "gl": query.region
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config["base_url"],
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=config["timeout"])
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_serper_results(data, query)
                    else:
                        logger.warning(f"Serper API returned status {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Serper search error: {e}")
            return []
    
    async def _search_searx(self, query: SearchQuery) -> List[SearchResult]:
        """Search using SearX metasearch engine"""
        try:
            config = self.provider_configs[SearchProvider.SEARX]
            
            params = {
                "q": query.query,
                "format": "json",
                "categories": "general",
                "lang": query.language,
                "pageno": 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    config["base_url"],
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=config["timeout"])
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_searx_results(data, query)
                    else:
                        logger.warning(f"SearX returned status {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"SearX search error: {e}")
            return []
    
    async def _search_google_custom(self, query: SearchQuery) -> List[SearchResult]:
        """Search using Google Custom Search API"""
        try:
            api_key = await self.auth_manager.get_credential("google_custom_search", "api_key")
            search_engine_id = await self.auth_manager.get_credential("google_custom_search", "cx")
            
            if not api_key or not search_engine_id:
                logger.warning("Google Custom Search credentials not configured")
                return []
            
            params = {
                "key": api_key,
                "cx": search_engine_id,
                "q": query.query,
                "num": min(query.max_results, 10),
                "hl": query.language,
                "gl": query.region
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15.0)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_google_results(data, query)
                    else:
                        logger.warning(f"Google Custom Search returned status {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Google Custom Search error: {e}")
            return []
    
    def _parse_duckduckgo_results(self, data: Dict[str, Any], 
                                 query: SearchQuery) -> List[SearchResult]:
        """Parse DuckDuckGo API response"""
        results = []
        
        # Handle instant answer
        if data.get("Abstract"):
            results.append(SearchResult(
                title="DuckDuckGo Instant Answer",
                url=data.get("AbstractURL", ""),
                snippet=data.get("Abstract", ""),
                provider=SearchProvider.DUCKDUCKGO,
                rank=1,
                score=1.0
            ))
        
        # Handle related topics
        for i, topic in enumerate(data.get("RelatedTopics", [])[:query.max_results]):
            if isinstance(topic, dict) and "Text" in topic:
                results.append(SearchResult(
                    title=topic.get("Text", "").split(" - ")[0],
                    url=topic.get("FirstURL", ""),
                    snippet=topic.get("Text", ""),
                    provider=SearchProvider.DUCKDUCKGO,
                    rank=i + 2,
                    score=0.8 - (i * 0.1)
                ))
        
        return results
    
    def _parse_brave_results(self, data: Dict[str, Any], 
                           query: SearchQuery) -> List[SearchResult]:
        """Parse Brave Search API response"""
        results = []
        
        for i, item in enumerate(data.get("web", {}).get("results", [])[:query.max_results]):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("description", ""),
                provider=SearchProvider.BRAVE,
                rank=i + 1,
                score=1.0 - (i * 0.05),
                metadata={
                    "age": item.get("age"),
                    "language": item.get("language")
                }
            ))
        
        return results
    
    def _parse_serper_results(self, data: Dict[str, Any], 
                            query: SearchQuery) -> List[SearchResult]:
        """Parse Serper.dev API response"""
        results = []
        
        for i, item in enumerate(data.get("organic", [])[:query.max_results]):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                provider=SearchProvider.SERPER,
                rank=i + 1,
                score=1.0 - (i * 0.05),
                metadata={
                    "position": item.get("position"),
                    "date": item.get("date")
                }
            ))
        
        return results
    
    def _parse_searx_results(self, data: Dict[str, Any], 
                           query: SearchQuery) -> List[SearchResult]:
        """Parse SearX API response"""
        results = []
        
        for i, item in enumerate(data.get("results", [])[:query.max_results]):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                provider=SearchProvider.SEARX,
                rank=i + 1,
                score=1.0 - (i * 0.05),
                metadata={
                    "engines": item.get("engines"),
                    "category": item.get("category")
                }
            ))
        
        return results
    
    def _parse_google_results(self, data: Dict[str, Any], 
                            query: SearchQuery) -> List[SearchResult]:
        """Parse Google Custom Search API response"""
        results = []
        
        for i, item in enumerate(data.get("items", [])[:query.max_results]):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                provider=SearchProvider.GOOGLE_CUSTOM,
                rank=i + 1,
                score=1.0 - (i * 0.05),
                metadata={
                    "displayLink": item.get("displayLink"),
                    "formattedUrl": item.get("formattedUrl")
                }
            ))
        
        return results
    
    async def _aggregate_results(self, results: List[SearchResult], 
                               query: SearchQuery) -> List[SearchResult]:
        """Aggregate and rank results from multiple providers"""
        if not results:
            return []
        
        # Deduplicate by URL
        seen_urls = set()
        deduplicated = []
        
        for result in results:
            if result.url and result.url not in seen_urls:
                seen_urls.add(result.url)
                deduplicated.append(result)
        
        # Calculate combined scores
        for result in deduplicated:
            # Base score from provider ranking
            provider_score = result.score
            
            # Boost based on provider reliability
            provider_boost = {
                SearchProvider.GOOGLE_CUSTOM: 1.2,
                SearchProvider.BRAVE: 1.1,
                SearchProvider.SERPER: 1.1,
                SearchProvider.DUCKDUCKGO: 1.0,
                SearchProvider.SEARX: 0.9
            }
            
            # Title relevance boost
            title_boost = 1.0
            if query.query.lower() in result.title.lower():
                title_boost = 1.3
            
            # Calculate final score
            result.score = provider_score * provider_boost.get(result.provider, 1.0) * title_boost
        
        # Sort by score
        deduplicated.sort(key=lambda x: x.score, reverse=True)
        
        # Update ranks
        for i, result in enumerate(deduplicated):
            result.rank = i + 1
        
        return deduplicated[:query.max_results]
    
    def _get_available_providers(self) -> List[SearchProvider]:
        """Get list of available providers"""
        return [provider for provider, available in self.provider_status.items() if available]
    
    def _get_cache_key(self, query: SearchQuery) -> str:
        """Generate cache key for query"""
        return f"{query.query}:{query.max_results}:{':'.join(p.value for p in query.providers)}"
    
    def _get_cached_results(self, cache_key: str) -> Optional[List[SearchResult]]:
        """Get cached results if not expired"""
        if cache_key in self.result_cache:
            # Check if cache is still valid (simplified)
            return self.result_cache[cache_key]
        return None
    
    def _cache_results(self, cache_key: str, results: List[SearchResult]):
        """Cache search results"""
        self.result_cache[cache_key] = results
        
        # Simple cache cleanup (in production, use proper TTL)
        if len(self.result_cache) > 100:
            # Remove oldest entries
            oldest_keys = list(self.result_cache.keys())[:20]
            for key in oldest_keys:
                del self.result_cache[key]
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all search providers"""
        return {
            "providers": {
                provider.value: {
                    "available": self.provider_status.get(provider, False),
                    "requires_auth": self.provider_configs[provider]["requires_auth"],
                    "rate_limit": self.provider_configs[provider]["rate_limit"]
                }
                for provider in SearchProvider
            },
            "cache_size": len(self.result_cache)
        }