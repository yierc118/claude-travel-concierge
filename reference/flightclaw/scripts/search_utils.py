"""Shared helpers for FlightClaw - formatting and price parsing."""

import re

CURRENCY_SYMBOLS = {
    "USD": "$", "GBP": "\u00a3", "EUR": "\u20ac", "THB": "\u0e3f",
    "JPY": "\u00a5", "CNY": "\u00a5", "KRW": "\u20a9", "INR": "\u20b9",
    "AUD": "A$", "CAD": "C$", "SGD": "S$", "HKD": "HK$", "NZD": "NZ$",
    "TWD": "NT$", "MYR": "RM", "PHP": "\u20b1", "IDR": "Rp", "VND": "\u20ab",
    "BRL": "R$", "MXN": "MX$", "CHF": "CHF", "SEK": "kr", "NOK": "kr",
    "DKK": "kr", "PLN": "z\u0142", "CZK": "K\u010d", "HUF": "Ft",
    "TRY": "\u20ba", "ZAR": "R", "AED": "AED", "SAR": "SAR", "QAR": "QAR",
    "KWD": "KD", "BHD": "BD", "OMR": "OMR", "ILS": "\u20aa",
}


def fmt_price(price, code=None):
    """Format a price. Accepts a pre-formatted string or a float + currency code."""
    if isinstance(price, str):
        return price
    if code:
        symbol = CURRENCY_SYMBOLS.get(code, code + " ")
        return f"{symbol}{price:,.0f}"
    return str(price)


def parse_price_str(price_str):
    """Extract numeric value from a formatted price string like 'HK$3,456' or '$450'."""
    if not price_str:
        return None
    match = re.search(r"[\d,]+(?:\.\d+)?", price_str)
    if match:
        return float(match.group().replace(",", ""))
    return None
