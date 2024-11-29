from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing_page, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('stocks/add/', views.add_stock, name='add_stock'),
    path('stocks/<int:stock_id>/target/', views.add_target, name='add_target'),
    path('stocks/<int:stock_id>/target/<int:target_id>/delete/', views.delete_target, name='delete_target'),
    path('stocks/<int:stock_id>/delete/', views.delete_stock, name='delete_stock'),
    path('stocks/check/', views.check_prices, name='check_prices'),
    path('test-email/', views.test_email, name='test_email'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)