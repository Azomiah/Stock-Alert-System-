# stock_monitor.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
import yfinance as yf
from decimal import Decimal
from django.conf import settings
import time
from .models import Stock

logger = logging.getLogger(__name__)


class StockMonitor:
    def send_gmail_alert(self, subject, message):
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.GMAIL_EMAIL
            msg['To'] = settings.NOTIFICATION_EMAIL
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(settings.GMAIL_EMAIL, settings.GMAIL_APP_PASSWORD)
            server.send_message(msg)
            server.quit()

            logger.info("Gmail alert sent successfully")
        except Exception as e:
            logger.error(f"Failed to send Gmail alert: {str(e)}")

    def send_alert(self, stock, target, current_price):
        direction_text = {
            'above': 'risen above',
            'below': 'fallen below',
            'exact': 'reached'
        }

        subject = f"StockWatch Alert: {stock.symbol}"
        message = (
            f"StockWatch Alert! {stock.symbol} ({stock.name}) has {direction_text[target.direction]} "
            f"your target of ${target.price}.\n\n"
            f"Current Price: ${current_price}\n"
            f"Previous Close: ${stock.previous_close}\n"
            f"Day Range: ${stock.day_low} - ${stock.day_high}\n"
            f"Time: {datetime.now().strftime('%I:%M %p, %b %d')}\n\n"
            f"View more details at: {settings.SITE_URL}/dashboard/"
        )

        self.send_gmail_alert(subject, message)

    def get_stock_info(self, symbol):
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

    def check_price_alerts(self, stock):
        info = self.get_stock_info(stock.symbol)
        if not info:
            return

        for key, value in info.items():
            setattr(stock, key, value)
        stock.last_updated = datetime.now()
        stock.save()

        current_price = info['current_price']

        for target in stock.pricetarget_set.filter(is_active=True):
            if ((target.direction == 'above' and current_price >= target.price) or
                    (target.direction == 'below' and current_price <= target.price) or
                    (target.direction == 'exact' and abs(current_price - target.price) <= 0.01)):

                if (not target.last_triggered or
                        (datetime.now() - target.last_triggered).total_seconds() > 3600):
                    self.send_alert(stock, target, current_price)
                    target.last_triggered = datetime.now()
                    target.save()

    def update_all_stocks(self):
        """Update all stocks in database"""
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