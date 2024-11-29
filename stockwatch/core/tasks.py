import threading
import time
from .models import Stock
import yfinance as yf
from datetime import datetime
import logging
from decimal import Decimal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockPriceUpdater:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.initialized = False
            return cls._instance

    def __init__(self):
        if not self.initialized:
            self.stop_event = threading.Event()
            self.thread = None
            self.initialized = True

    def get_stock_info(self, symbol: str):
        """Fetch stock info from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if info:
                return {
                    'current_price': Decimal(str(info.get('regularMarketPrice', 0))),
                    'previous_close': Decimal(str(info.get('previousClose', 0))),
                    'market_cap': info.get('marketCap'),
                    'volume': info.get('volume'),
                    'day_high': Decimal(str(info.get('dayHigh', 0))),
                    'day_low': Decimal(str(info.get('dayLow', 0))),
                    'name': info.get('longName')
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {str(e)}")
            return None

    def update_prices(self):
        """Update prices for all stocks in database"""
        while not self.stop_event.is_set():
            try:
                stocks = Stock.objects.all()
                for stock in stocks:
                    logger.info(f"Fetching info for {stock.symbol}...")
                    info = self.get_stock_info(stock.symbol)

                    if info:
                        for key, value in info.items():
                            setattr(stock, key, value)
                        stock.last_updated = datetime.now()
                        stock.save()
                        logger.info(f"Updated {stock.symbol} price to ${stock.current_price}")
                    else:
                        logger.warning(f"Could not fetch info for {stock.symbol}")

                    time.sleep(2)  # Small delay between API calls

                time.sleep(60)  # Wait for 1 minute before next update cycle
            except Exception as e:
                logger.error(f"Error in update loop: {str(e)}")
                time.sleep(60)  # Wait before retrying if there's an error

    def start(self):
        """Start the price updater thread"""
        if self.thread is None or not self.thread.is_alive():
            logger.info("Starting stock price updater...")
            self.stop_event.clear()
            self.thread = threading.Thread(target=self.update_prices)
            self.thread.daemon = True
            self.thread.start()
            logger.info("Stock price updater started")
        else:
            logger.info("Stock price updater already running")

    def stop(self):
        """Stop the price updater thread"""
        logger.info("Stopping stock price updater...")
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None

# Create a singleton instance
price_updater = StockPriceUpdater()