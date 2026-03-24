from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.schemas.common import PublisherAppRecord, PublisherDiscoveryResult, StoreEnum, StoreFetchResult
from app.services.store_clients.http_client import resilient_get

logger = logging.getLogger(__name__)


class GooglePlayClient:
    STORE_KEY = "google_play"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.timeout = self.settings.request_timeout_seconds

    async def fetch_app(self, *, package_name: str, region: str) -> StoreFetchResult:
        url = self._build_detail_url(package_name=package_name, region=region)
        observed_at = datetime.now(timezone.utc)
        response = await resilient_get(url, store=self.STORE_KEY, timeout=self.timeout)

        if response.status_code in (403, 429) and self.settings.enable_browser_fallback:
            logger.info("HTTP %d for %s – falling back to browser", response.status_code, package_name)
            return await self._fetch_app_browser(url=url, region=region, observed_at=observed_at)

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

        return self._parse_detail_html(soup=soup, html=response.text, url=url, region=region, observed_at=observed_at)

    def _extract_script_data(self, soup: BeautifulSoup) -> list | None:
        """Extract the main app details array from AF_initDataCallback ds:5 script."""
        for s in soup.find_all("script"):
            txt = s.string or ""
            if "AF_initDataCallback" not in txt or "'ds:5'" not in txt:
                continue
            data_match = re.search(r"data:(.*?),\s*sideChannel:", txt, re.DOTALL)
            if not data_match:
                data_match = re.search(r"data:(.*)\}\s*\)\s*;?\s*$", txt, re.DOTALL)
            if not data_match:
                continue
            raw = data_match.group(1).strip()
            raw = raw.replace("null", "None").replace("true", "True").replace("false", "False")
            try:
                return eval(raw)  # noqa: S307
            except Exception:
                logger.debug("Failed to eval ds:5 data")
        return None

    def _safe_get(self, data: list, *indices) -> object:
        """Safely traverse nested lists by index path."""
        current = data
        for idx in indices:
            if not isinstance(current, list) or idx >= len(current):
                return None
            current = current[idx]
        return current

    async def discover_publisher(
        self,
        *,
        region: str,
        publisher_name: str,
        publisher_url: str | None = None,
    ) -> PublisherDiscoveryResult:
        url = publisher_url or self._build_publisher_url(region=region, publisher_name=publisher_name)
        response = await resilient_get(url, store=self.STORE_KEY, timeout=self.timeout)
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

    def _extract_itemprop(self, soup: BeautifulSoup, itemprop_name: str) -> str | None:
        tag = soup.find(attrs={"itemprop": itemprop_name})
        if tag:
            return (tag.get("content") or tag.get_text(strip=True)) or None
        return None

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

    def _parse_detail_html(
        self,
        *,
        soup: BeautifulSoup,
        html: str,
        url: str,
        region: str,
        observed_at: datetime,
        fetch_status: str = "success",
    ) -> StoreFetchResult:
        title = self._extract_meta(soup, "og:title")
        icon_url = self._extract_meta(soup, "og:image")

        developer_name = None
        version = None
        rating = None
        rating_count = None
        price_str = None
        installs = None
        content_rating = None
        file_size = None
        last_updated = None
        whats_new = None
        category = None
        developer_url = None

        script_data = self._extract_script_data(soup)
        if script_data:
            d = self._safe_get(script_data, 1, 2)
            if isinstance(d, list):
                if not title:
                    title = self._safe_get(d, 0, 0)

                developer_name = self._safe_get(d, 68, 0)
                if not developer_name:
                    developer_name = self._safe_get(d, 37, 0)

                rating_block = self._safe_get(d, 51)
                if isinstance(rating_block, list) and rating_block:
                    rv = self._safe_get(rating_block, 0, 1)
                    if isinstance(rv, (int, float)):
                        rating = round(float(rv), 2)
                    rc = self._safe_get(rating_block, 2, 1)
                    if isinstance(rc, int):
                        rating_count = rc

                dl_block = self._safe_get(d, 13)
                if isinstance(dl_block, list) and dl_block:
                    installs = self._safe_get(dl_block, 0)

                cr = self._safe_get(d, 9, 0)
                if isinstance(cr, str):
                    content_rating = cr

                iap = self._safe_get(d, 19, 0)
                if isinstance(iap, str):
                    price_str = iap

                cat_block = self._safe_get(d, 79)
                if isinstance(cat_block, list) and cat_block:
                    category = self._safe_get(cat_block, 0, 0, 0)

                dev_url = self._safe_get(d, 68, 1, 4, 2)
                if isinstance(dev_url, str):
                    developer_url = f"https://play.google.com{dev_url}" if dev_url.startswith("/") else dev_url

                raw_str = str(d)
                version_match = re.search(r"\[\[\['(\d+\.\d+[^']*)'\]\]", raw_str)
                if version_match:
                    raw_ver = version_match.group(1)
                    version = raw_ver.split("_")[0]

                rn_match = re.search(
                    r"\[None,\s*\[None,\s*'((?:[^'\\]|\\.)+)'\]\],\s*\[\['[A-Z][a-z]+ \d+, \d{4}'",
                    raw_str,
                )
                if not rn_match:
                    rn_match = re.search(
                        r"\[None,\s*'((?:Version|Update|New|Bug|Fix|Patch|What)[^']{10,})'",
                        raw_str,
                    )
                if rn_match:
                    whats_new = rn_match.group(1)
                    whats_new = whats_new.replace("&quot;", '"').replace("&amp;", "&").replace("&#39;", "'")
                    whats_new = re.sub(r"<[^>]+>", "", whats_new).strip()

                upd_matches = list(re.finditer(
                    r"\['([A-Z][a-z]+ \d+, \d{4})',\s*\[\d+,\s*\d+\]\]",
                    raw_str,
                ))
                if upd_matches:
                    last_updated = upd_matches[-1].group(1)

        if not developer_name:
            anchor = soup.select_one("a.hrTbp.R8zArc")
            if anchor:
                developer_name = anchor.get_text(strip=True)

        if not category:
            cat_anchor = soup.select_one("a[itemprop='genre']")
            if cat_anchor:
                category = cat_anchor.get_text(strip=True)

        if not rating:
            rs = self._extract_meta(soup, "rating") or self._extract_itemprop(soup, "ratingValue")
            if rs:
                try:
                    rating = round(float(rs), 2)
                except ValueError:
                    pass

        if rating_count is None:
            rcs = self._extract_itemprop(soup, "ratingCount")
            if rcs:
                try:
                    rating_count = int(rcs.replace(",", ""))
                except ValueError:
                    pass

        metadata = {
            "installs": installs,
            "content_rating": content_rating,
            "developer_url": developer_url,
            "image": icon_url,
            "file_size": file_size,
            "last_updated": last_updated,
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
            icon_url=icon_url,
            rating=rating,
            rating_count=rating_count,
            price=price_str,
            release_notes=whats_new,
            file_size=file_size,
            last_updated=last_updated,
            content_rating=content_rating,
            fetch_status=fetch_status,
            metadata=metadata,
            raw_payload={"html_length": len(html)},
            observed_at=observed_at,
        )

    async def _fetch_app_browser(self, *, url: str, region: str, observed_at: datetime) -> StoreFetchResult:
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.settings.ua_pool_list[0],
                    locale="en-US",
                )
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                html = await page.content()
                await browser.close()

            soup = BeautifulSoup(html, "html.parser")
            title = self._extract_meta(soup, "og:title")
            if not title or title.casefold() == "google play":
                return StoreFetchResult(
                    store=StoreEnum.GOOGLE_PLAY,
                    region=region.upper(),
                    is_visible=False,
                    url=url,
                    fetch_status="browser_fallback",
                    raw_payload={"html_length": len(html)},
                    observed_at=observed_at,
                )
            return self._parse_detail_html(soup=soup, html=html, url=url, region=region, observed_at=observed_at, fetch_status="browser_fallback")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Browser fallback failed for %s: %s", url, exc)
            return StoreFetchResult(
                store=StoreEnum.GOOGLE_PLAY,
                region=region.upper(),
                is_visible=False,
                url=url,
                fetch_status="error",
                metadata={"error": f"browser_fallback: {exc}"},
                raw_payload={"error": str(exc)},
                observed_at=observed_at,
            )
