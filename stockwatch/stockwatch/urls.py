from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Main pages
    path('', views.landing_page, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Stock operations
    path('stocks/add/', views.add_stock, name='add_stock'),
    path('stocks/<int:stock_id>/delete/', views.delete_stock, name='delete_stock'),
    path('stocks/check/', views.check_prices, name='check_prices'),

    # Price target operations
    path('stocks/<int:stock_id>/target/', views.add_target, name='add_target'),
    path('stocks/<int:stock_id>/target/<int:target_id>/delete/',
         views.delete_target, name='delete_target'),

    # Utility endpoints
    path('test-email/', views.test_email, name='test_email'),
    path('stocks/<int:stock_id>/delete/', views.delete_stock, name='delete_stock'),
]