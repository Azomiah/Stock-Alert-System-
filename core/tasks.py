# tasks.py
import threading
import time
from .stock_monitor import StockMonitor
import logging

logger = logging.getLogger(__name__)

class StockPriceUpdater:
    def __init__(self):
        self.stop_event = threading.Event()
        self.monitor = StockMonitor()

    def update_prices(self):
        while not self.stop_event.is_set():
            try:
                self.monitor.update_all_stocks()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in update loop: {str(e)}")
                time.sleep(60)

    def start(self):
        logger.info("Starting stock price updater...")
        thread = threading.Thread(target=self.update_prices)
        thread.daemon = True
        thread.start()

    def stop(self):
        logger.info("Stopping stock price updater...")
        self.stop_event.set()

price_updater = StockPriceUpdater()