"""
Chope automated booking script — Method C
Handles any Bangkok restaurant on Chope end-to-end.

Usage:
    python scripts/chope_book.py \
        --rid plu1909bkk \
        --slug plu-bangkok \
        --date 2026-03-30 \
        --time "1:45 pm" \
        --adults 3 \
        [--children 0] \
        [--headless]

Stops at confirmation page and prints the Chope Booking Confirmation ID.
Credentials loaded from .env: CHOPE_USERNAME, CHOPE_PASSWORD
"""
import argparse
import os
import sys
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE_DIR = "/Users/yiercao/Vibe_Coding/AgenticWorflow_Travel Concierge"
USERNAME = os.getenv("CHOPE_USERNAME")
PASSWORD = os.getenv("CHOPE_PASSWORD")


def book(rid: str, slug: str, date: str, time: str, adults: int,
         children: int = 0, headless: bool = True) -> dict:
    """
    Complete a Chope booking end-to-end.

    Args:
        rid:      Chope restaurant ID (e.g. "plu1909bkk")
        slug:     URL slug for the restaurant page (e.g. "plu-bangkok")
        date:     Date in YYYY-MM-DD format (e.g. "2026-03-30")
        time:     Time string as shown on Chope (e.g. "1:45 pm")
        adults:   Number of adults
        children: Number of children (default 0)
        headless: Run browser headlessly (default True)

    Returns:
        dict with keys: confirmation_id, restaurant, date, time, adults, url
    """
    # Build the vc-calendar day class (e.g. "id-2026-03-30")
    vc_day_class = f".vc-day.id-{date}"

    # Build pre-filled restaurant page URL
    time_encoded = quote(time)
    restaurant_url = (
        f"https://www.chope.co/bangkok-restaurants/restaurant/{slug}"
        f"?children={children}&adults={adults}&date={date}&time={time_encoded}"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 900})

        new_pages = []
        context.on("page", lambda pg: new_pages.append(pg))
        page = context.new_page()

        # Step 1: Login
        page.goto("https://www.chope.co/bangkok-restaurants/user", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=20000)
        page.fill('input[name="email"]', USERNAME)
        page.fill('input[name="password"]', PASSWORD)
        page.press('input[name="password"]', "Enter")
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(2000)

        # Step 2: Open restaurant page (pre-filled)
        page.goto(restaurant_url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(2000)

        # Step 3: Click Book Now → opens booking.chope.co popup
        page.evaluate("() => document.querySelector('#btn_sub')?.click()")
        page.wait_for_timeout(4000)

        wp = next((p for p in new_pages if "booking.chope.co" in p.url), None)
        if not wp:
            raise RuntimeError("Booking widget did not open as a new tab")

        wp.wait_for_load_state("networkidle", timeout=20000)
        wp.wait_for_timeout(2000)

        # Step 4: Select date in widget calendar
        wp.evaluate("""() => {
            const btns = document.querySelectorAll(".date_btn button, .date_buttons button");
            for (const b of btns) {
                if (b.textContent.trim() === "Select Date") { b.click(); return; }
            }
        }""")
        wp.wait_for_timeout(1500)

        clicked = wp.evaluate(f"""() => {{
            const day = document.querySelector("{vc_day_class}");
            if (!day) return "not found: {vc_day_class}";
            const content = day.querySelector(".vc-focusable");
            if (content) {{ content.click(); return "ok"; }}
            day.click(); return "ok (parent)";
        }}""")
        if "not found" in str(clicked):
            raise RuntimeError(f"Calendar day not found: {vc_day_class}")
        wp.wait_for_timeout(1500)

        # Step 5: Select time slot
        time_clicked = wp.evaluate(f"""() => {{
            const items = document.querySelectorAll(".time_item");
            for (const s of items) {{
                if (s.textContent.trim() === "{time}") {{ s.click(); return "ok"; }}
            }}
            return "not found: {time}";
        }}""")
        if "not found" in str(time_clicked):
            raise RuntimeError(f"Time slot not available: {time}")
        wp.wait_for_timeout(800)

        # Step 6: Click Next → Contact Details
        wp.evaluate("""() => {
            for (const b of document.querySelectorAll("button")) {
                if (b.textContent.trim() === "Next") { b.click(); return; }
            }
        }""")
        wp.wait_for_load_state("networkidle", timeout=15000)
        wp.wait_for_timeout(2000)

        # Step 7: Check T&C and click Book table
        wp.evaluate("""() => {
            const cb = document.querySelector(".nav-confirmation-row input[type='checkbox']");
            if (cb && !cb.checked) cb.click();
        }""")
        wp.wait_for_timeout(500)

        wp.evaluate("""() => {
            for (const b of document.querySelectorAll("button")) {
                if (b.textContent.trim().toLowerCase() === "book table" && !b.disabled) {
                    b.click(); return;
                }
            }
        }""")
        wp.wait_for_load_state("networkidle", timeout=20000)
        wp.wait_for_timeout(5000)

        # Step 8: Extract confirmation ID from URL
        final_url = wp.url
        if "booking_confirmation" not in final_url:
            # Save screenshot for debugging
            wp.screenshot(path="/tmp/chope_book_error.png", full_page=True)
            raise RuntimeError(f"Booking failed. Final URL: {final_url}")

        confirmation_id = final_url.split("/booking_confirmation/")[1].split("?")[0]

        # Save confirmation screenshot
        screenshot_path = f"/tmp/chope_{confirmation_id}.png"
        wp.screenshot(path=screenshot_path, full_page=False)

        context.close()

        return {
            "confirmation_id": confirmation_id,
            "restaurant": slug,
            "rid": rid,
            "date": date,
            "time": time,
            "adults": adults,
            "children": children,
            "url": final_url,
            "screenshot": screenshot_path,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chope automated booking")
    parser.add_argument("--rid", required=True, help="Restaurant ID (e.g. plu1909bkk)")
    parser.add_argument("--slug", required=True, help="URL slug (e.g. plu-bangkok)")
    parser.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    parser.add_argument("--time", required=True, help='Time (e.g. "1:45 pm")')
    parser.add_argument("--adults", type=int, default=2)
    parser.add_argument("--children", type=int, default=0)
    parser.add_argument("--headless", action="store_true", default=False)
    args = parser.parse_args()

    result = book(
        rid=args.rid,
        slug=args.slug,
        date=args.date,
        time=args.time,
        adults=args.adults,
        children=args.children,
        headless=args.headless,
    )

    print(f"\nBooking confirmed!")
    print(f"  Confirmation ID : {result['confirmation_id']}")
    print(f"  Restaurant      : {result['restaurant']}")
    print(f"  Date/Time       : {result['date']} {result['time']}")
    print(f"  Party           : {result['adults']} adults, {result['children']} children")
    print(f"  Screenshot      : {result['screenshot']}")
