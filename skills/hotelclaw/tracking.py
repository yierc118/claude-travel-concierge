"""hotelclaw tracking tools — track, check, list, and remove accommodation."""
from datetime import datetime, timezone
from helpers import fmt_price, load_tracked, save_tracked
from scrapers import search_all_sources, search_booking_com


def register_tracking_tools(mcp):
    """Register all tracking tools on the given MCP server instance."""

    @mcp.tool()
    def search_hotels(city: str, check_in: str, check_out: str, guests: int = 1, results: int = 5) -> str:
        """Search for accommodation options across all sources.

        Args:
            city: City name (e.g. "Tokyo", "Paris")
            check_in: Check-in date (YYYY-MM-DD)
            check_out: Check-out date (YYYY-MM-DD)
            guests: Number of guests (default 1)
            results: Max results per source (default 5)
        """
        options, warnings = search_all_sources(city, check_in, check_out, guests, results_per_source=results)

        if not options:
            msg = f"No accommodation found for {city} ({check_in} to {check_out})."
            if warnings:
                msg += "\n" + "\n".join(warnings)
            return msg

        lines = [f"Accommodation options for {city} ({check_in} → {check_out}, {guests} guest(s)):\n"]
        for opt in options:
            price_str = fmt_price(opt["price_per_night"])
            lines.append(f"• {opt['name']} [{opt['source']}]")
            lines.append(f"  {opt['area']} | {price_str}/night | {opt.get('url', 'no url')}")

        if warnings:
            lines.append("\n" + "\n".join(warnings))

        lines.append(f"\n{len(options)} option(s) found across all sources.")
        return "\n".join(lines)

    @mcp.tool()
    def track_property(name: str, city: str, check_in: str, check_out: str, url: str = "", target_price: float | None = None) -> str:
        """Add a property to price tracking.

        Args:
            name: Property name (e.g. "Shinjuku Granbell Hotel")
            city: City name
            check_in: Check-in date (YYYY-MM-DD)
            check_out: Check-out date (YYYY-MM-DD)
            url: Direct booking URL (optional but recommended for price checks)
            target_price: Alert when price drops below this amount (USD)
        """
        tracked = load_tracked()
        property_id = f"{city.lower().replace(' ', '-')}-{name.lower().replace(' ', '-')}-{check_in}"

        if any(t["id"] == property_id for t in tracked):
            return f"Already tracking: {name} in {city} ({check_in})"

        now = datetime.now(timezone.utc).isoformat()
        nights = (
            (datetime.fromisoformat(check_out) - datetime.fromisoformat(check_in)).days
        )

        # Try to get initial price
        initial_price = None
        try:
            results, _ = search_all_sources(city, check_in, check_out, guests=1, results_per_source=3)
            match = next((r for r in results if name.lower() in r["name"].lower()), None)
            if match:
                initial_price = match["price_per_night"]
        except Exception:
            pass

        entry = {
            "id": property_id,
            "name": name,
            "city": city,
            "check_in": check_in,
            "check_out": check_out,
            "nights": nights,
            "url": url,
            "target_price": target_price,
            "currency": "USD",
            "added_at": now,
            "price_history": [
                {"timestamp": now, "price_per_night": initial_price}
            ],
        }

        tracked.append(entry)
        save_tracked(tracked)

        price_msg = fmt_price(initial_price) + "/night" if initial_price else "price unknown"
        return f"Now tracking: {name} in {city} ({check_in} → {check_out}, {nights} nights) — {price_msg}"

    @mcp.tool()
    def check_prices(threshold: float = 15.0) -> str:
        """Check all tracked properties for price changes.

        Args:
            threshold: Percentage drop to trigger alert (default 15)
        """
        tracked = load_tracked()
        if not tracked:
            return "No properties being tracked. Use track_property to add one."

        now = datetime.now(timezone.utc).isoformat()
        output = []
        alerts = []

        for entry in tracked:
            label = f"{entry['name']} ({entry['city']}, {entry['check_in']})"
            currency = entry.get("currency", "USD")

            try:
                results, warnings = search_all_sources(
                    entry["city"], entry["check_in"], entry["check_out"], results_per_source=3
                )
                match = next((r for r in results if entry["name"].lower() in r["name"].lower()), None)
                price = match["price_per_night"] if match else None
            except Exception as e:
                output.append(f"{label}: Error — {e}")
                continue

            if price is None:
                output.append(f"{label}: No price found")
                continue

            entry["price_history"].append({"timestamp": now, "price_per_night": price})

            prev_prices = [p["price_per_night"] for p in entry["price_history"][:-1] if p["price_per_night"]]
            if prev_prices:
                last_price = prev_prices[-1]
                change = price - last_price
                pct = (change / last_price) * 100

                direction = "DOWN" if change < 0 else "up"
                output.append(f"{label}: {fmt_price(price, currency)}/night ({direction} {abs(pct):.1f}%)")

                if change < 0 and abs(pct) >= threshold:
                    alerts.append(f"PRICE DROP: {label} — now {fmt_price(price, currency)}/night (was {fmt_price(last_price, currency)}, down {abs(pct):.1f}%)")
            else:
                output.append(f"{label}: {fmt_price(price, currency)}/night (first check)")

            if entry.get("target_price") and price <= entry["target_price"]:
                alerts.append(f"TARGET REACHED: {label} — {fmt_price(price, currency)}/night (target: {fmt_price(entry['target_price'], currency)})")

        save_tracked(tracked)

        if alerts:
            output.append("\nALERTS:")
            output.extend(f"  {a}" for a in alerts)

        return "\n".join(output)

    @mcp.tool()
    def list_tracked() -> str:
        """List all tracked properties with price history summary."""
        tracked = load_tracked()
        if not tracked:
            return "No properties being tracked. Use track_property to add one."

        output = []
        for entry in tracked:
            currency = entry.get("currency", "USD")
            line = f"{entry['name']} | {entry['city']} | {entry['check_in']} → {entry['check_out']} ({entry['nights']} nights)"
            if entry.get("target_price"):
                line += f" | Target: {fmt_price(entry['target_price'], currency)}/night"

            history = entry.get("price_history", [])
            if history:
                first = next((p["price_per_night"] for p in history if p["price_per_night"]), None)
                last = history[-1].get("price_per_night")
                if first and last:
                    change = last - first
                    pct = (change / first) * 100
                    direction = "down" if change < 0 else "up"
                    line += f"\n  Current: {fmt_price(last, currency)}/night | Original: {fmt_price(first, currency)}/night | {direction} {abs(pct):.1f}%"
                elif last:
                    line += f"\n  Current: {fmt_price(last, currency)}/night"
                line += f"\n  Checks: {len(history)} | Since: {entry.get('added_at', '?')[:10]}"
            else:
                line += "\n  No price data yet"

            output.append(line)

        output.append(f"\n{len(tracked)} property(ies) tracked.")
        return "\n".join(output)

    @mcp.tool()
    def remove_tracked(property_id: str) -> str:
        """Remove a property from the tracking list.

        Args:
            property_id: The property ID to remove. Use list_tracked to see IDs.
        """
        tracked = load_tracked()
        before = len(tracked)
        tracked = [t for t in tracked if t["id"] != property_id]

        if len(tracked) == before:
            return f"Property {property_id} not found. Use list_tracked to see tracked properties."

        save_tracked(tracked)
        return f"Removed {property_id}. {len(tracked)} property(ies) remaining."
