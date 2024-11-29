# core/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings
from .models import Stock, PriceTarget
from .stock_monitor import StockMonitor
import json
import logging

logger = logging.getLogger(__name__)


def landing_page(request):
    return render(request, 'core/landing.html')


def dashboard(request):
    stocks = Stock.objects.all().prefetch_related('pricetarget_set')
    logger.info(f"Retrieved {stocks.count()} stocks for dashboard")
    return render(request, 'core/dashboard.html', {'stocks': stocks})


@require_http_methods(["POST"])
def add_stock(request):
    try:
        data = json.loads(request.body)
        symbol = data.get('symbol')
        logger.info(f"Attempting to add stock: {symbol}")

        if not symbol:
            logger.warning("Stock symbol not provided")
            return JsonResponse({
                'status': 'error',
                'message': 'Symbol not provided'
            })

        # Check if stock already exists
        if Stock.objects.filter(symbol=symbol.upper()).exists():
            logger.warning(f"Stock {symbol} already exists")
            return JsonResponse({
                'status': 'error',
                'message': 'Stock already exists'
            })

        monitor = StockMonitor()
        info = monitor.get_stock_info(symbol)
        logger.info(f"Fetched info for {symbol}: {info}")

        if info and info.get('current_price'):
            stock = Stock.objects.create(
                symbol=symbol.upper(),
                current_price=info['current_price'],
                previous_close=info['previous_close'],
                market_cap=info['market_cap'],
                volume=info['volume'],
                day_high=info['day_high'],
                day_low=info['day_low'],
                name=info['name']
            )
            logger.info(f"Successfully created stock: {stock.symbol} with price {stock.current_price}")
            return JsonResponse({
                'status': 'success',
                'price': float(info['current_price'])
            })
        else:
            logger.error(f"Unable to fetch stock info for {symbol}")
            return JsonResponse({
                'status': 'error',
                'message': 'Unable to fetch stock info'
            })
    except Exception as e:
        logger.error(f"Error adding stock: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


@require_http_methods(["POST"])
def add_target(request, stock_id):
    try:
        data = json.loads(request.body)
        stock = get_object_or_404(Stock, id=stock_id)
        logger.info(f"Adding target for stock {stock.symbol}")

        price = data.get('price')
        direction = data.get('direction')

        if not price or not direction:
            logger.warning("Missing price or direction in target creation")
            return JsonResponse({
                'status': 'error',
                'message': 'Price and direction are required'
            })

        if direction not in ['above', 'below', 'exact']:
            logger.warning(f"Invalid direction provided: {direction}")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid direction'
            })

        target = PriceTarget.objects.create(
            stock=stock,
            price=price,
            direction=direction
        )
        logger.info(f"Created price target: {target}")
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Error adding target: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


@require_http_methods(["POST"])
def delete_target(request, stock_id, target_id):
    try:
        target = get_object_or_404(PriceTarget, id=target_id, stock_id=stock_id)
        logger.info(f"Deleting target {target}")
        target.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Error deleting target: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


@require_http_methods(["POST"])
def delete_stock(request, stock_id):
    try:
        stock = get_object_or_404(Stock, id=stock_id)
        logger.info(f"Deleting stock {stock.symbol}")
        stock.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Error deleting stock: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


def check_prices(request):
    try:
        logger.info("Starting price check for all stocks")
        monitor = StockMonitor()
        stocks = Stock.objects.all()
        logger.info(f"Checking prices for {stocks.count()} stocks")

        for stock in stocks:
            monitor.check_price_alerts(stock)

        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Error checking prices: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


def test_email(request):
    try:
        logger.info("Sending test email")
        send_mail(
            'Test StockWatch Alert',
            'This is a test email from StockWatch',
            settings.EMAIL_HOST_USER,
            [settings.NOTIFICATION_EMAIL],
            fail_silently=False,
        )
        logger.info("Test email sent successfully")
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Error sending test email: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })