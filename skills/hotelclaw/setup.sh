#!/bin/bash
set -e
echo "Installing hotelclaw dependencies..."
pip install playwright requests "mcp[cli]"
playwright install chromium
# serpapi is optional — only needed for Google Hotels source
pip install serpapi 2>/dev/null && echo "serpapi installed (Google Hotels enabled)" || echo "serpapi not installed — Google Hotels source will be skipped"
echo "hotelclaw ready."
