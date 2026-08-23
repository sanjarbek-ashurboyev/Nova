"""Populate the database with a realistic demo dataset.

Intended for local development, screenshots and reviewers cloning the repo:

    python manage.py seed_demo --flush

Product and category artwork is generated on the fly with Pillow, so no binary
placeholder files need to live in version control.
"""

import random
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from accounts.models import District, Region
from catalog.models import Category, Product, ProductImage, Thread
from orders.models import Order, Payment, Survey

User = get_user_model()

DEMO_PASSWORD = 'demo12345'

PALETTE = [
    ((37, 99, 235), (14, 165, 233)),
    ((219, 39, 119), (244, 114, 182)),
    ((5, 150, 105), (52, 211, 153)),
    ((234, 88, 12), (251, 146, 60)),
    ((124, 58, 237), (167, 139, 250)),
    ((190, 18, 60), (251, 113, 133)),
]

REGIONS = {
    'Toshkent': ['Chilonzor', 'Yunusobod', 'Mirzo Ulugbek', 'Sergeli'],
    'Samarqand': ['Urgut', 'Kattaqorgon', 'Payariq'],
    'Buxoro': ['Gijduvon', 'Kogon', 'Vobkent'],
    'Fargona': ['Qoqon', 'Margilon', 'Rishton'],
}

CATEGORIES = [
    ('Kitoblar', 'Books'),
    ('Elektronika', 'Electronics'),
    ('Sport', 'Sport'),
    ('Uy-rozgor', 'Home'),
]

PRODUCTS = [
    # (category, name, price, return_price, stock, bestseller)
    ('Kitoblar', 'Atomic Habits', 89_000, 12_000, 40, True),
    ('Kitoblar', "O'tkan kunlar", 65_000, 8_000, 25, True),
    ('Kitoblar', 'Deep Work', 95_000, 14_000, 18, False),
    ('Elektronika', 'Simsiz quloqchin TWS-9', 249_000, 30_000, 60, True),
    ('Elektronika', 'Power Bank 20000mAh', 179_000, 22_000, 35, False),
    ('Elektronika', 'Smart Watch S8', 399_000, 45_000, 12, True),
    ('Sport', 'Yoga gilamchasi', 129_000, 15_000, 50, False),
    ('Sport', 'Gantel 2x5kg', 219_000, 25_000, 20, False),
    ('Uy-rozgor', 'Termos 1.2L', 99_000, 11_000, 45, True),
    ('Uy-rozgor', 'Aromadiffuzor Mist', 159_000, 18_000, 30, False),
]

CUSTOMERS = [
    ('Aziz Karimov', '+998901112233'),
    ('Nilufar Toshpolatova', '+998932224455'),
    ('Bekzod Rahimov', '+998945556677'),
    ('Malika Yusupova', '+998977778899'),
    ('Jasur Ergashev', '+998908889900'),
    ('Dilnoza Saidova', '+998913334466'),
]

STATUS_MIX = [
    Order.OrderStatus.NEW,
    Order.OrderStatus.NEW,
    Order.OrderStatus.PACKAGING,
    Order.OrderStatus.SHIPPING,
    Order.OrderStatus.DELIVERED,
    Order.OrderStatus.DELIVERED,
    Order.OrderStatus.PICKUP_LATER,
    Order.OrderStatus.RETURNED,
    Order.OrderStatus.CANCELLED,
]


