from datetime import datetime
from django.core.mail import send_mail
from django.conf import settings
import logging
from decimal import Decimal
import yfinance as yf
import time
import json

logger = logging.getLogger(__name__)


class StockMonitor:
    def get_stock_info(self, symbol):
        """
        Fetch comprehensive stock information using Yahoo Finance
        """
        try:
            logger.info(f"Fetching stock info for {symbol}")
            ticker = yf.Ticker(symbol)

            # Get fast info first
            logger.info("Attempting to get fast info")
            fast_info = ticker.fast_info
            price = getattr(fast_info, 'last_price', None)
            logger.info(f"Fast info price: {price}")

            # Get regular info
            logger.info("Attempting to get regular info")
            info = ticker.info
            logger.info(f"Regular info received: {json.dumps(dict(info), default=str)}")

            if not info:
                logger.warning(f"No data returned for {symbol}")
                return None

            # Try different price fields
            market_price = (
                    price or
                    info.get('regularMarketPrice') or
                    info.get('currentPrice') or
                    info.get('price')
            )

            logger.info(f"Selected market price: {market_price}")

            if not market_price:
                logger.warning(f"No price data available for {symbol}")
                return None

            stock_info = {
                'current_price': Decimal(str(market_price)),
                'previous_close': Decimal(str(info.get('previousClose', market_price))),
                'market_cap': info.get('marketCap'),
                'volume': info.get('volume'),
                'day_high': Decimal(str(info.get('dayHigh', market_price))),
                'day_low': Decimal(str(info.get('dayLow', market_price))),
                'name': info.get('longName', symbol)
            }

            logger.info(f"Final processed info for {symbol}: {json.dumps(stock_info, default=str)}")
            return stock_info

        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {str(e)}", exc_info=True)
            return None

    def send_alert(self, stock, target, current_price):
        """
        Send email alert for triggered price target
        """
        try:
            direction_text = {
                'above': 'risen above',
                'below': 'fallen below',
                'exact': 'reached'
            }

            subject = f"🚨 StockWatch Alert: {stock.symbol}"
            message = (
                f"Stock Alert for {stock.symbol} ({stock.name})\n\n"
                f"The stock price has {direction_text[target.direction]} "
                f"your target of ${target.price}.\n\n"
                f"Current Price: ${current_price}\n"
                f"Previous Close: ${stock.previous_close}\n"
                f"Day Range: ${stock.day_low} - ${stock.day_high}\n"
                f"Time: {datetime.now().strftime('%I:%M %p, %b %d')}\n\n"
                f"View more details at: {settings.SITE_URL}/dashboard/"
            )

            logger.info(f"Sending alert email for {stock.symbol}")
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [settings.NOTIFICATION_EMAIL],
                fail_silently=False,
            )

            target.last_triggered = datetime.now()
            target.save()

            logger.info(f"Alert sent for {stock.symbol} - Target: {target.direction} ${target.price}")

        except Exception as e:
            logger.error(f"Error sending alert for {stock.symbol}: {str(e)}", exc_info=True)

    def check_price_alerts(self, stock):
        """
        Check if any price targets have been triggered for a stock
        """
        try:
            logger.info(f"Checking price alerts for {stock.symbol}")
            info = self.get_stock_info(stock.symbol)

            if not info:
                logger.warning(f"No info available for {stock.symbol}, skipping alerts")
                return

            logger.info(f"Updating {stock.symbol} with new data: {json.dumps(info, default=str)}")

            # Update stock information
            for key, value in info.items():
                setattr(stock, key, value)
            stock.last_updated = datetime.now()
            stock.save()

            current_price = info['current_price']
            logger.info(f"Current price for {stock.symbol}: ${current_price}")

            # Check all active price targets
            active_targets = stock.pricetarget_set.filter(is_active=True)
            logger.info(f"Checking {active_targets.count()} active targets for {stock.symbol}")

            for target in active_targets:
                if target.is_triggered(current_price):
                    logger.info(f"Target triggered for {stock.symbol}: {target.direction} ${target.price}")
                    if (not target.last_triggered or
                            (datetime.now() - target.last_triggered).total_seconds() > 3600):
                        self.send_alert(stock, target, current_price)
                    else:
                        logger.info(f"Skipping alert for {stock.symbol} - already triggered within the hour")

        except Exception as e:
            logger.error(f"Error checking alerts for {stock.symbol}: {str(e)}", exc_info=True)

    def update_all_stocks(self):
        """
        Update all stocks in the database
        """
        try:
            logger.info("Starting stock update cycle")
            from .models import Stock  # Import here to avoid circular import

            stocks = Stock.objects.all()
            logger.info(f"Found {stocks.count()} stocks to update")

            for stock in stocks:
                try:
                    logger.info(f"Processing {stock.symbol}")
                    self.check_price_alerts(stock)
                    time.sleep(2)  # Rate limiting
                    logger.info(f"Completed processing {stock.symbol}")
                except Exception as e:
                    logger.error(f"Error processing {stock.symbol}: {str(e)}", exc_info=True)
                    continue

            logger.info("Completed stock update cycle")

        except Exception as e:
            logger.error(f"Error in update cycle: {str(e)}", exc_info=True)