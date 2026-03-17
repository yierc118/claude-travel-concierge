"""
hotelclaw scrapers — three independent accommodation data sources.

Each scraper returns: list of {name, type, area, price_per_night, currency, url, source}
Each fails independently — caller handles empty results and continues.
"""
import os
import time
import random
import logging
from typing import Any

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def _human_delay():
    """Random 2–5s delay to avoid rate limiting."""
    time.sleep(random.uniform(2, 5))


def search_google_hotels(city: str, check_in: str, check_out: str, guests: int = 1, results: int = 5) -> list[dict[str, Any]]:
    """
    Search Google Hotels via SerpAPI (requires SERPAPI_KEY env var).
    Returns empty list and logs warning if key missing or request fails.
    """
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        logger.warning("SERPAPI_KEY not set — skipping Google Hotels source")
        return []

    try:
        from serpapi import GoogleSearch  # type: ignore
        params = {
            "engine": "google_hotels",
            "q": f"hotels in {city}",
            "check_in_date": check_in,
            "check_out_date": check_out,
            "adults": guests,
            "currency": "USD",
            "api_key": api_key,
        }
        search = GoogleSearch(params)
        raw = search.get_dict()
        hotels = raw.get("properties", [])[:results]
        out = []
        for h in hotels:
            price = h.get("rate_per_night", {}).get("lowest")
            if price:
                try:
                    price = float(str(price).replace("$", "").replace(",", ""))
                except ValueError:
                    price = None
            out.append({
                "name": h.get("name", "Unknown"),
                "type": "hotel",
                "area": h.get("neighborhood", city),
                "price_per_night": price,
                "currency": "USD",
                "url": h.get("link", ""),
                "source": "google_hotels",
            })
        return out
    except Exception as e:
        logger.warning(f"Google Hotels scrape failed: {e}")
        return []


def search_booking_com(city: str, check_in: str, check_out: str, guests: int = 1, results: int = 5) -> list[dict[str, Any]]:
    """
    Search Booking.com via Playwright headless browser.
    Returns empty list and logs warning on failure.
    """
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
        check_in_fmt = check_in.replace("-", "")  # YYYYMMDD
        check_out_fmt = check_out.replace("-", "")
        url = (
            f"https://www.booking.com/searchresults.html"
            f"?ss={city}&checkin={check_in_fmt}&checkout={check_out_fmt}"
            f"&group_adults={guests}&no_rooms=1&selected_currency=USD"
        )
        out = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="en-US",
            )
            page = context.new_page()
            _human_delay()
            page.goto(url, timeout=30000)
            _human_delay()
            page.wait_for_load_state("networkidle", timeout=15000)

            cards = page.query_selector_all('[data-testid="property-card"]')[:results]
            for card in cards:
                try:
                    name_el = card.query_selector('[data-testid="title"]')
                    price_el = card.query_selector('[data-testid="price-and-discounted-price"]')
                    area_el = card.query_selector('[data-testid="address"]')
                    link_el = card.query_selector('a[data-testid="title-link"]')

                    name = name_el.inner_text().strip() if name_el else "Unknown"
                    area = area_el.inner_text().strip() if area_el else city
                    link = link_el.get_attribute("href") if link_el else ""

                    price = None
                    if price_el:
                        raw = price_el.inner_text().strip()
                        digits = "".join(c for c in raw if c.isdigit() or c == ".")
                        try:
                            price = float(digits) if digits else None
                        except ValueError:
                            price = None

                    out.append({
                        "name": name,
                        "type": "hotel",
                        "area": area,
                        "price_per_night": price,
                        "currency": "USD",
                        "url": link,
                        "source": "booking_com",
                    })
                except Exception as card_err:
                    logger.warning(f"Booking.com card parse error: {card_err}")
                    continue

            browser.close()
        return out
    except Exception as e:
        logger.warning(f"Booking.com scrape failed: {e}")
        return []


def search_airbnb(city: str, check_in: str, check_out: str, guests: int = 1, results: int = 5) -> list[dict[str, Any]]:
    """
    Search Airbnb via Playwright headless browser.
    Returns empty list and logs warning on failure.
    """
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
        url = (
            f"https://www.airbnb.com/s/{city}/homes"
            f"?checkin={check_in}&checkout={check_out}&adults={guests}"
        )
        out = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="en-US",
            )
            page = context.new_page()
            _human_delay()
            page.goto(url, timeout=30000)
            _human_delay()
            page.wait_for_load_state("networkidle", timeout=15000)

            cards = page.query_selector_all('[itemprop="itemListElement"]')[:results]
            for card in cards:
                try:
                    name_el = card.query_selector('[id^="title_"]')
                    price_el = card.query_selector('._tyxjp1')  # price span
                    link_el = card.query_selector('a[href^="/rooms"]')

                    name = name_el.inner_text().strip() if name_el else "Airbnb listing"
                    link = "https://www.airbnb.com" + link_el.get_attribute("href") if link_el else ""

                    price = None
                    if price_el:
                        raw = price_el.inner_text().strip()
                        digits = "".join(c for c in raw if c.isdigit() or c == ".")
                        try:
                            price = float(digits) if digits else None
                        except ValueError:
                            price = None

                    out.append({
                        "name": name,
                        "type": "airbnb",
                        "area": city,
                        "price_per_night": price,
                        "currency": "USD",
                        "url": link,
                        "source": "airbnb",
                    })
                except Exception as card_err:
                    logger.warning(f"Airbnb card parse error: {card_err}")
                    continue

            browser.close()
        return out
    except Exception as e:
        logger.warning(f"Airbnb scrape failed: {e}")
        return []


def search_all_sources(city: str, check_in: str, check_out: str, guests: int = 1, results_per_source: int = 3) -> tuple[list[dict], list[str]]:
    """
    Search all three sources. Returns (results, warnings).
    Each source fails independently — partial results are returned with warnings.
    """
    warnings = []
    all_results = []

    google = search_google_hotels(city, check_in, check_out, guests, results_per_source)
    if not google:
        warnings.append("⚠️ Google Hotels: no results (check SERPAPI_KEY)")
    all_results.extend(google)

    booking = search_booking_com(city, check_in, check_out, guests, results_per_source)
    if not booking:
        warnings.append("⚠️ Booking.com: no results (may be blocked or slow)")
    all_results.extend(booking)

    airbnb = search_airbnb(city, check_in, check_out, guests, results_per_source)
    if not airbnb:
        warnings.append("⚠️ Airbnb: no results (may be blocked or slow)")
    all_results.extend(airbnb)

    return all_results, warnings
