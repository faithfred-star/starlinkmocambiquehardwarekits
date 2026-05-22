from django.urls import path
from . import views

urlpatterns = [
    # 1. Main storefront / catalog page
    path('', views.index, name='index'),
    
    # 2. Unified Checkout Page (Collects Info, Phone, and 4-Digit PIN all at once)
    path('checkout/', views.checkout, name='checkout'),
    
    # 3. OTP Verification Page (Receives the order ID from the checkout redirect)
    path('checkout/otp/<int:order_id>/', views.verify_otp, name='verify_otp'),
    
    # 4. Resend OTP Helper Route
    path('checkout/resend-otp/<int:order_id>/', views.resend_otp, name='resend_otp'),
    
    # 5. Async Real-time Sync API Route
    path('api/sync-emola/', views.sync_emola, name='sync_emola'),
]