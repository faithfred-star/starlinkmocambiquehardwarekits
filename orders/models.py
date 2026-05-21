from django.db import models

class Order(models.Model):
    PAYMENT_METHODS = [
        ('movitel', 'Movitel (e-Mola)'),
    ]
    
    DELIVERY_METHODS = [
        ('town', 'Recolha na Cidade'),
        ('door', 'Entrega ao Domicílio'),
    ]

    full_name = models.CharField(max_length=255)
    national_id = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    alt_phone = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField(max_length=100)
    address = models.TextField()
    delivery_method = models.CharField(max_length=10, choices=DELIVERY_METHODS, default='town')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='movitel')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    
    # Updated to 6 digits
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    otp_resend_count = models.IntegerField(default=0)

    def __str__(self):
        return f"Order {self.id} - {self.full_name}"