from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import yfinance as yf

from .validator import validate_ohlcv_dataframe

logger = logging.getLogger(__name__)


def download_stock_history(
    ticker: str,
    period: str = "5y",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """
    Downloads daily historical OHLCV data for a single stock ticker via yfinance.
    Applies data validation rules.

    Returns:
    - Cleaned, validated DataFrame with trade_date formatted as 'YYYY-MM-DD'.
    - List of validation warnings or download error messages.
    """
    errors: List[str] = []
    try:
        yf_ticker = yf.Ticker(ticker)
        if start_date and end_date:
            df = yf_ticker.history(start=start_date, end=end_date, auto_adjust=False)
        elif start_date:
            df = yf_ticker.history(start=start_date, auto_adjust=False)
        else:
            df = yf_ticker.history(period=period, auto_adjust=False)

        if df is None or df.empty:
            errors.append(f"No historical data returned for ticker {ticker}.")
            return None, errors

        # Reset index to convert DatetimeIndex into a 'trade_date' column
        df = df.reset_index()
        date_col = "Date" if "Date" in df.columns else df.columns[0]
        df["trade_date"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")

        # Map Adj Close if available
        if "Adj Close" in df.columns:
            df["adjusted_close"] = df["Adj Close"]
        elif "Close" in df.columns:
            df["adjusted_close"] = df["Close"]

        # Validate DataFrame
        df_valid, val_errors = validate_ohlcv_dataframe(df)
        errors.extend(val_errors)

        if df_valid.empty:
            errors.append(f"All data rows failed validation for ticker {ticker}.")
            return None, errors

        return df_valid, errors

    except Exception as e:
        err_msg = f"Exception downloading data for ticker {ticker}: {e}"
        logger.error(err_msg)
        errors.append(err_msg)
        return None, errors


def download_universe_historical_data(
    constituents: List[Dict[str, Any]],
    period: str = "5y",
    max_workers: int = 5,
) -> Dict[str, Dict[str, Any]]:
    """
    Downloads historical OHLCV data concurrently for a list of constituent stocks.

    Returns a dict keyed by symbol:
    {
       "COALINDIA": {
          "stock": constituent_dict,
          "df": DataFrame or None,
          "errors": [list of warnings/errors],
          "status": "SUCCESS" | "FAILURE"
       }
    }
    """
    results: Dict[str, Dict[str, Any]] = {}

    def _fetch_single(constituent: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[pd.DataFrame], List[str]]:
        ticker = constituent["ticker"]
        df, errors = download_stock_history(ticker, period=period)
        return constituent, df, errors

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_stock = {
            executor.submit(_fetch_single, stock): stock
            for stock in constituents
        }

        for future in as_completed(future_to_stock):
            stock = future_to_stock[future]
            symbol = stock["symbol"]
            try:
                const_res, df, errors = future.result()
                status = "SUCCESS" if df is not None and not df.empty else "FAILURE"
                results[symbol] = {
                    "stock": const_res,
                    "df": df,
                    "errors": errors,
                    "status": status,
                }
            except Exception as exc:
                logger.error(f"Error processing stock {symbol}: {exc}")
                results[symbol] = {
                    "stock": stock,
                    "df": None,
                    "errors": [str(exc)],
                    "status": "FAILURE",
                }

    return results
