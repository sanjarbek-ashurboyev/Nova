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


class OrderStatusRulesTest(TestCase):
    """Status changes an operator makes, and the stock each one moves."""

    def setUp(self):
        self.operator = User.objects.create_user(
            phone='+998903456789', password='pw', role=User.RoleChoices.OPERATOR
        )
        category = Category.objects.create(name='Kitoblar', image='categories/x.png')
        # 10 in the warehouse, 2 already taken by the order below.
        self.product = Product.objects.create(
            category=category, name='Atomic Habits', price=Decimal('89000'),
            return_price=Decimal('12000'), description='demo', stock=8,
        )
        self.order = Order.objects.create(
            product=self.product, customer_name='Aziz Karimov', phone='+998901112233',
            quantity=2, status=Order.OrderStatus.NEW, operator=self.operator, address='Toshkent',
        )
        self.client.force_login(self.operator)

    def quick_change(self, status):
        return self.client.post(reverse('operator:change-status', args=[self.order.pk]),
                                {'status': status, 'comment': ''})

    def detail_change(self, **changes):
        data = {'customer_name': self.order.customer_name, 'phone': self.order.phone,
                'quantity': self.order.quantity, 'address': self.order.address,
                'status': self.order.status, 'comment': '', **changes}
        return self.client.post(reverse('operator:order-detail', args=[self.order.pk]), data)

    def move(self, *statuses):
        """Walk the order through allowed statuses, failing loudly if one is refused."""
        for status in statuses:
            self.quick_change(status)
            self.order.refresh_from_db()
            self.assertEqual(self.order.status, status)

    def stock(self):
        self.product.refresh_from_db()
        return self.product.stock

    def test_cancelling_an_order_puts_its_items_back(self):
        self.move(Order.OrderStatus.CANCELLED)
        self.assertEqual(self.stock(), 10)

    def test_a_returned_shipment_puts_its_items_back(self):
        self.move(Order.OrderStatus.PACKAGING, Order.OrderStatus.SHIPPING, Order.OrderStatus.RETURNED)
        self.assertEqual(self.stock(), 10)

    def test_a_return_after_delivery_puts_its_items_back(self):
        self.move(Order.OrderStatus.PICKUP_LATER, Order.OrderStatus.DELIVERED)
        self.assertEqual(self.stock(), 8, 'a delivered order keeps its items out of stock')
        self.move(Order.OrderStatus.RETURNED)
        self.assertEqual(self.stock(), 10)

    def test_stock_comes_back_only_once(self):
        self.move(Order.OrderStatus.CANCELLED)
        self.quick_change(Order.OrderStatus.CANCELLED)  # a double submit
        self.move(Order.OrderStatus.ARCHIVE)
        self.assertEqual(self.stock(), 10)

    def test_progressing_an_order_does_not_touch_stock(self):
        self.move(Order.OrderStatus.HOLD, Order.OrderStatus.PACKAGING, Order.OrderStatus.SHIPPING)
        self.assertEqual(self.stock(), 8)

    def test_only_the_driver_can_mark_a_shipped_order_delivered(self):
        self.move(Order.OrderStatus.PACKAGING, Order.OrderStatus.SHIPPING)

        response = self.quick_change(Order.OrderStatus.DELIVERED)

        self.assertRedirects(response, reverse('operator:my-orders'), fetch_redirect_response=False)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.OrderStatus.SHIPPING)
        message = str(list(response.wsgi_request._messages)[0])
        self.assertIn("o'tib bo'lmaydi", message)

    def test_finished_orders_cannot_be_reopened(self):
        self.move(Order.OrderStatus.CANCELLED)
        for status in (Order.OrderStatus.NEW, Order.OrderStatus.PACKAGING, Order.OrderStatus.DELIVERED):
            with self.subTest(status):
                self.quick_change(status)
                self.order.refresh_from_db()
                self.assertEqual(self.order.status, Order.OrderStatus.CANCELLED)
        self.assertEqual(self.stock(), 10)

    def test_a_rejected_quick_change_redirects_instead_of_rendering_a_broken_page(self):
        response = self.quick_change('not-a-status')
        self.assertRedirects(response, reverse('operator:my-orders'), fetch_redirect_response=False)

    def test_quantity_changes_move_stock_while_the_order_is_open(self):
        self.detail_change(quantity=5)
        self.assertEqual(self.stock(), 5)
        self.order.refresh_from_db()
        self.detail_change(quantity=1)
        self.assertEqual(self.stock(), 9)

    def test_quantity_cannot_exceed_what_is_in_stock(self):
        response = self.detail_change(quantity=11)
        self.assertEqual(response.status_code, 200)  # the form is shown again with the error
        self.order.refresh_from_db()
        self.assertEqual((self.order.quantity, self.stock()), (2, 8))

    def test_quantity_is_fixed_once_the_order_has_shipped(self):
        self.move(Order.OrderStatus.PACKAGING, Order.OrderStatus.SHIPPING)

        response = self.detail_change(quantity=5)

        self.assertIn('quantity', response.context['form'].errors)
        self.order.refresh_from_db()
        self.assertEqual((self.order.quantity, self.stock()), (2, 8))

    def test_editing_quantity_and_cancelling_together_returns_everything(self):
        self.detail_change(quantity=3, status=Order.OrderStatus.CANCELLED)
        self.assertEqual(self.stock(), 10)

    def test_the_detail_page_offers_only_allowed_statuses(self):
        self.move(Order.OrderStatus.PACKAGING, Order.OrderStatus.SHIPPING)
        page = self.client.get(reverse('operator:order-detail', args=[self.order.pk])).content.decode()

        self.assertIn('value="returned"', page)
        self.assertNotIn('value="delivered"', page)
        self.assertNotIn('value="cancelled"', page)
