from django.db import migrations, models


def cancel_duplicate_pending_payments(apps, schema_editor):
    """Keep only the newest pending payment per user; cancel the rest."""
    Payment = apps.get_model('orders', 'Payment')
    seen = set()
    stale = []
    for payment in Payment.objects.filter(status='new').order_by('user_id', '-created_at', '-id'):
        if payment.user_id in seen:
            stale.append(payment.pk)
        else:
            seen.add(payment.user_id)
    Payment.objects.filter(pk__in=stale).update(status='cancelled')


def noop(apps, schema_editor):
    """Cancelled payments are indistinguishable from ones cancelled normally."""


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0011_order_address'),
    ]

    operations = [
        migrations.RunPython(cancel_duplicate_pending_payments, noop),
        migrations.AddConstraint(
            model_name='payment',
            constraint=models.UniqueConstraint(
                condition=models.Q(('status', 'new')),
                fields=('user',),
                name='unique_pending_payment_per_user',
            ),
        ),
    ]
