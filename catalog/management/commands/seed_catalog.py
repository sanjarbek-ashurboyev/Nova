"""Replace the catalog with a realistic demo storefront.

    python manage.py seed_catalog --flush

Categories and products are defined below; their artwork lives in
``media/demo/`` as real, Creative-Commons licensed photographs (see
``media/demo/CREDITS.md`` for the per-file attribution).  Because the files are
checked into the repository the command needs no network access — anyone who
clones Nova gets the same storefront.

The same catalog is also shipped as a fixture, which is the quicker way to get it
back once you have it::

    python manage.py loaddata demo_catalog

Regenerate that fixture after editing ``CATEGORIES``/``PRODUCTS`` here::

    python manage.py seed_catalog --flush
    python manage.py dumpdata catalog.Category catalog.Product catalog.ProductImage \\
        --indent 2 --output catalog/fixtures/demo_catalog.json
"""

import posixpath
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from catalog.models import Category, Product, ProductImage, Thread
from orders.models import Order

DEMO_ROOT = Path(settings.MEDIA_ROOT) / 'demo'
MAX_PRODUCT_PHOTOS = 2

# (name, ordering, english search term used to source the photo)
CATEGORIES = [
    ('Kitoblar', 'stack of books'),
    ('Elektronika', 'consumer electronics gadgets'),
    ('Sport va faollik', 'fitness equipment'),
    ("Uy-ro'zg'or", 'modern kitchen utensils'),
    ("Go'zallik", 'cosmetics flat lay'),
    ('Bolalar uchun', 'children toys'),
    ("Sovg'alar", 'gift boxes'),
]

