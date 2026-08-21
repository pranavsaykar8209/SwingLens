import io
import logging
from typing import List, Dict, Any
import httpx

logger = logging.getLogger(__name__)

# Official Nifty Next 50 Index constituent CSV URLs
NIFTY_NEXT_50_URLS = [
    "https://niftyindices.com/IndexConstituent/ind_niftynext50list.csv",
    "https://archives.nseindia.com/content/indices/ind_niftynext50list.csv",
]

# Complete fallback list of current Nifty Next 50 constituents (50 stocks)
FALLBACK_NIFTY_NEXT_50: List[Dict[str, str]] = [
    {"symbol": "ABB", "company_name": "ABB India Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "ADANIENSOL", "company_name": "Adani Energy Solutions Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "ADANIGREEN", "company_name": "Adani Green Energy Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "ADANIPOWER", "company_name": "Adani Power Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "ATGL", "company_name": "Adani Total Gas Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "AMBUJACEM", "company_name": "Ambuja Cements Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "BAJAJHLDNG", "company_name": "Bajaj Holdings & Investment Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "BANKBARODA", "company_name": "Bank of Baroda", "exchange": "NSE", "series": "EQ"},
    {"symbol": "BERGEPAINT", "company_name": "Berger Paints India Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "BHARATFORG", "company_name": "Bharat Forge Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "BOSCHLTD", "company_name": "Bosch Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "CANBK", "company_name": "Canara Bank", "exchange": "NSE", "series": "EQ"},
    {"symbol": "CHOLAFIN", "company_name": "Cholamandalam Investment and Finance Company Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "COLPAL", "company_name": "Colgate-Palmolive (India) Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "DLF", "company_name": "DLF Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "DMART", "company_name": "Avenue Supermarts Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "GAIL", "company_name": "GAIL (India) Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "GODREJPROP", "company_name": "Godrej Properties Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "HAVELLS", "company_name": "Havells India Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "HAL", "company_name": "Hindustan Aeronautics Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "ICICIGI", "company_name": "ICICI Lombard General Insurance Company Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "ICICIPRULI", "company_name": "ICICI Prudential Life Insurance Company Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "IOC", "company_name": "Indian Oil Corporation Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "IRCTC", "company_name": "Indian Railway Catering And Tourism Corporation Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "IRFC", "company_name": "Indian Railway Finance Corporation Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "INDIGO", "company_name": "InterGlobe Aviation Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "JINDALSTEL", "company_name": "Jindal Steel & Power Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "JIOFIN", "company_name": "Jio Financial Services Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "JSWENERGY", "company_name": "JSW Energy Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "LTIM", "company_name": "LTIMindtree Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "LODHA", "company_name": "Macrotech Developers Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "MAXHEALTH", "company_name": "Max Healthcare Institute Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "NAUKRI", "company_name": "Info Edge (India) Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "NHPC", "company_name": "NHPC Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "PFC", "company_name": "Power Finance Corporation Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "PIDILITIND", "company_name": "Pidilite Industries Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "PNB", "company_name": "Punjab National Bank", "exchange": "NSE", "series": "EQ"},
    {"symbol": "RECLTD", "company_name": "REC Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "SBICARD", "company_name": "SBI Cards and Payment Services Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "SRF", "company_name": "SRF Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "MOTHERSON", "company_name": "Samvardhana Motherson International Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "SHREECEM", "company_name": "Shree Cement Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "SIEMENS", "company_name": "Siemens Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "SOLARINDS", "company_name": "Solar Industries India Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "TATAELXSI", "company_name": "Tata Elxsi Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "TATAMTRDVR", "company_name": "Tata Motors Ltd. DVR", "exchange": "NSE", "series": "EQ"},
    {"symbol": "TATPWR", "company_name": "Tata Power Company Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "TORNTPHARM", "company_name": "Torrent Pharmaceuticals Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "TRENT", "company_name": "Trent Ltd.", "exchange": "NSE", "series": "EQ"},
    {"symbol": "ZOMATO", "company_name": "Eternal Limited (Zomato)", "exchange": "NSE", "series": "EQ"},
]


def fetch_nifty_next_50_constituents() -> List[Dict[str, Any]]:
    """
    Fetches Nifty Next 50 index constituents.
    First attempts fetching from official online NSE CSV endpoints.
    If online fetch fails or returns invalid data, seamlessly falls back
    to the internal curated Nifty Next 50 constituent list.

    Returns a list of dicts formatted with:
    `symbol`, `ticker` (with `.NS`), `company_name`, `exchange`, `series`.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
    }

    fetched_constituents = []
    for url in NIFTY_NEXT_50_URLS:
        try:
            response = httpx.get(url, headers=headers, timeout=5.0, follow_redirects=True)
            if response.status_code == 200 and "Company Name" in response.text:
                lines = response.text.splitlines()
                # Parse CSV content
                import csv

                reader = csv.DictReader(lines)
                for row in reader:
                    symbol = row.get("Symbol") or row.get("symbol")
                    company_name = row.get("Company Name") or row.get("company_name")
                    series = row.get("Series") or row.get("series") or "EQ"
                    if symbol:
                        symbol_clean = symbol.strip().upper()
                        fetched_constituents.append({
                            "symbol": symbol_clean,
                            "ticker": f"{symbol_clean}.NS",
                            "company_name": (company_name or symbol_clean).strip(),
                            "exchange": "NSE",
                            "series": series.strip(),
                        })
                if len(fetched_constituents) >= 40:
                    logger.info(f"Successfully fetched {len(fetched_constituents)} constituents from {url}")
                    return fetched_constituents
        except Exception as e:
            logger.warning(f"Failed to fetch Nifty Next 50 list from {url}: {e}")

    # Fallback if online fetch fails
    logger.info("Using curated fallback Nifty Next 50 constituent universe.")
    return [
        {
            "symbol": item["symbol"],
            "ticker": f"{item['symbol']}.NS",
            "company_name": item["company_name"],
            "exchange": item["exchange"],
            "series": item["series"],
        }
        for item in FALLBACK_NIFTY_NEXT_50
    ]
