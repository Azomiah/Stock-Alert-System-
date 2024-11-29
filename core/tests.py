from django.test import TestCase

# Create your tests here.
# core/tests.py
from django.test import TestCase
from django.core import mail
from .models import Stock, PriceTarget
from .tasks import StockPriceUpdater
from datetime import datetime


class StockAlertTest(TestCase):
    def setUp(self):
        # Create test stock
        self.stock = Stock.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            current_price=180.00
        )

        # Create price target
        self.target = PriceTarget.objects.create(
            stock=self.stock,
            price=190.00,
            direction='above'
        )

    def test_price_alert(self):
        updater = StockPriceUpdater()
        # Simulate price change that triggers alert
        new_price = 191.45
        updater.send_alert(self.stock.symbol, new_price, self.target.price, self.target.direction)

        # Check if email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        expected_subject = "🚨 Stock Alert: AAPL"
        self.assertEqual(email.subject, expected_subject)

        # Print email content for verification
        print("\nTest Email Content:")
        print("-" * 40)
        print(email.body)
        print("-" * 40)


def display_test_alert():
    alert = """
🚨 Stock Alert: AAPL
Target: $190.00 above
Current Price: $191.45
Time: {}
""".format(datetime.now().strftime('%I:%M %p, %b %d'))

    print(alert)

if __name__ == "__main__":
    display_test_alert()