# (category, name, price, return_price, stock, bestseller, description, search term)
PRODUCTS = [
    # ---------------------------------------------------------------- Kitoblar
    ('Kitoblar', 'Odatlar kuchi', 89_000, 12_000, 40, True,
     "Kichik odatlarni tizimga solib, katta natijaga erishish haqidagi xalqaro bestseller. "
     "Qattiq muqova, 320 bet.",
     'self help book'),
    ('Kitoblar', "O'tkan kunlar", 65_000, 8_000, 25, True,
     "Abdulla Qodiriyning mumtoz romani — o'zbek adabiyotining ilk romani. "
     "Yumshoq muqova, 380 bet.",
     'vintage antique book'),
    ('Kitoblar', "Biznes kitoblari to'plami", 245_000, 30_000, 15, False,
     "Boshlovchi tadbirkorlar uchun 4 ta kitobdan iborat to'plam: strategiya, moliya, "
     "marketing va boshqaruv.",
     'business books stack'),
    ('Kitoblar', 'Bolalar ertaklari', 55_000, 7_000, 60, False,
     "Rangli illyustratsiyali ertaklar to'plami. Qalin qog'oz, 2 yoshdan yuqori bolalar uchun.",
     'children picture book'),
    ('Kitoblar', 'Charm muqovali kundalik', 79_000, 10_000, 35, False,
     "Sun'iy charm muqovali kundalik, 200 bet, qatorli. Rezinali qulf va lentali xatcho'p bilan.",
     'leather notebook journal'),

    # ------------------------------------------------------------- Elektronika
    ('Elektronika', 'Simsiz quloqchin TWS-9', 249_000, 30_000, 60, True,
     "Bluetooth 5.3, zaryad keysi bilan 24 soatgacha ishlash, shovqinni bostirish funksiyasi.",
     'wireless earbuds'),
    ('Elektronika', 'Power Bank 20000mAh', 179_000, 22_000, 45, False,
     "20000mAh sig'im, 22.5W tez quvvatlash, ikkita USB va bitta USB-C chiqishi.",
     'power bank charger'),
    ('Elektronika', 'Smart Watch S8', 399_000, 45_000, 20, True,
     "1.85\" AMOLED ekran, puls va kislorod o'lchash, 100+ sport rejimi, IP68 himoya.",
     'smartwatch'),
    ('Elektronika', 'Bluetooth kolonka Boom', 219_000, 26_000, 30, False,
     "10W stereo ovoz, IPX7 suvdan himoya, 12 soat uzluksiz musiqa.",
     'bluetooth speaker'),
    ('Elektronika', 'Simsiz sichqoncha Silent', 89_000, 11_000, 55, False,
     "2.4GHz simsiz ulanish, ovozsiz tugmalar, 1600 DPI, AA batareya bilan 12 oy ishlaydi.",
     'wireless computer mouse'),

    # --------------------------------------------------------- Sport va faollik
    ('Sport va faollik', 'Yoga gilamchasi', 129_000, 15_000, 50, False,
     "6 mm qalinlikdagi ikki tomonlama NBR gilamcha, sirpanmaydigan sirt, olib yurish tasmasi bilan.",
     'yoga mat'),
    ('Sport va faollik', "Gantel to'plami 2x5kg", 219_000, 25_000, 20, False,
     "Neopren qoplamali juft gantel, qo'l terlaganda ham sirpanmaydi. Uy sharoiti uchun ideal.",
     'dumbbells'),
    ('Sport va faollik', 'Sport sumkasi Active', 159_000, 18_000, 35, True,
     "Suv o'tkazmaydigan mato, alohida poyabzal bo'limi, 35 litr sig'im.",
     'gym duffel bag'),
    ('Sport va faollik', 'Sport suv shishasi 1L', 69_000, 9_000, 70, False,
     "BPA-siz tritan plastik, o'lchov shkalasi va bir qo'l bilan ochiladigan qopqoq.",
     'sport water bottle'),
    ('Sport va faollik', 'Sakrash arqoni Pro', 49_000, 6_000, 80, False,
     "Podshipnikli tez arqon, uzunligi rostlanadi, hisoblagichi bor.",
     'jump rope skipping'),

    # ----------------------------------------------------------- Uy-ro'zg'or
    ("Uy-ro'zg'or", 'Termos 1.2L', 99_000, 11_000, 45, True,
     "Ikki qavatli po'lat termos, issiqni 12 soat, sovuqni 18 soat saqlaydi.",
     'thermos flask'),
    ("Uy-ro'zg'or", 'Aromadiffuzor Mist', 159_000, 18_000, 30, False,
     "300 ml sig'imli ultratovushli diffuzor, 7 rangli fon yorug'ligi va taymer bilan.",
     'aroma diffuser'),
    ("Uy-ro'zg'or", "Choy servizi 12 predmet", 289_000, 34_000, 18, False,
     "Chinni choy servizi: 6 ta piyola, 6 ta likopcha va choynak. Sovg'abop quti bilan.",
     'porcelain tea set'),
    ("Uy-ro'zg'or", "Oshxona pichoqlari to'plami", 249_000, 28_000, 22, True,
     "Zanglamaydigan po'latdan 5 ta pichoq va yog'och tagligi. Ergonomik dastalar.",
     'kitchen knife set'),
    ("Uy-ro'zg'or", 'Stol chirog\'i LED', 139_000, 16_000, 40, False,
     "3 xil yorug'lik harorati, 10 daraja yorqinlik, USB quvvatlash va telefon tagligi.",
     'desk lamp'),

    # ------------------------------------------------------------- Go'zallik
    ("Go'zallik", 'Yuz uchun namlantiruvchi krem', 119_000, 14_000, 50, True,
     "Gialuron kislotali kunduzgi krem, barcha teri turlari uchun. 50 ml.",
     'face cream jar cosmetic'),
    ("Go'zallik", 'Parfyum Nova Nuit 50ml', 349_000, 40_000, 25, True,
     "Sharqona-gulli parfyum suvi: bergamot, yasmin va sandal daraxti notalari.",
     'perfume bottle'),
    ("Go'zallik", 'Soch quritgich Ion 2200W', 289_000, 33_000, 20, False,
     "Ionli quritgich, 2 tezlik va 3 harorat rejimi, sovuq havo tugmasi.",
     'hair dryer'),
    ("Go'zallik", "Bo'yanish to'plami Basic", 199_000, 23_000, 30, False,
     "Kundalik bo'yanish uchun palitra, 12 ta soya, ikkita lab bo'yog'i va cho'tkalar.",
     'makeup palette'),
    ("Go'zallik", "Tabiiy sovun to'plami", 89_000, 10_000, 60, False,
     "Qo'lda tayyorlangan 4 ta sovun: zaytun, lavanda, asal va ko'mir.",
     'handmade soap bars'),

    # --------------------------------------------------------- Bolalar uchun
    ('Bolalar uchun', "Konstruktor 350 detal", 189_000, 22_000, 35, True,
     "350 ta rangli detal, 3 yoshdan yuqori bolalar uchun. Saqlash qutisi bilan.",
     'building blocks toy'),
    ('Bolalar uchun', "Yumshoq o'yinchoq ayiq", 99_000, 12_000, 45, False,
     "45 sm bo'yli gipoallergen ayiqcha, mashinada yuvish mumkin.",
     'teddy bear'),
    ('Bolalar uchun', 'Rangli qalamlar 36 ta', 59_000, 7_000, 70, False,
     "Yog'och korpusli 36 rangli qalam, sinmaydigan grifel, metall quti bilan.",
     'colored pencils'),
    ('Bolalar uchun', 'Puzzle 500 detal', 79_000, 9_000, 40, False,
     "500 detalli manzarali puzzle, tayyor o'lchami 50x38 sm.",
     'jigsaw puzzle'),
    ('Bolalar uchun', 'Maktab ryukzagi', 179_000, 21_000, 38, True,
     "Ortopedik orqa qismli ryukzak, 3 bo'lim, svetoforda ko'rinadigan aks etuvchi tasmalar.",
     'kids school backpack'),

    # ------------------------------------------------------------- Sovg'alar
    ("Sovg'alar", "Sovg'a to'plami Premium", 269_000, 31_000, 25, True,
     "Bayram uchun tayyor to'plam: shokolad, sham, choy va tabrik kartochkasi.",
     'gift box present'),
    ("Sovg'alar", "Shokolad to'plami", 129_000, 15_000, 55, False,
     "Belgiya shokoladidan 24 dona assorti, sovg'abop qutida.",
     'chocolate box assortment'),
    ("Sovg'alar", 'Gul buketi Fresh', 189_000, 22_000, 20, False,
     "Mavsumiy gullardan yig'ilgan buket, kraft qog'ozda. Toshkent bo'ylab yetkazib beriladi.",
     'flower bouquet'),
    ("Sovg'alar", "Xushbo'y sham to'plami", 109_000, 13_000, 50, False,
     "Soya mumidan 3 ta sham: vanil, sitrus va o'rmon hidi. Har biri 25 soat yonadi.",
     'scented candles'),
    ("Sovg'alar", "Qo'l soati Classic", 459_000, 52_000, 15, True,
     "Zanglamaydigan po'lat korpus, mineral shisha, 3ATM suvdan himoya. Sovg'a qutisi bilan.",
     'wristwatch classic'),
]


