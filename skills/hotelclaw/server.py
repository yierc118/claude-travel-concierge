"""hotelclaw MCP server."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP  # type: ignore
from tracking import register_tracking_tools
from scrapers import search_all_sources

mcp = FastMCP("hotelclaw")
register_tracking_tools(mcp)


@mcp.tool()
def search_hotels_direct(city: str, check_in: str, check_out: str, guests: int = 1, results: int = 5) -> str:
    """Search accommodation without tracking. Returns formatted results."""
    from helpers import fmt_price
    options, warnings = search_all_sources(city, check_in, check_out, guests, results_per_source=results)
    if not options:
        return f"No results for {city} ({check_in} to {check_out})." + ("\n" + "\n".join(warnings) if warnings else "")
    lines = [f"Hotels in {city} ({check_in} → {check_out}):"]
    for opt in options:
        lines.append(f"• {opt['name']} [{opt['source']}] — {fmt_price(opt['price_per_night'])}/night — {opt['area']}")
    if warnings:
        lines.extend(warnings)
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
