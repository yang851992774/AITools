from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.schemas.common import PublisherAppRecord, PublisherDiscoveryResult, StoreEnum, StoreFetchResult


class GooglePlayClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.timeout = self.settings.request_timeout_seconds
        self.headers = {
            "User-Agent": self.settings.user_agent,
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def fetch_app(self, *, package_name: str, region: str) -> StoreFetchResult:
        url = self._build_detail_url(package_name=package_name, region=region)
        observed_at = datetime.now(timezone.utc)
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
            response = await client.get(url)

        if response.status_code >= 400:
            return StoreFetchResult(
                store=StoreEnum.GOOGLE_PLAY,
                region=region.upper(),
                is_visible=False,
                url=url,
                fetch_status="success",
                raw_payload={"status_code": response.status_code},
                observed_at=observed_at,
            )

        soup = BeautifulSoup(response.text, "html.parser")
        title = self._extract_meta(soup, "og:title")
        if not title or title.casefold() == "google play" or "not found" in response.text.casefold():
            return StoreFetchResult(
                store=StoreEnum.GOOGLE_PLAY,
                region=region.upper(),
                is_visible=False,
                url=url,
                raw_payload={"html_length": len(response.text)},
                observed_at=observed_at,
            )

        developer_name = None
        developer_anchor = soup.select_one("a.hrTbp.R8zArc")
        if developer_anchor:
            developer_name = developer_anchor.get_text(strip=True)

        category = None
        category_anchor = soup.select_one("a[itemprop='genre']")
        if category_anchor:
            category = category_anchor.get_text(strip=True)

        version = None
        for node in soup.select("div.hAyfc"):
            label = node.select_one("div.BgcNfc")
            value = node.select_one("span.htlgb")
            if not label or not value:
                continue
            if label.get_text(strip=True).casefold() == "current version":
                version = value.get_text(strip=True)
                break

        metadata = {
            "installs": self._extract_detail_value(soup, "Installs"),
            "content_rating": self._extract_detail_value(soup, "Content rating"),
            "developer_url": developer_anchor.get("href") if developer_anchor else None,
            "image": self._extract_meta(soup, "og:image"),
        }

        return StoreFetchResult(
            store=StoreEnum.GOOGLE_PLAY,
            region=region.upper(),
            is_visible=True,
            title=title,
            developer_name=developer_name,
            version=version,
            category=category,
            url=url,
            metadata=metadata,
            raw_payload={"html_length": len(response.text)},
            observed_at=observed_at,
        )

    async def discover_publisher(
        self,
        *,
        region: str,
        publisher_name: str,
        publisher_url: str | None = None,
    ) -> PublisherDiscoveryResult:
        url = publisher_url or self._build_publisher_url(region=region, publisher_name=publisher_name)
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        apps: list[PublisherAppRecord] = []
        raw_payload: list[dict] = []
        seen: set[str] = set()
        for anchor in soup.select("a[href*='/store/apps/details?id=']"):
            href = anchor.get("href") or ""
            if "id=" not in href:
                continue
            package_name = href.split("id=")[-1].split("&")[0]
            if package_name in seen:
                continue
            seen.add(package_name)
            name = anchor.get("aria-label") or anchor.get_text(strip=True) or package_name
            full_url = href if href.startswith("http") else f"https://play.google.com{href}"
            apps.append(
                PublisherAppRecord(
                    external_key=f"google_play:{package_name}",
                    name=name,
                    developer_name=publisher_name,
                    url=full_url,
                    package_name=package_name,
                    category="Game",
                    metadata={"source_url": url},
                )
            )
            raw_payload.append({"package_name": package_name, "url": full_url, "name": name})

        return PublisherDiscoveryResult(
            store=StoreEnum.GOOGLE_PLAY,
            region=region.upper(),
            apps=apps,
            raw_payload=raw_payload,
            observed_at=datetime.now(timezone.utc),
        )

    def _build_detail_url(self, *, package_name: str, region: str) -> str:
        return f"https://play.google.com/store/apps/details?id={quote_plus(package_name)}&hl=en&gl={region.upper()}"

    def _build_publisher_url(self, *, region: str, publisher_name: str) -> str:
        query = quote_plus(f"pub:{publisher_name}")
        return f"https://play.google.com/store/search?q={query}&c=apps&hl=en&gl={region.upper()}"

    def _extract_meta(self, soup: BeautifulSoup, property_name: str) -> str | None:
        tag = soup.find("meta", attrs={"property": property_name})
        if tag and tag.get("content"):
            return tag["content"].strip()
        return None

    def _extract_detail_value(self, soup: BeautifulSoup, label_name: str) -> str | None:
        for node in soup.select("div.hAyfc"):
            label = node.select_one("div.BgcNfc")
            value = node.select_one("span.htlgb")
            if not label or not value:
                continue
            if label.get_text(strip=True).casefold() == label_name.casefold():
                return value.get_text(strip=True)
        return None
