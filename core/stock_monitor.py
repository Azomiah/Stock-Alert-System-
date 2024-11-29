from datetime import datetime
from django.core.mail import send_mail
from django.conf import settings
import logging
from decimal import Decimal
import yfinance as yf
import time

logger = logging.getLogger(__name__)

class StockMonitor:
    def get_stock_info(self, symbol):
        """
        Fetch comprehensive stock information using Yahoo Finance
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info:
                logger.warning(f"No data returned for {symbol}")
                return None

            return {
                'current_price': Decimal(str(info.get('regularMarketPrice', 0))),
                'previous_close': Decimal(str(info.get('previousClose', 0))),
                'market_cap': info.get('marketCap'),
                'volume': info.get('volume'),
                'day_high': Decimal(str(info.get('dayHigh', 0))),
                'day_low': Decimal(str(info.get('dayLow', 0))),
                'name': info.get('longName')
            }
        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {str(e)}")
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
            logger.error(f"Error sending alert for {stock.symbol}: {str(e)}")

    def check_price_alerts(self, stock):
        """
        Check if any price targets have been triggered for a stock
        """
        try:
            info = self.get_stock_info(stock.symbol)
            if not info:
                return

            # Update stock information
            for key, value in info.items():
                setattr(stock, key, value)
            stock.last_updated = datetime.now()
            stock.save()

            current_price = info['current_price']

            # Check all active price targets
            for target in stock.pricetarget_set.filter(is_active=True):
                if target.is_triggered(current_price):
                    # Don't send alerts more than once per hour for the same target
                    if (not target.last_triggered or
                            (datetime.now() - target.last_triggered).total_seconds() > 3600):
                        self.send_alert(stock, target, current_price)
        except Exception as e:
            logger.error(f"Error checking alerts for {stock.symbol}: {str(e)}")

    def update_all_stocks(self):
        """
        Update all stocks in the database
        """
        from .models import Stock  # Import here to avoid circular import

        logger.info("Starting stock update cycle")
        stocks = Stock.objects.all()

        for stock in stocks:
            try:
                logger.info(f"Checking {stock.symbol}")
                self.check_price_alerts(stock)
                time.sleep(2)  # Rate limiting
            except Exception as e:
                logger.error(f"Error processing {stock.symbol}: {str(e)}")
                continue

        logger.info("Completed stock update cycle")