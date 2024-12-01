# core/views.py
from datetime import datetime

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal
from .stock_monitor import StockMonitor
from .models import Stock, PriceTarget
from django.shortcuts import render
import anthropic
import requests
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import yfinance as yf
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


def test_stock_alert(request):
    monitor = StockMonitor()
    example_stock = Stock(
        symbol="AAPL",
        name="Apple Inc.",
        current_price=Decimal("190.50"),
        previous_close=Decimal("188.25"),
        day_high=Decimal("191.00"),
        day_low=Decimal("189.00"),
        volume=1000000,
        market_cap=3000000000000
    )
    example_target = PriceTarget(
        stock=example_stock,
        price=Decimal("190.00"),
        direction="above",
        is_active=True
    )

    subject = f"🚨 StockWatch Alert: {example_stock.symbol}"
    message = (
        f"Stock Alert for {example_stock.symbol} ({example_stock.name})\n\n"
        f"The stock price has risen above your target of ${example_target.price}\n\n"
        f"Current Price: ${example_stock.current_price}\n"
        f"Previous Close: ${example_stock.previous_close}\n"
        f"Today's Range: ${example_stock.day_low} - ${example_stock.day_high}\n"
        f"Time: {datetime.now().strftime('%I:%M %p, %b %d, %Y')}\n\n"
        f"View more details at: {settings.SITE_URL}/dashboard/\n\n"
        f"StockWatch - Your Market Monitor"
    )

    monitor.send_gmail_alert(subject, message)
    return JsonResponse({'status': 'success', 'message': 'Test alert sent'})


def reports_page(request):
    """Render the reports page"""
    return render(request, 'core/reports.html')


def analyze_performance(info):
    try:
        change = ((info.get('currentPrice', 0) - info.get('previousClose', 0)) /
                  info.get('previousClose', 0) * 100)
        if change > 5:
            return "Strong positive performance (>5% gain)"
        elif change > 2:
            return "Moderate positive performance (2-5% gain)"
        elif change > -2:
            return "Stable performance (±2%)"
        elif change > -5:
            return "Moderate negative performance (2-5% loss)"
        else:
            return "Strong negative performance (>5% loss)"
    except:
        return "Performance analysis unavailable"


def analyze_volume(info):
    try:
        avg_volume = info.get('averageVolume', 0)
        current_volume = info.get('volume', 0)
        ratio = current_volume / avg_volume if avg_volume else 0
        if ratio > 2:
            return "Extremely high volume (>2x average)"
        elif ratio > 1.5:
            return "High volume (1.5-2x average)"
        elif ratio > 0.75:
            return "Normal volume"
        else:
            return "Low volume (<75% of average)"
    except:
        return "Volume analysis unavailable"


def analyze_price_trend(hist):
    try:
        last_price = hist['Close'][-1]
        ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
        ma5 = hist['Close'].rolling(window=5).mean().iloc[-1]

        trend = []
        if last_price > ma20:
            trend.append("Above 20-day moving average")
        else:
            trend.append("Below 20-day moving average")

        if ma5 > ma20:
            trend.append("Short-term upward trend")
        else:
            trend.append("Short-term downward trend")

        return ", ".join(trend)
    except:
        return "Trend analysis unavailable"


def analyze_market_position(info):
    try:
        market_cap = info.get('marketCap', 0)
        if market_cap >= 200e9:
            cap_category = "Mega Cap"
        elif market_cap >= 10e9:
            cap_category = "Large Cap"
        elif market_cap >= 2e9:
            cap_category = "Mid Cap"
        elif market_cap >= 300e6:
            cap_category = "Small Cap"
        else:
            cap_category = "Micro Cap"

        beta = info.get('beta', 0)
        if beta > 1.5:
            volatility = "High volatility"
        elif beta > 0.5:
            volatility = "Moderate volatility"
        else:
            volatility = "Low volatility"

        return f"{cap_category} stock with {volatility}"
    except:
        return "Market position analysis unavailable"


@require_http_methods(["POST"])
def generate_report(request):
    try:
        data = json.loads(request.body)
        symbol = data.get('topic', '').upper()

        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info or 'longName' not in info:
            return JsonResponse({
                'error': 'Could not find stock information'
            }, status=400)

        hist = ticker.history(period="1mo")

        report = f"""<div class="text-[#C6A265]">
<h1 class="text-2xl font-bold mb-4">Financial Report for {symbol}</h1>

<h2 class="text-xl font-semibold mt-6 mb-2">COMPANY OVERVIEW</h2>
<div class="mb-4">
    <p>Name: {info.get('longName', symbol)}</p>
    <p>Industry: {info.get('industry', 'N/A')}</p>
    <p>Sector: {info.get('sector', 'N/A')}</p>
    <p>Description: {info.get('longBusinessSummary', 'N/A')}</p>
</div>

<h2 class="text-xl font-semibold mt-6 mb-2">CURRENT MARKET DATA</h2>
<div class="mb-4">
    <p>Current Price: ${info.get('currentPrice', 'N/A')}</p>
    <p>Previous Close: ${info.get('previousClose', 'N/A')}</p>
    <p>Open: ${info.get('open', 'N/A')}</p>
    <p>Day Range: ${info.get('dayLow', 'N/A')} - ${info.get('dayHigh', 'N/A')}</p>
    <p>Volume: {info.get('volume', 'N/A'):,}</p>
</div>

<h2 class="text-xl font-semibold mt-6 mb-2">FINANCIAL METRICS</h2>
<div class="mb-4">
    <p>Market Cap: ${info.get('marketCap', 'N/A'):,}</p>
    <p>P/E Ratio: {info.get('trailingPE', 'N/A')}</p>
    <p>EPS (TTM): ${info.get('trailingEps', 'N/A')}</p>
    <p>52 Week Range: ${info.get('fiftyTwoWeekLow', 'N/A')} - ${info.get('fiftyTwoWeekHigh', 'N/A')}</p>
    <p>Forward Dividend Yield: {info.get('dividendYield', 0) * 100:.2f}%</p>
</div>

<h2 class="text-xl font-semibold mt-6 mb-2">ANALYSIS</h2>
<div class="mb-4">
    <p>• Market Performance: {analyze_performance(info)}</p>
    <p>• Volume Analysis: {analyze_volume(info)}</p>
    <p>• Price Trend: {analyze_price_trend(hist)}</p>
    <p>• Market Position: {analyze_market_position(info)}</p>
</div>

<p class="mt-6 text-sm">Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</div>"""

        return JsonResponse({
            'status': 'success',
            'report': report
        })

    except Exception as e:
        logging.error(f"Error generating report: {str(e)}")
        return JsonResponse({
            'error': 'Failed to generate report. Make sure you entered a valid stock symbol.'
        }, status=500)