def demo_path(*parts):
    """Return the MEDIA_ROOT-relative path of a demo photo, or None if it is missing.

    The images are pointed at in place rather than copied into the ``upload_to``
    directories: they already live inside MEDIA_ROOT, so they are served as-is and
    the same paths survive a ``dumpdata``/``loaddata`` round trip on a fresh clone.
    """
    if not DEMO_ROOT.joinpath(*parts).is_file():
        return None
    return posixpath.join('demo', *parts)


class Command(BaseCommand):
    help = 'Seed the storefront with demo categories and products (real photos from media/demo).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help=(
                'Delete every existing category and product first. Orders point at products '
                'with on_delete=PROTECT, so the orders (and their surveys and threads) are '
                'removed too — otherwise the delete would be refused.'
            ),
        )
        parser.add_argument(
            '--keep-images',
            action='store_true',
            help='Leave products that already have an image untouched.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not DEMO_ROOT.is_dir():
            raise CommandError(
                f'{DEMO_ROOT} not found. The demo photographs ship with the repository; '
                'restore them before running this command.'
            )

        if options['flush']:
            counts = {
                'orders': Order.objects.count(),
                'threads': Thread.objects.count(),
                'products': Product.objects.count(),
                'categories': Category.objects.count(),
            }
            # Order.product is PROTECT, so the orders have to go before the products do.
            Order.objects.all().delete()      # cascades to Survey
            Thread.objects.all().delete()
            ProductImage.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(
                '  Flushed ' + ', '.join(f'{value} {label}' for label, value in counts.items())
            )

        categories = self._create_categories()
        self._create_products(categories, keep_images=options['keep_images'])

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Storefront ready: {Category.objects.count()} categories, '
            f'{Product.objects.count()} products, {ProductImage.objects.count()} photos.'
        ))

    def _create_categories(self):
        categories = {}
        for order, (name, _term) in enumerate(CATEGORIES):
            slug = slugify(name)
            category, created = Category.objects.get_or_create(
                name=name,
                defaults={'order': order, 'slug': slug},
            )
            if category.order != order:
                category.order = order
                category.save(update_fields=['order'])

            path = demo_path('categories', f'{slug}.jpg')
            if path is None:
                self.stderr.write(f'  ! missing demo/categories/{slug}.jpg')
            elif created or not category.image:
                category.image.name = path
                category.save(update_fields=['image'])

            categories[name] = category
        self.stdout.write(f'  Categories: {len(categories)}')
        return categories

    def _create_products(self, categories, keep_images=False):
        photos = 0
        for category_name, name, price, return_price, stock, bestseller, description, _term in PRODUCTS:
            slug = slugify(name)
            product, _created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'category': categories[category_name],
                    'price': Decimal(price),
                    'return_price': Decimal(return_price),
                    'stock': stock,
                    'is_bestseller': bestseller,
                    'description': description,
                },
            )

            if keep_images and product.images.exists():
                continue

            # Keyed on (product, order) so re-running keeps the existing rows — and their
            # primary keys — instead of churning them, which would make demo_catalog.json
            # insert duplicates on top rather than overwrite.
            kept = 0
            for order in range(MAX_PRODUCT_PHOTOS):
                path = demo_path('products', f'{slug}-{order + 1}.jpg')
                if path is None:
                    break
                ProductImage.objects.update_or_create(
                    product=product, order=order, defaults={'image': path},
                )
                kept += 1
                photos += 1
            product.images.filter(order__gte=kept).delete()

            if not product.images.exists():
                self.stderr.write(f'  ! missing demo/products/{slug}-1.jpg')

        self.stdout.write(f'  Products: {len(PRODUCTS)} ({photos} photos)')