def _placeholder(label, size=(800, 800), seed=0):
    """Render a gradient card with a centred label and return it as PNG bytes."""
    top, bottom = PALETTE[seed % len(PALETTE)]
    width, height = size
    image = Image.new('RGB', size, top)
    draw = ImageDraw.Draw(image)

    for y in range(height):
        ratio = y / max(height - 1, 1)
        draw.line(
            [(0, y), (width, y)],
            fill=tuple(int(a + (b - a) * ratio) for a, b in zip(top, bottom)),
        )

    try:
        font = ImageFont.load_default(size=height // 12)
    except TypeError:  # Pillow < 10 has no size argument
        font = ImageFont.load_default()

    words = label.split()
    lines, current = [], ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if len(candidate) > 14 and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)

    line_height = height // 10
    start_y = (height - line_height * len(lines)) // 2
    for index, line in enumerate(lines):
        box = draw.textbbox((0, 0), line, font=font)
        draw.text(
            ((width - (box[2] - box[0])) // 2, start_y + index * line_height),
            line,
            font=font,
            fill=(255, 255, 255),
        )

    buffer = BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()


class Command(BaseCommand):
    help = 'Create a demo dataset: regions, catalog, users, threads, orders and payments.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete existing catalog, order and non-superuser data first.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(20260823)

        if options['flush']:
            self.stdout.write('Flushing existing demo data...')
            Survey.objects.all().delete()
            Payment.objects.all().delete()
            Order.objects.all().delete()
            Thread.objects.all().delete()
            ProductImage.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            District.objects.all().delete()
            Region.objects.all().delete()

        districts = self._create_regions()
        categories = self._create_categories()
        products = self._create_products(categories)
        users = self._create_users(districts)
        threads = self._create_threads(products, users['sellers'])
        self._create_orders(products, threads, users, districts)
        self._create_payments(users['sellers'])

        self._report()

    def _create_regions(self):
        districts = []
        for region_name, district_names in REGIONS.items():
            region, _ = Region.objects.get_or_create(title=region_name)
            for district_name in district_names:
                district, _ = District.objects.get_or_create(title=district_name, region=region)
                districts.append(district)
        self.stdout.write(f'  Regions/districts: {len(REGIONS)}/{len(districts)}')
        return districts

    def _create_categories(self):
        categories = {}
        for index, (name, label) in enumerate(CATEGORIES):
            category, created = Category.objects.get_or_create(name=name, defaults={'order': index})
            if created or not category.image:
                category.image.save(
                    f'demo-category-{index}.png',
                    ContentFile(_placeholder(label, size=(600, 600), seed=index)),
                    save=True,
                )
            categories[name] = category
        self.stdout.write(f'  Categories: {len(categories)}')
        return categories

    def _create_products(self, categories):
        products = []
        for index, (category, name, price, return_price, stock, bestseller) in enumerate(PRODUCTS):
            product, created = Product.objects.get_or_create(
                name=name,
                defaults={
                    'category': categories[category],
                    'price': Decimal(price),
                    'return_price': Decimal(return_price),
                    'stock': stock,
                    'is_bestseller': bestseller,
                    'description': (
                        f'{name} — Nova demo katalogidagi namunaviy mahsulot. '
                        'Ushbu matn `seed_demo` buyrugi tomonidan yaratilgan.'
                    ),
                },
            )
            if created or not product.images.exists():
                image = ProductImage(product=product, order=0)
                image.image.save(
                    f'demo-product-{index}.png',
                    ContentFile(_placeholder(name, seed=index)),
                    save=False,
                )
                image.save()
            products.append(product)
        self.stdout.write(f'  Products: {len(products)}')
        return products

    def _create_users(self, districts):
        def make(phone, first, last, role, **extra):
            user = User.objects.filter(phone=phone).first()
            if user is None:
                user = User.objects.create_user(
                    phone=phone,
                    password=DEMO_PASSWORD,
                    first_name=first,
                    last_name=last,
                    role=role,
                    district=random.choice(districts),
                    **extra,
                )
            return user

        admin = User.objects.filter(phone='+998900000000').first()
        if admin is None:
            admin = User.objects.create_superuser(
                phone='+998900000000',
                password=DEMO_PASSWORD,
                first_name='Nova',
                last_name='Admin',
            )

        sellers = [
            make('+998901234567', 'Shohruh', 'Anvarov', User.RoleChoices.USER, balance=Decimal('450000')),
            make('+998902345678', 'Kamola', 'Ismoilova', User.RoleChoices.USER, balance=Decimal('120000')),
        ]
        sellers[1].referrer = sellers[0]
        sellers[1].save(update_fields=['referrer'])

        operators = [
            make('+998903456789', 'Otabek', 'Nazarov', User.RoleChoices.OPERATOR),
            make('+998904567890', 'Zilola', 'Qodirova', User.RoleChoices.OPERATOR),
        ]
        drivers = [
            make('+998905678901', 'Rustam', 'Sobirov', User.RoleChoices.DRIVER),
            make('+998906789012', 'Doniyor', 'Alimov', User.RoleChoices.DRIVER),
        ]

        self.stdout.write(
            f'  Users: 1 admin, {len(sellers)} sellers, '
            f'{len(operators)} operators, {len(drivers)} drivers'
        )
        return {'admin': admin, 'sellers': sellers, 'operators': operators, 'drivers': drivers}

    def _create_threads(self, products, sellers):
        threads = []
        for index, product in enumerate(products[:6]):
            seller = sellers[index % len(sellers)]
            ceiling = min(product.return_price, product.price)
            thread, _ = Thread.objects.get_or_create(
                name=f'{product.name} — {seller.first_name}',
                product=product,
                user=seller,
                defaults={
                    'discount': (ceiling // 2),
                    'visit_count': random.randint(20, 400),
                },
            )
            threads.append(thread)
        self.stdout.write(f'  Threads: {len(threads)}')
        return threads

    def _create_orders(self, products, threads, users, districts):
        if Order.objects.exists():
            self.stdout.write('  Orders: skipped (table not empty — rerun with --flush)')
            return

        now = timezone.now()
        created = 0
        for index in range(24):
            status = STATUS_MIX[index % len(STATUS_MIX)]
            thread = threads[index % len(threads)] if index % 3 else None
            product = thread.product if thread else products[index % len(products)]
            customer_name, customer_phone = CUSTOMERS[index % len(CUSTOMERS)]

            assigned_operator = None
            assigned_driver = None
            taken_at = None
            delivered_at = None

            if status != Order.OrderStatus.NEW:
                assigned_operator = users['operators'][index % len(users['operators'])]
                taken_at = now - timezone.timedelta(days=index % 7, hours=index % 5)
            if status in {
                Order.OrderStatus.SHIPPING,
                Order.OrderStatus.DELIVERED,
                Order.OrderStatus.RETURNED,
            }:
                assigned_driver = users['drivers'][index % len(users['drivers'])]
            if status == Order.OrderStatus.DELIVERED:
                delivered_at = now - timezone.timedelta(days=index % 5)

            order = Order.objects.create(
                product=product,
                customer_name=customer_name,
                phone=customer_phone,
                quantity=random.randint(1, 3),
                status=status,
                user=thread.user if thread else None,
                thread=thread,
                operator=assigned_operator,
                driver=assigned_driver,
                taken_at=taken_at,
                delivered_at=delivered_at,
                district=districts[index % len(districts)],
                address=f'{index + 1}-uy, Navoiy kochasi',
            )
            created += 1

            if status == Order.OrderStatus.DELIVERED and index % 2 == 0:
                Survey.objects.create(
                    order=order,
                    operator=assigned_operator,
                    comment='Mijoz yetkazib berish sifatidan mamnun.',
                )
        self.stdout.write(f'  Orders: {created} (with surveys on delivered ones)')

    def _create_payments(self, sellers):
        created = 0
        for index, seller in enumerate(sellers):
            _, was_created = Payment.objects.get_or_create(
                user=seller,
                status=Payment.Status.PAID,
                defaults={
                    'card_number': f'860012345678{index:04d}'[:16],
                    'amount': Decimal('150000'),
                },
            )
            created += int(was_created)
        self.stdout.write(f'  Payments: {created}')

    def _report(self):
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Demo data ready. Sign in with:'))
        rows = [
            ('Admin / superuser', '+998900000000'),
            ('Seller (cabinet)', '+998901234567'),
            ('Operator', '+998903456789'),
            ('Driver', '+998905678901'),
        ]
        width = max(len(role) for role, _ in rows)
        for role, phone in rows:
            self.stdout.write(f'  {role.ljust(width)}  {phone}  /  {DEMO_PASSWORD}')
        self.stdout.write('')
