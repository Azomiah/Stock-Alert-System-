import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
import yfinance as yf
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
import time
from .models import Stock

logger = logging.getLogger(__name__)


class StockMonitor:
    def __init__(self):
        self.update_interval = 60  # seconds
        self.price_threshold = Decimal('0.001')  # 0.1% threshold for exact price matches

    def format_decimal(self, value):
        """Format decimal to 2 places with proper rounding"""
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def get_stock_info(self, symbol):
        """Fetch comprehensive stock information"""
        try:
            ticker = yf.Ticker(symbol)

            # Get real-time price data
            price_data = ticker.history(period='1d')
            if price_data.empty:
                logger.warning(f"No price data available for {symbol}")
                return None

            # Get general info
            info = ticker.info
            if not info:
                logger.warning(f"No info available for {symbol}")
                return None

            return {
                'current_price': self.format_decimal(price_data['Close'].iloc[-1]),
                'previous_close': self.format_decimal(info.get('previousClose', 0)),
                'market_cap': info.get('marketCap'),
                'volume': info.get('volume', 0),
                'day_high': self.format_decimal(price_data['High'].iloc[-1]),
                'day_low': self.format_decimal(price_data['Low'].iloc[-1]),
                'name': info.get('longName', symbol)
            }
        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {str(e)}")
            return None

    def send_gmail_alert(self, subject, message):
        """Send email alert using Gmail SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.GMAIL_EMAIL
            msg['To'] = settings.NOTIFICATION_EMAIL
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))

            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(settings.GMAIL_EMAIL, settings.GMAIL_APP_PASSWORD)
                server.send_message(msg)

            logger.info(f"Alert email sent successfully: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send Gmail alert: {str(e)}")
            return False

    def send_alert(self, stock, target, current_price):
        """Send formatted stock price alert"""
        direction_text = {
            'above': 'risen above',
            'below': 'fallen below',
            'exact': 'reached'
        }

        subject = f"🚨 StockWatch Alert: {stock.symbol}"
        message = (
            f"Stock Alert for {stock.symbol} ({stock.name})\n\n"
            f"The stock price has {direction_text[target.direction]} your target of ${target.price}\n\n"
            f"Current Price: ${current_price}\n"
            f"Previous Close: ${stock.previous_close}\n"
            f"Today's Range: ${stock.day_low} - ${stock.day_high}\n"
            f"Time: {datetime.now().strftime('%I:%M %p, %b %d, %Y')}\n\n"
            f"View more details at: {settings.SITE_URL}/dashboard/\n\n"
            f"StockWatch - Your Market Monitor"
        )

        return self.send_gmail_alert(subject, message)

    def is_target_triggered(self, target, current_price):
        """Check if a price target has been triggered"""
        if target.direction == 'above':
            return current_price >= target.price
        elif target.direction == 'below':
            return current_price <= target.price
        else:  # exact match
            return abs(current_price - target.price) <= (target.price * self.price_threshold)

    def check_price_alerts(self, stock):
        """Check if any price targets have been triggered for a stock"""
        info = self.get_stock_info(stock.symbol)
        if not info:
            return False

        # Update stock information
        for key, value in info.items():
            setattr(stock, key, value)
        stock.last_updated = datetime.now()
        stock.save()

        current_price = info['current_price']
        alerts_sent = False

        # Check all active price targets
        for target in stock.pricetarget_set.filter(is_active=True):
            if self.is_target_triggered(target, current_price):
                # Don't send alerts more than once per hour for the same target
                if (not target.last_triggered or
                        (datetime.now() - target.last_triggered).total_seconds() > 3600):
                    if self.send_alert(stock, target, current_price):
                        target.last_triggered = datetime.now()
                        target.save()
                        alerts_sent = True

        return alerts_sent

    def update_all_stocks(self):
        """Update all stocks in database with latest information"""
        logger.info("Starting stock update cycle")
        stocks = Stock.objects.all()
        updated_count = 0

        for stock in stocks:
            try:
                logger.info(f"Checking {stock.symbol}")
                if self.check_price_alerts(stock):
                    updated_count += 1
                time.sleep(2)  # Rate limiting for API calls
            except Exception as e:
                logger.error(f"Error processing {stock.symbol}: {str(e)}")
                continue

        logger.info(f"Completed stock update cycle. Updated {updated_count} stocks.")
        return updated_count