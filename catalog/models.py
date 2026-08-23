from django.core.exceptions import ValidationError
from django.db.models import Model, CharField, SlugField, PositiveIntegerField, CASCADE, ForeignKey, DecimalField, \
    TextField, BooleanField, SmallIntegerField, ImageField, DateTimeField
from django.utils.text import slugify


class BaseSlugModel(Model):
    slug = SlugField(unique=True, blank=True)
    name = CharField(max_length=100)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        abstract = True


class Category(BaseSlugModel):
    order = PositiveIntegerField(default=0)
    image = ImageField(upload_to='categories')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

class Product(BaseSlugModel):
    category = ForeignKey('catalog.Category', on_delete=CASCADE, related_name='products')
    price = DecimalField(max_digits=12, decimal_places=0, default=0)
    description = TextField()
    is_bestseller = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    stock = SmallIntegerField()
    return_price = DecimalField(max_digits=12, decimal_places=0, default=0)

    @property
    def thumbnail(self):
        images = self.images.all()
        return images[0] if images else None

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class ProductImage(Model):
    product = ForeignKey('catalog.Product', on_delete=CASCADE, related_name='images')
    image = ImageField(upload_to='products/')
    order = PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']


class Thread(Model):
    name = CharField(max_length=255)
    product = ForeignKey('catalog.Product', on_delete=CASCADE, related_name='threads')
    user = ForeignKey('accounts.User', on_delete=CASCADE, related_name='threads')
    discount = DecimalField(max_digits=12, decimal_places=0)
    visit_count = PositiveIntegerField(default=0)

    def clean(self):
        super().clean()
        if self.product_id is None or self.discount is None:
            return
        if self.discount < 0:
            raise ValidationError({'discount': "Chegirma manfiy bo'lishi mumkin emas"})
        ceiling = min(self.product.return_price, self.product.price)
        if self.discount > ceiling:
            raise ValidationError({
                'discount': f"Chegirma {ceiling} so'mdan oshmasligi kerak"
            })

    def __str__(self):
        return self.name
    
