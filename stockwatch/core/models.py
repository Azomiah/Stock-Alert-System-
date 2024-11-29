from django.db import models
from decimal import Decimal

class Stock(models.Model):
    symbol = models.CharField(max_length=10, db_index=True)
    name = models.CharField(max_length=100, null=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    previous_close = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    market_cap = models.BigIntegerField(null=True)
    volume = models.BigIntegerField(null=True)
    day_high = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    day_low = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    last_updated = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ['symbol']

    def __str__(self):
        return f"{self.symbol} - {self.name or 'N/A'}"

    def price_change_abs(self):
        if self.current_price and self.previous_close:
            return abs(self.current_price - self.previous_close)
        return Decimal('0.00')

    @property
    def price_change(self):
        if self.current_price and self.previous_close:
            return self.current_price - self.previous_close
        return Decimal('0.00')

    @property
    def price_change_percentage(self):
        if self.current_price and self.previous_close and self.previous_close != 0:
            return (self.price_change / self.previous_close) * 100
        return Decimal('0.00')

class PriceTarget(models.Model):
    DIRECTION_CHOICES = [
        ('above', 'Above'),
        ('below', 'Below'),
        ('exact', 'Exact'),
    ]

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    direction = models.CharField(max_length=5, choices=DIRECTION_CHOICES)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_triggered = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.stock.symbol} {self.direction} ${self.price}"

    def is_triggered(self, current_price):
        if not current_price:
            return False

        if self.direction == 'above':
            return current_price >= self.price
        elif self.direction == 'below':
            return current_price <= self.price
        else:  # exact
            # Using a small threshold for exact matches (within 0.1%)
            threshold = self.price * Decimal('0.001')
            return abs(current_price - self.price) <= threshold