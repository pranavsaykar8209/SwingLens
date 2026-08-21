from unittest.mock import patch, MagicMock
import pandas as pd
import pytest
from backend.market_data.universe import fetch_nifty_next_50_constituents, FALLBACK_NIFTY_NEXT_50
from backend.market_data.downloader import download_stock_history


def test_fetch_nifty_next_50_constituents():
    constituents = fetch_nifty_next_50_constituents()
    assert isinstance(constituents, list)
    assert len(constituents) >= 40  # Should be 50 or close

    first = constituents[0]
    assert "symbol" in first
    assert "ticker" in first
    assert first["ticker"].endswith(".NS")
    assert "company_name" in first
    assert "exchange" in first
    assert "series" in first


@patch("yfinance.Ticker")
def test_download_stock_history_mock(mock_yf_ticker):
    # Setup mock dataframe returned by yfinance
    mock_df = pd.DataFrame(
        {
            "Open": [100.0, 102.0],
            "High": [105.0, 107.0],
            "Low": [98.0, 101.0],
            "Close": [104.0, 106.0],
            "Adj Close": [104.0, 106.0],
            "Volume": [10000, 12000],
        },
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
    )

    instance = MagicMock()
    instance.history.return_value = mock_df
    mock_yf_ticker.return_value = instance

    df_valid, errors = download_stock_history("COALINDIA.NS", period="5y")

    assert df_valid is not None
    assert not df_valid.empty
    assert len(df_valid) == 2
    assert "trade_date" in df_valid.columns
    assert df_valid.iloc[0]["trade_date"] == "2024-01-01"
