from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from catalog.models import Category, Product, Thread

User = get_user_model()


class SlugGenerationTest(TestCase):
    def test_slug_is_derived_from_the_name(self):
        category = Category.objects.create(name='Uy-rozgor buyumlari', image='categories/x.png')
        self.assertEqual(category.slug, 'uy-rozgor-buyumlari')

    def test_explicit_slug_is_respected(self):
        category = Category.objects.create(
            name='Elektronika', slug='tech', image='categories/x.png'
        )
        self.assertEqual(category.slug, 'tech')

    def test_slug_is_not_regenerated_on_rename(self):
        category = Category.objects.create(name='Kitoblar', image='categories/x.png')
        category.name = 'Adabiyot'
        category.save()
        self.assertEqual(category.slug, 'kitoblar')


class ProductTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Kitoblar', image='categories/x.png')

    def _product(self, **overrides):
        defaults = {
            'category': self.category,
            'name': 'Atomic Habits',
            'price': Decimal('89000'),
            'return_price': Decimal('12000'),
            'description': 'demo',
            'stock': 10,
        }
        return Product.objects.create(**{**defaults, **overrides})

    def test_thumbnail_is_none_without_images(self):
        self.assertIsNone(self._product().thumbnail)

    def test_thumbnail_returns_the_lowest_ordered_image(self):
        product = self._product()
        product.images.create(image='products/second.png', order=2)
        first = product.images.create(image='products/first.png', order=1)
        self.assertEqual(product.thumbnail, first)

    def test_products_are_ordered_newest_first(self):
        older = self._product(name='Older')
        newer = self._product(name='Newer')
        self.assertEqual(list(Product.objects.all()), [newer, older])


class ThreadDiscountTest(TestCase):
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

    def _thread(self, discount):
        return Thread(
            name='promo', product=self.product, user=self.user, discount=Decimal(discount)
        )

    def test_discount_within_the_ceiling_is_valid(self):
        self._thread('12000').full_clean(exclude=['slug'])

    def test_discount_above_return_price_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            self._thread('12001').clean()
        self.assertIn('discount', ctx.exception.message_dict)

    def test_negative_discount_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            self._thread('-1').clean()
        self.assertIn('discount', ctx.exception.message_dict)

    def test_ceiling_is_the_lower_of_price_and_return_price(self):
        # A return_price above the sale price must not let the discount exceed the price.
        self.product.price = Decimal('5000')
        self.product.save()
        with self.assertRaises(ValidationError):
            self._thread('6000').clean()
