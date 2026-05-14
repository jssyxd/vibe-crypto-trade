"""Test OKX data source for crypto backtesting."""
import json
from datetime import datetime, timedelta

def test_okx_btc_data():
    """Test that we can fetch BTC/USDT data from OKX."""
    print("Testing OKX data source...")

    # Import from installed backtest package
    try:
        from backtest.loaders.okx import DataLoader
        print("OKXLoader imported successfully")
    except ImportError as e:
        print(f"Failed to import DataLoader: {e}")
        return False

    # Initialize loader
    try:
        loader = DataLoader()
        print("DataLoader initialized")
    except Exception as e:
        print(f"Failed to initialize DataLoader: {e}")
        return False

    # Fetch recent BTC/USDT data
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        print(f"Loading BTC/USDT data from {start_date.date()} to {end_date.date()}...")

        # Use the correct fetch method signature
        result = loader.fetch(
            codes=["BTC-USDT"],
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="1D"
        )

        if "BTC-USDT" not in result:
            print("Failed to load BTC-USDT data")
            return False

        data = result["BTC-USDT"]

        print(f"Loaded {len(data)} bars of BTC/USDT data")
        print(f"  Date range: {data.index[0]} to {data.index[-1]}")
        print(f"  Latest close: {data['close'].iloc[-1]:.2f}")

        return True

    except Exception as e:
        print(f"Failed to load data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_okx_btc_data()
    exit(0 if success else 1)