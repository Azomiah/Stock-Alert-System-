# core/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings
from .models import Stock, PriceTarget
from .stock_monitor import StockMonitor
import json


def landing_page(request):
    return render(request, 'core/landing.html')


def dashboard(request):
    stocks = Stock.objects.all().prefetch_related('pricetarget_set')
    return render(request, 'core/dashboard.html', {'stocks': stocks})


@require_http_methods(["POST"])
def add_stock(request):
    try:
        data = json.loads(request.body)
        symbol = data.get('symbol')

        if not symbol:
            return JsonResponse({
                'status': 'error',
                'message': 'Symbol not provided'
            })

        # Check if stock already exists
        if Stock.objects.filter(symbol=symbol.upper()).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Stock already exists'
            })

        monitor = StockMonitor()
        info = monitor.get_stock_info(symbol)

        if info:
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
            return JsonResponse({
                'status': 'success',
                'price': float(info['current_price'])
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Unable to fetch stock info'
            })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


@require_http_methods(["POST"])
def add_target(request, stock_id):
    try:
        data = json.loads(request.body)
        stock = get_object_or_404(Stock, id=stock_id)

        price = data.get('price')
        direction = data.get('direction')

        if not price or not direction:
            return JsonResponse({
                'status': 'error',
                'message': 'Price and direction are required'
            })

        if direction not in ['above', 'below', 'exact']:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid direction'
            })

        PriceTarget.objects.create(
            stock=stock,
            price=price,
            direction=direction
        )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


@require_http_methods(["POST"])
def delete_target(request, stock_id, target_id):
    try:
        target = get_object_or_404(PriceTarget, id=target_id, stock_id=stock_id)
        target.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


@require_http_methods(["POST"])
def delete_stock(request, stock_id):
    try:
        stock = get_object_or_404(Stock, id=stock_id)
        stock.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


def check_prices(request):
    try:
        monitor = StockMonitor()
        for stock in Stock.objects.all():
            monitor.check_price_alerts(stock)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


def test_email(request):
    try:
        send_mail(
            'Test StockWatch Alert',
            'This is a test email from StockWatch',
            settings.EMAIL_HOST_USER,
            [settings.NOTIFICATION_EMAIL],
            fail_silently=False,
        )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })