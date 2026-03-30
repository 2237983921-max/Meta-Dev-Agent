from __future__ import annotations

import asyncio
import math
import random
from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import Any

import httpx

BASE_URL = "https://api.dexscreener.com"
CACHE_TTL_SECONDS = 20
TRACKED_CHAINS = {"solana", "ethereum", "base", "bsc"}
DEFAULT_KEYWORDS = [
    "PEPE",
    "WIF",
    "BONK",
    "POPCAT",
    "FLOKI",
    "BRETT",
    "MEW",
    "MOG",
    "NEIRO",
    "FWOG",
    "GOAT",
    "SPX",
]
MEME_TERMS = {
    "meme",
    "pepe",
    "dog",
    "cat",
    "frog",
    "bonk",
    "wif",
    "floki",
    "shib",
    "inu",
    "mog",
    "neiro",
    "goat",
    "popcat",
    "fwog",
    "pengu",
    "sigma",
    "spx",
    "degen",
    "pump",
    "based",
    "pnut",
    "moodeng",
}
EXCLUDED_TERMS = {
    "usdc",
    "usdt",
    "wrapped bitcoin",
    "wrapped ethereum",
    "bitcoin",
    "ethereum",
    "ether",
    "solana",
    "tether",
    "usd coin",
    "wbtc",
    "weth",
}
PREFERRED_DEXES = {"raydium", "pumpfun", "pumpswap", "uniswap", "pancakeswap", "aerodrome"}
PAIR_QUOTES = {"SOL", "USDC", "USDT", "WETH", "ETH", "BNB", "WBNB"}


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def as_float(value: Any, default: float = 0.0) -> float:
    if value in (None, "", "null"):
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def unique_keywords(raw_keywords: list[str] | None) -> list[str]:
    source = raw_keywords or DEFAULT_KEYWORDS
    normalized: list[str] = []
    seen: set[str] = set()

    for keyword in source:
        value = keyword.strip()
        if not value:
            continue

        key = value.lower()
        if key in seen:
            continue

        normalized.append(value)
        seen.add(key)

    return normalized or list(DEFAULT_KEYWORDS)


class DexMemeService:
    def __init__(self) -> None:
        self.client: httpx.AsyncClient | None = None
        self.lock = asyncio.Lock()
        self.cache: dict[str, Any] | None = None
        self.cache_key: tuple[str, ...] = tuple(DEFAULT_KEYWORDS)
        self.cache_expiry = 0.0
        self.histories: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=24))

    async def startup(self) -> None:
        self.client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=httpx.Timeout(20.0, connect=10.0),
            headers={"Accept": "application/json", "User-Agent": "MemeRadarLive/1.0"},
        )

    async def shutdown(self) -> None:
        if self.client is not None:
            await self.client.aclose()

    async def get_dashboard(self, keywords: list[str] | None = None) -> dict[str, Any]:
        final_keywords = tuple(unique_keywords(keywords))
        current_time = asyncio.get_running_loop().time()

        if self.cache and self.cache_key == final_keywords and current_time < self.cache_expiry:
            return self.cache

        async with self.lock:
            current_time = asyncio.get_running_loop().time()
            if self.cache and self.cache_key == final_keywords and current_time < self.cache_expiry:
                return self.cache

            dashboard = await self._build_dashboard(list(final_keywords))
            self.cache = dashboard
            self.cache_key = final_keywords
            self.cache_expiry = current_time + CACHE_TTL_SECONDS
            return dashboard

    async def _build_dashboard(self, keywords: list[str]) -> dict[str, Any]:
        profiles_task = self._get_json("/token-profiles/latest/v1")
        boost_top_task = self._get_json("/token-boosts/top/v1")
        boost_latest_task = self._get_json("/token-boosts/latest/v1")
        takeovers_task = self._get_json("/community-takeovers/latest/v1")
        search_tasks = [self._get_json("/latest/dex/search", params={"q": keyword}) for keyword in keywords]

        profiles, boosts_top, boosts_latest, takeovers, *search_results = await asyncio.gather(
            profiles_task,
            boost_top_task,
            boost_latest_task,
            takeovers_task,
            *search_tasks,
        )

        discovery_tokens = self._collect_discovery_entries(profiles, boosts_top, boosts_latest, takeovers)
        discovery_pairs = await self._fetch_pairs_for_tokens(discovery_tokens)
        search_pairs = self._collect_search_pairs(keywords, search_results)

        token_map: dict[str, dict[str, Any]] = {}

        for pair in discovery_pairs:
            token = self._normalize_pair(pair, search_keyword=None)
            if not token or not self._is_meme_candidate(token, keywords):
                continue
            token_map[token["id"]] = token

        for keyword, pairs in search_pairs.items():
            selected_pair = self._pick_best_search_pair(keyword, pairs)
            if not selected_pair:
                continue

            token = self._normalize_pair(selected_pair, search_keyword=keyword)
            if not token:
                continue

            existing = token_map.get(token["id"])
            if existing:
                existing["sources"] = sorted(set(existing["sources"]) | {"search"})
                existing["matchedKeywords"] = sorted(set(existing["matchedKeywords"]) | {keyword})
                existing["score"] = max(existing["score"], token["score"])
                if token["boostActive"] > existing["boostActive"]:
                    existing["boostActive"] = token["boostActive"]
            elif self._is_meme_candidate(token, keywords, force_if_query=True):
                token_map[token["id"]] = token

        tokens = sorted(token_map.values(), key=lambda item: item["score"], reverse=True)[:24]
        feed = self._build_feed(tokens)
        alerts = [item for item in feed if item["importance"] >= 72][:8]
        socials = self._build_social_cards(tokens)
        summary = self._build_summary(tokens, feed, alerts)

        return {
            "generatedAt": now_iso(),
            "mode": "live",
            "source": "DEX Screener",
            "keywords": keywords,
            "summary": summary,
            "tokens": tokens,
            "feed": feed,
            "alerts": alerts,
            "socials": socials,
        }

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if self.client is None:
            raise RuntimeError("DexMemeService has not been started")

        response = await self.client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def _collect_discovery_entries(self, *sources: Any) -> dict[tuple[str, str], dict[str, Any]]:
        collected: dict[tuple[str, str], dict[str, Any]] = {}

        for source in sources:
            if not isinstance(source, list):
                continue

            for entry in source[:40]:
                chain_id = str(entry.get("chainId", "")).lower()
                token_address = entry.get("tokenAddress")
                if chain_id not in TRACKED_CHAINS or not token_address:
                    continue

                key = (chain_id, token_address)
                current = collected.get(key, {})
                links = current.get("links", []) + (entry.get("links") or [])
                collected[key] = {
                    "chainId": chain_id,
                    "tokenAddress": token_address,
                    "description": current.get("description") or entry.get("description") or "",
                    "links": links,
                    "amount": max(as_float(current.get("amount")), as_float(entry.get("amount"))),
                    "totalAmount": max(as_float(current.get("totalAmount")), as_float(entry.get("totalAmount"))),
                    "sources": sorted(set(current.get("sources", [])) | {self._infer_source_name(source)}),
                }

        return collected

    def _infer_source_name(self, source: Any) -> str:
        if source and isinstance(source, list):
            sample = source[0] if source else {}
            if "claimDate" in sample:
                return "takeover"
            if "totalAmount" in sample or "amount" in sample:
                return "boost"
            return "profile"
        return "profile"

    async def _fetch_pairs_for_tokens(self, tokens: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
        by_chain: dict[str, list[str]] = defaultdict(list)
        metadata_by_key: dict[str, dict[str, Any]] = {}

        for (chain_id, token_address), metadata in tokens.items():
            by_chain[chain_id].append(token_address)
            metadata_by_key[f"{chain_id}:{token_address.lower()}"] = metadata

        tasks = []
        for chain_id, addresses in by_chain.items():
            for chunk in chunked(addresses, 30):
                tasks.append(self._get_json(f"/tokens/v1/{chain_id}/" + ",".join(chunk)))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks)
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for result in results:
            if not isinstance(result, list):
                continue

            for pair in result:
                chain_id = str(pair.get("chainId", "")).lower()
                address = str(pair.get("baseToken", {}).get("address", "")).lower()
                if not address:
                    continue
                grouped[f"{chain_id}:{address}"].append(pair)

        selected: list[dict[str, Any]] = []
        for key, pairs in grouped.items():
            best_pair = max(pairs, key=self._pair_rank)
            metadata = metadata_by_key.get(key, {})
            best_pair["_meta"] = metadata
            selected.append(best_pair)

        return selected

    def _collect_search_pairs(self, keywords: list[str], responses: list[Any]) -> dict[str, list[dict[str, Any]]]:
        results: dict[str, list[dict[str, Any]]] = {}

        for keyword, payload in zip(keywords, responses, strict=False):
            pairs = payload.get("pairs", []) if isinstance(payload, dict) else []
            filtered = []

            for pair in pairs[:40]:
                chain_id = str(pair.get("chainId", "")).lower()
                if chain_id not in TRACKED_CHAINS:
                    continue
                if as_float(pair.get("liquidity", {}).get("usd")) <= 0:
                    continue
                filtered.append(pair)

            results[keyword] = filtered

        return results

    def _pick_best_search_pair(self, keyword: str, pairs: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not pairs:
            return None

        normalized = keyword.lower()
        ranked = sorted(pairs, key=lambda pair: self._search_rank(pair, normalized), reverse=True)
        return ranked[0]

    def _search_rank(self, pair: dict[str, Any], keyword: str) -> float:
        name = str(pair.get("baseToken", {}).get("name", "")).lower()
        symbol = str(pair.get("baseToken", {}).get("symbol", "")).lower()
        description = str(pair.get("info", {}) or {}).lower()
        exact_match = 60 if symbol == keyword or name == keyword else 0
        starts_match = 18 if symbol.startswith(keyword) or name.startswith(keyword) else 0
        contains_match = 10 if keyword in f"{symbol} {name} {description}" else 0
        return exact_match + starts_match + contains_match + self._pair_rank(pair)

    def _pair_rank(self, pair: dict[str, Any]) -> float:
        liquidity = as_float(pair.get("liquidity", {}).get("usd"))
        volume = as_float(pair.get("volume", {}).get("h24"))
        boosts = as_float(pair.get("boosts", {}).get("active"))
        market_cap = as_float(pair.get("marketCap")) or as_float(pair.get("fdv"))
        price_change = abs(as_float(pair.get("priceChange", {}).get("h24")))
        dex_bonus = 18 if str(pair.get("dexId", "")).lower() in PREFERRED_DEXES else 0
        quote_bonus = 12 if str(pair.get("quoteToken", {}).get("symbol", "")).upper() in PAIR_QUOTES else 0
        return (
            dex_bonus
            + quote_bonus
            + min(liquidity / 5000, 50)
            + min(volume / 15000, 40)
            + min(boosts * 0.3, 15)
            + min(market_cap / 1_000_000, 12)
            + min(price_change * 0.15, 12)
        )

    def _normalize_pair(self, pair: dict[str, Any], search_keyword: str | None) -> dict[str, Any] | None:
        chain_id = str(pair.get("chainId", "")).lower()
        base_token = pair.get("baseToken") or {}
        token_address = str(base_token.get("address", "")).strip()
        if not token_address:
            return None

        symbol_raw = str(base_token.get("symbol", "")).strip()
        clean_symbol = symbol_raw.lstrip("$")

        token_id = f"{chain_id}:{token_address.lower()}"
        info = pair.get("info") or {}
        meta = pair.get("_meta") or {}
        price_usd = as_float(pair.get("priceUsd"))
        liquidity_usd = as_float(pair.get("liquidity", {}).get("usd"))
        volume_h24 = as_float(pair.get("volume", {}).get("h24"))
        volume_h1 = as_float(pair.get("volume", {}).get("h1"))
        market_cap = as_float(pair.get("marketCap")) or as_float(pair.get("fdv"))
        price_change_h24 = as_float(pair.get("priceChange", {}).get("h24"))
        price_change_h6 = as_float(pair.get("priceChange", {}).get("h6"))
        price_change_h1 = as_float(pair.get("priceChange", {}).get("h1"))
        age_hours = self._age_hours(pair.get("pairCreatedAt"))
        links = self._merge_links(info, meta)
        matched_keywords = [search_keyword] if search_keyword else []
        sources = set(meta.get("sources", []))
        if search_keyword:
            sources.add("search")

        score = self._score_token(
            liquidity_usd=liquidity_usd,
            volume_h24=volume_h24,
            price_change_h24=price_change_h24,
            boosts=as_float(pair.get("boosts", {}).get("active")) or as_float(meta.get("totalAmount")),
            market_cap=market_cap,
            social_count=len(links["socials"]),
            age_hours=age_hours,
            keyword_matches=len(matched_keywords),
        )
        sentiment = self._sentiment_score(price_change_h24, volume_h24, liquidity_usd, market_cap)
        sparkline = self._update_history(
            token_id,
            price_usd if price_usd > 0 else market_cap,
            price_change_h24,
        )
        tags = self._build_tags(
            liquidity_usd=liquidity_usd,
            volume_h24=volume_h24,
            volume_h1=volume_h1,
            price_change_h24=price_change_h24,
            boosts=as_float(pair.get("boosts", {}).get("active")) or as_float(meta.get("totalAmount")),
            age_hours=age_hours,
            social_count=len(links["socials"]),
        )

        return {
            "id": token_id,
            "chain": chain_id,
            "symbol": f"${clean_symbol.upper()}",
            "symbolRaw": clean_symbol,
            "name": base_token.get("name", ""),
            "tokenAddress": token_address,
            "pairAddress": pair.get("pairAddress"),
            "pairUrl": pair.get("url"),
            "dexId": pair.get("dexId"),
            "icon": info.get("imageUrl") or meta.get("icon"),
            "header": info.get("header") or meta.get("header"),
            "description": meta.get("description") or "",
            "priceUsd": price_usd,
            "priceNative": as_float(pair.get("priceNative")),
            "priceChange": {
                "h1": price_change_h1,
                "h6": price_change_h6,
                "h24": price_change_h24,
            },
            "txns": pair.get("txns") or {},
            "volume": {
                "h1": volume_h1,
                "h6": as_float(pair.get("volume", {}).get("h6")),
                "h24": volume_h24,
                "m5": as_float(pair.get("volume", {}).get("m5")),
            },
            "liquidityUsd": liquidity_usd,
            "marketCap": market_cap,
            "fdv": as_float(pair.get("fdv")),
            "boostActive": int(as_float(pair.get("boosts", {}).get("active")) or as_float(meta.get("totalAmount"))),
            "pairCreatedAt": pair.get("pairCreatedAt"),
            "ageHours": age_hours,
            "score": score,
            "sentiment": sentiment,
            "sparkline": sparkline,
            "links": links,
            "socialCount": len(links["socials"]),
            "websiteCount": len(links["websites"]),
            "tags": tags,
            "sources": sorted(sources or {"live"}),
            "matchedKeywords": matched_keywords,
        }

    def _merge_links(self, info: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
        websites: list[str] = []
        socials: list[dict[str, str]] = []

        for website in info.get("websites") or []:
            url = website.get("url")
            if url and url not in websites:
                websites.append(url)

        for social in info.get("socials") or []:
            url = social.get("url")
            if url:
                socials.append({"type": social.get("type") or social.get("platform") or "social", "url": url})

        for link in meta.get("links") or []:
            url = link.get("url")
            if not url:
                continue

            link_type = (link.get("type") or "").lower()
            if link_type in {"twitter", "telegram", "discord", "instagram", "tiktok"}:
                if not any(existing["url"] == url for existing in socials):
                    socials.append({"type": link_type, "url": url})
            elif url not in websites:
                websites.append(url)

        twitter = next((item["url"] for item in socials if item["type"] == "twitter"), "")
        telegram = next((item["url"] for item in socials if item["type"] == "telegram"), "")
        website = websites[0] if websites else ""

        return {
            "twitter": twitter,
            "telegram": telegram,
            "website": website,
            "socials": socials,
            "websites": websites,
        }

    def _age_hours(self, pair_created_at: Any) -> float:
        timestamp = as_float(pair_created_at)
        if not timestamp:
            return 9999.0

        created_at = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
        return max(0.0, (datetime.now(UTC) - created_at).total_seconds() / 3600)

    def _score_token(
        self,
        *,
        liquidity_usd: float,
        volume_h24: float,
        price_change_h24: float,
        boosts: float,
        market_cap: float,
        social_count: int,
        age_hours: float,
        keyword_matches: int,
    ) -> int:
        liquidity_score = min(liquidity_usd / 8_000, 25)
        volume_score = min(volume_h24 / 20_000, 25)
        boost_score = min(boosts * 0.3, 18)
        momentum_score = max(-12, min(price_change_h24 * 0.45, 18))
        age_score = 10 if age_hours <= 24 else 6 if age_hours <= 72 else 0
        social_score = min(social_count * 2.5, 10)
        market_cap_score = 6 if market_cap <= 150_000_000 else 0
        keyword_score = min(keyword_matches * 4, 8)
        score = 18 + liquidity_score + volume_score + boost_score + momentum_score + age_score + social_score + market_cap_score + keyword_score
        return max(0, min(100, round(score)))

    def _sentiment_score(self, price_change_h24: float, volume_h24: float, liquidity_usd: float, market_cap: float) -> int:
        liquidity_factor = min(liquidity_usd / 25_000, 12)
        volume_factor = min(volume_h24 / 50_000, 18)
        cap_factor = 6 if 0 < market_cap < 150_000_000 else 2
        momentum = max(-18, min(price_change_h24 * 0.55, 28))
        return max(5, min(95, round(42 + liquidity_factor + volume_factor + cap_factor + momentum)))

    def _update_history(self, token_id: str, current_value: float, price_change_h24: float) -> list[float]:
        history = self.histories[token_id]
        if current_value <= 0:
            return list(history) if history else [0]

        if not history:
            history.extend(self._bootstrap_history(token_id, current_value, price_change_h24))

        last_value = history[-1]
        if not math.isclose(last_value, current_value, rel_tol=1e-6, abs_tol=1e-9):
            history.append(round(current_value, 8))

        return [round(value, 8) for value in history]

    def _bootstrap_history(self, token_id: str, current_value: float, price_change_h24: float) -> list[float]:
        rng = random.Random(token_id)
        change_ratio = price_change_h24 / 100 if price_change_h24 else 0
        start_value = current_value / max(0.15, 1 + change_ratio)
        points: list[float] = []

        for index in range(18):
            progress = index / 17
            base = start_value + (current_value - start_value) * progress
            noise = (rng.random() - 0.5) * max(current_value * 0.04, 0.00000001)
            points.append(max(current_value * 0.08, round(base + noise, 8)))

        points[-1] = round(current_value, 8)
        return points

    def _build_tags(
        self,
        *,
        liquidity_usd: float,
        volume_h24: float,
        volume_h1: float,
        price_change_h24: float,
        boosts: float,
        age_hours: float,
        social_count: int,
    ) -> list[str]:
        tags: list[str] = []
        if age_hours <= 24:
            tags.append("新币")
        if boosts > 0:
            tags.append("Boost")
        if price_change_h24 >= 20:
            tags.append("强趋势")
        if price_change_h24 <= -20:
            tags.append("高回撤")
        if volume_h1 >= max(10_000, volume_h24 * 0.16):
            tags.append("量能放大")
        if liquidity_usd < 25_000:
            tags.append("高波动")
        if social_count >= 2:
            tags.append("社媒活跃")
        return tags

    def _is_meme_candidate(
        self,
        token: dict[str, Any],
        keywords: list[str],
        *,
        force_if_query: bool = False,
    ) -> bool:
        text = " ".join(
            [
                token.get("symbolRaw", ""),
                token.get("name", ""),
                token.get("description", ""),
                " ".join(token.get("matchedKeywords", [])),
            ]
        ).lower()

        if any(excluded in text for excluded in EXCLUDED_TERMS):
            return False

        if force_if_query and token.get("matchedKeywords"):
            return True

        if any(keyword.lower() in text for keyword in keywords):
            return True

        if any(term in text for term in MEME_TERMS):
            return True

        if token.get("boostActive", 0) > 0 and token.get("marketCap", 0) < 250_000_000:
            return True

        return False

    def _build_feed(self, tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
        feed: list[dict[str, Any]] = []

        for token in tokens[:18]:
            if token["ageHours"] <= 12:
                feed.append(
                    self._feed_item(
                        token,
                        item_type="new-pair",
                        title=f"{token['symbol']} 进入新币窗口",
                        description=f"该交易对创建于 {token['ageHours']:.1f} 小时前，当前流动性 {self._short_currency(token['liquidityUsd'])}。",
                        importance=88,
                        badge="🆕 新币",
                        timestamp=token.get("pairCreatedAt"),
                    )
                )

            if token["boostActive"] > 0:
                feed.append(
                    self._feed_item(
                        token,
                        item_type="boosted",
                        title=f"{token['symbol']} 正在被加热",
                        description=f"当前活跃 boost {token['boostActive']}，24h 成交 {self._short_currency(token['volume']['h24'])}。",
                        importance=min(95, 62 + token["boostActive"] // 20),
                        badge="🔥 Boost",
                    )
                )

            if token["priceChange"]["h24"] >= 18:
                feed.append(
                    self._feed_item(
                        token,
                        item_type="momentum-up",
                        title=f"{token['symbol']} 24h 动能抬升",
                        description=f"24h 涨幅 {token['priceChange']['h24']:.2f}% ，流动性 {self._short_currency(token['liquidityUsd'])}。",
                        importance=74,
                        badge="📈 动量",
                    )
                )

            if token["volume"]["h1"] >= max(10_000, token["volume"]["h24"] * 0.16):
                feed.append(
                    self._feed_item(
                        token,
                        item_type="volume-spike",
                        title=f"{token['symbol']} 1h 成交放大",
                        description=f"1h 成交 {self._short_currency(token['volume']['h1'])}，24h 总成交 {self._short_currency(token['volume']['h24'])}。",
                        importance=78,
                        badge="⚡ 量能",
                    )
                )

            if token["priceChange"]["h24"] <= -20:
                feed.append(
                    self._feed_item(
                        token,
                        item_type="drawdown",
                        title=f"{token['symbol']} 出现高回撤",
                        description=f"24h 回撤 {abs(token['priceChange']['h24']):.2f}% ，更适合放进观察列表继续盯。",
                        importance=69,
                        badge="🩸 回撤",
                    )
                )

        feed.sort(key=lambda item: (item["importance"], item["timestamp"]), reverse=True)
        return feed[:40]

    def _feed_item(
        self,
        token: dict[str, Any],
        *,
        item_type: str,
        title: str,
        description: str,
        importance: int,
        badge: str,
        timestamp: Any | None = None,
    ) -> dict[str, Any]:
        event_time = now_iso()
        if timestamp:
            event_time = datetime.fromtimestamp(as_float(timestamp) / 1000, tz=UTC).isoformat()

        return {
            "id": f"{item_type}:{token['id']}",
            "type": item_type,
            "title": title,
            "description": description,
            "importance": importance,
            "badge": badge,
            "timestamp": event_time,
            "tokenId": token["id"],
            "symbol": token["symbol"],
            "name": token["name"],
            "chain": token["chain"],
            "icon": token["icon"],
            "priceUsd": token["priceUsd"],
            "priceChange24h": token["priceChange"]["h24"],
            "volumeH24": token["volume"]["h24"],
            "liquidityUsd": token["liquidityUsd"],
        }

    def _build_social_cards(self, tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []

        for token in tokens:
            if not token["links"]["socials"] and not token["links"]["websites"]:
                continue

            cards.append(
                {
                    "id": token["id"],
                    "symbol": token["symbol"],
                    "name": token["name"],
                    "chain": token["chain"],
                    "icon": token["icon"],
                    "twitter": token["links"]["twitter"],
                    "telegram": token["links"]["telegram"],
                    "website": token["links"]["website"],
                    "boostActive": token["boostActive"],
                    "socialCount": token["socialCount"],
                    "description": token["description"],
                    "score": token["score"],
                }
            )

        return cards[:18]

    def _build_summary(self, tokens: list[dict[str, Any]], feed: list[dict[str, Any]], alerts: list[dict[str, Any]]) -> dict[str, Any]:
        tracked = len(tokens)
        total_liquidity = sum(token["liquidityUsd"] for token in tokens)
        total_volume = sum(token["volume"]["h24"] for token in tokens)
        avg_change = sum(token["priceChange"]["h24"] for token in tokens) / tracked if tracked else 0.0
        avg_sentiment = sum(token["sentiment"] for token in tokens) / tracked if tracked else 0.0
        top_token = tokens[0] if tokens else {}
        dominant_chain = self._dominant_chain(tokens)

        market_mode = "风险偏好走强"
        if avg_change < 0:
            market_mode = "波动偏弱"
        elif avg_change < 8:
            market_mode = "高低切换"

        return {
            "trackedTokens": tracked,
            "signals": len(feed),
            "alerts": len(alerts),
            "watchCandidates": sum(1 for token in tokens if token["score"] >= 72),
            "topToken": top_token.get("symbol", "-"),
            "topNarrative": self._infer_narrative(tokens),
            "dominantChain": dominant_chain,
            "marketMode": market_mode,
            "avgChange24h": round(avg_change, 2),
            "avgSentiment": round(avg_sentiment),
            "totalLiquidityUsd": round(total_liquidity, 2),
            "totalVolume24h": round(total_volume, 2),
        }

    def _dominant_chain(self, tokens: list[dict[str, Any]]) -> str:
        counts: dict[str, int] = defaultdict(int)
        for token in tokens:
            counts[token["chain"]] += 1

        return max(counts.items(), key=lambda item: item[1])[0] if counts else "solana"

    def _infer_narrative(self, tokens: list[dict[str, Any]]) -> str:
        if not tokens:
            return "动物系"

        animal_points = 0
        ai_points = 0
        chaos_points = 0

        for token in tokens:
            text = f"{token['name']} {token['description']} {token['symbolRaw']}".lower()
            if any(term in text for term in ["dog", "cat", "frog", "shib", "pengu", "pepe"]):
                animal_points += 1
            if any(term in text for term in ["ai", "grok", "quant", "agent"]):
                ai_points += 1
            if any(term in text for term in ["pump", "degen", "sigma", "goat", "meme"]):
                chaos_points += 1

        scores = [("动物系", animal_points), ("AI Meme", ai_points), ("社区混沌流", chaos_points)]
        return max(scores, key=lambda item: item[1])[0]

    def _short_currency(self, value: float) -> str:
        if value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        if value >= 1_000:
            return f"${value / 1_000:.1f}K"
        return f"${value:.0f}"
