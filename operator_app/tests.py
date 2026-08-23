from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product
from orders.models import Order

User = get_user_model()


class OperatorAccessControlTest(TestCase):
    """Every operator route must be closed to anonymous visitors and other roles."""

    def setUp(self):
        self.operator = User.objects.create_user(
            phone='+998903456789', password='pw', role=User.RoleChoices.OPERATOR
        )
        self.seller = User.objects.create_user(
            phone='+998901234567', password='pw', role=User.RoleChoices.USER
        )
        self.driver = User.objects.create_user(
            phone='+998905678901', password='pw', role=User.RoleChoices.DRIVER
        )

    def test_anonymous_visitor_is_redirected_to_login(self):
        response = self.client.get(reverse('operator:new-orders'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_seller_is_forbidden(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(reverse('operator:new-orders')).status_code, 403)

    def test_driver_is_forbidden(self):
        self.client.force_login(self.driver)
        self.assertEqual(self.client.get(reverse('operator:my-orders')).status_code, 403)

    def test_operator_is_allowed(self):
        self.client.force_login(self.operator)
        self.assertEqual(self.client.get(reverse('operator:new-orders')).status_code, 200)


class OperatorTakeOrderTest(TestCase):
    def setUp(self):
        self.operator = User.objects.create_user(
            phone='+998903456789', password='pw', role=User.RoleChoices.OPERATOR
        )
        self.other_operator = User.objects.create_user(
            phone='+998904567890', password='pw', role=User.RoleChoices.OPERATOR
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
            'status': Order.OrderStatus.NEW,
        }
        return Order.objects.create(**{**defaults, **overrides})

    def test_new_orders_list_hides_already_claimed_orders(self):
        unclaimed = self._order()
        self._order(operator=self.other_operator, status=Order.OrderStatus.PACKAGING)

        self.client.force_login(self.operator)
        response = self.client.get(reverse('operator:new-orders'))
        self.assertEqual(list(response.context['orders']), [unclaimed])

    def test_my_orders_only_lists_the_signed_in_operators_work(self):
        mine = self._order(operator=self.operator, status=Order.OrderStatus.PACKAGING)
        self._order(operator=self.other_operator, status=Order.OrderStatus.PACKAGING)

        self.client.force_login(self.operator)
        response = self.client.get(reverse('operator:my-orders'))
        self.assertEqual(list(response.context['orders']), [mine])

    def test_operator_cannot_open_another_operators_order(self):
        theirs = self._order(operator=self.other_operator, status=Order.OrderStatus.PACKAGING)
        self.client.force_login(self.operator)
        response = self.client.get(reverse('operator:order-detail', args=[theirs.pk]))
        self.assertIn(response.status_code, (403, 404))
