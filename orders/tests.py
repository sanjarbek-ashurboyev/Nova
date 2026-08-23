from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from catalog.models import Category, Product, Thread
from orders.models import Order, Payment

User = get_user_model()


class OrderTotalPriceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone='+998901234567', password='pw')
        category = Category.objects.create(name='Kitoblar', image='categories/x.png')
        self.product = Product.objects.create(
            category=category,
            name='Atomic Habits',
            price=Decimal('89000'),
            return_price=Decimal('12000'),
            description='demo',
            stock=10,
        )

    def _order(self, quantity=1, thread=None):
        return Order.objects.create(
            product=self.product,
            customer_name='Aziz Karimov',
            phone='+998901112233',
            quantity=quantity,
            thread=thread,
        )

    def test_total_is_price_times_quantity_without_a_thread(self):
        self.assertEqual(self._order(quantity=3).total_price, Decimal('267000'))

    def test_thread_discount_is_applied_per_unit(self):
        thread = Thread.objects.create(
            name='promo', product=self.product, user=self.user, discount=Decimal('9000')
        )
        # (89000 - 9000) * 2
        self.assertEqual(self._order(quantity=2, thread=thread).total_price, Decimal('160000'))

    def test_total_never_goes_negative(self):
        self.product.price = Decimal('1000')
        self.product.save()
        thread = Thread.objects.create(
            name='promo', product=self.product, user=self.user, discount=Decimal('5000')
        )
        self.assertEqual(self._order(quantity=2, thread=thread).total_price, Decimal('0'))


class PaymentBalanceLedgerTest(TestCase):
    """Payment.save() keeps User.balance in sync as the payout status changes."""

    def setUp(self):
        self.user = User.objects.create_user(
            phone='+998901234567', password='pw', balance=Decimal('500000')
        )

    def _balance(self):
        self.user.refresh_from_db()
        return self.user.balance

    def test_new_payment_does_not_touch_the_balance(self):
        Payment.objects.create(user=self.user, card_number='8600123456780001', amount=Decimal('100000'))
        self.assertEqual(self._balance(), Decimal('500000'))

    def test_marking_paid_deducts_the_amount(self):
        payment = Payment.objects.create(
            user=self.user, card_number='8600123456780001', amount=Decimal('100000')
        )
        payment.status = Payment.Status.PAID
        payment.save()
        self.assertEqual(self._balance(), Decimal('400000'))

    def test_paying_is_not_applied_twice_on_a_repeated_save(self):
        payment = Payment.objects.create(
            user=self.user, card_number='8600123456780001', amount=Decimal('100000')
        )
        payment.status = Payment.Status.PAID
        payment.save()
        payment.save()
        self.assertEqual(self._balance(), Decimal('400000'))

    def test_reverting_a_paid_payment_refunds_the_balance(self):
        payment = Payment.objects.create(
            user=self.user, card_number='8600123456780001', amount=Decimal('100000')
        )
        payment.status = Payment.Status.PAID
        payment.save()

        payment.status = Payment.Status.CANCELLED
        payment.save()
        self.assertEqual(self._balance(), Decimal('500000'))

    def test_editing_the_amount_of_a_paid_payment_adjusts_by_the_delta(self):
        payment = Payment.objects.create(
            user=self.user, card_number='8600123456780001', amount=Decimal('100000')
        )
        payment.status = Payment.Status.PAID
        payment.save()  # balance 400000

        payment.amount = Decimal('150000')
        payment.save()  # a further 50000 leaves the balance
        self.assertEqual(self._balance(), Decimal('350000'))

    def test_reloaded_instance_tracks_its_persisted_status(self):
        payment = Payment.objects.create(
            user=self.user, card_number='8600123456780001', amount=Decimal('100000')
        )
        payment.status = Payment.Status.PAID
        payment.save()

        reloaded = Payment.objects.get(pk=payment.pk)
        reloaded.save()  # no status change — balance must stay put
        self.assertEqual(self._balance(), Decimal('400000'))

    def test_only_one_pending_payment_is_allowed_per_user(self):
        Payment.objects.create(user=self.user, card_number='8600123456780001', amount=Decimal('10000'))
        with self.assertRaises(IntegrityError):
            Payment.objects.create(
                user=self.user, card_number='8600123456780002', amount=Decimal('20000')
            )

    def test_a_second_payment_is_allowed_once_the_first_is_settled(self):
        first = Payment.objects.create(
            user=self.user, card_number='8600123456780001', amount=Decimal('10000')
        )
        first.status = Payment.Status.PAID
        first.save()

        Payment.objects.create(user=self.user, card_number='8600123456780002', amount=Decimal('20000'))
        self.assertEqual(Payment.objects.filter(user=self.user).count(), 2)
