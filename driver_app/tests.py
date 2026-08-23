from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product
from orders.models import Order

User = get_user_model()


class DriverAccessControlTest(TestCase):
    def setUp(self):
        self.driver = User.objects.create_user(
            phone='+998905678901', password='pw', role=User.RoleChoices.DRIVER
        )
        self.seller = User.objects.create_user(
            phone='+998901234567', password='pw', role=User.RoleChoices.USER
        )
        self.operator = User.objects.create_user(
            phone='+998903456789', password='pw', role=User.RoleChoices.OPERATOR
        )

    def test_anonymous_visitor_is_redirected_to_login(self):
        response = self.client.get(reverse('driver:available-orders'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_seller_is_forbidden(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(reverse('driver:available-orders')).status_code, 403)

    def test_operator_is_forbidden(self):
        self.client.force_login(self.operator)
        self.assertEqual(self.client.get(reverse('driver:my-orders')).status_code, 403)

    def test_driver_is_allowed(self):
        self.client.force_login(self.driver)
        self.assertEqual(self.client.get(reverse('driver:available-orders')).status_code, 200)


class DriverOrderQueueTest(TestCase):
    def setUp(self):
        self.driver = User.objects.create_user(
            phone='+998905678901', password='pw', role=User.RoleChoices.DRIVER
        )
        self.other_driver = User.objects.create_user(
            phone='+998906789012', password='pw', role=User.RoleChoices.DRIVER
        )
        category = Category.objects.create(name='Kitoblar', image='categories/x.png')
        self.product = Product.objects.create(
            category=category,
            name='Atomic Habits',
            price=Decimal('89000'),
            return_price=Decimal('12000'),
            description='demo',
            stock=10,
        )

    def _order(self, **overrides):
        defaults = {
            'product': self.product,
            'customer_name': 'Aziz Karimov',
            'phone': '+998901112233',
            'status': Order.OrderStatus.SHIPPING,
        }
        return Order.objects.create(**{**defaults, **overrides})

    def test_my_orders_only_lists_this_drivers_deliveries(self):
        mine = self._order(driver=self.driver)
        self._order(driver=self.other_driver)

        self.client.force_login(self.driver)
        response = self.client.get(reverse('driver:my-orders'))
        self.assertEqual(list(response.context['orders']), [mine])

    def test_driver_cannot_deliver_another_drivers_order(self):
        theirs = self._order(driver=self.other_driver)
        self.client.force_login(self.driver)
        self.client.post(reverse('driver:deliver-order', args=[theirs.pk]))

        theirs.refresh_from_db()
        self.assertNotEqual(theirs.status, Order.OrderStatus.DELIVERED)
