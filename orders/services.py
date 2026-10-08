"""Which status an operator may move an order to, and the stock each change moves.

Stock is taken from the product when an order is placed (catalog.views) and must come
back exactly once if the order is cancelled or returned. Everything that changes an
order's status or quantity on the operator side goes through apply_operator_change(),
which locks the order row first so two submits cannot both return the stock.
"""
from django.db import transaction
from django.db.models import F

from catalog.models import Product
from orders.models import Order

Status = Order.OrderStatus

# Where an operator may move an order from each status. Staying put is always allowed,
# so editing only the address or the comment works in any status.
OPERATOR_TRANSITIONS = {
    Status.NEW: {Status.PACKAGING, Status.HOLD, Status.PICKUP_LATER, Status.CANCELLED},
    Status.HOLD: {Status.PACKAGING, Status.PICKUP_LATER, Status.CANCELLED},
    # The customer collects it in person, so there is no driver to confirm delivery.
    Status.PICKUP_LATER: {Status.PACKAGING, Status.HOLD, Status.DELIVERED, Status.CANCELLED},
    Status.PACKAGING: {Status.SHIPPING, Status.HOLD, Status.CANCELLED},
    # Only the driver who took it marks a shipped order delivered (driver_app).
    Status.SHIPPING: {Status.RETURNED},
    Status.DELIVERED: {Status.RETURNED, Status.ARCHIVE},
    Status.RETURNED: {Status.ARCHIVE},
    Status.CANCELLED: {Status.ARCHIVE},
    Status.ARCHIVE: set(),
}

# Entering one of these puts the order's items back in stock.
RETURNS_STOCK = {Status.CANCELLED, Status.RETURNED}

# The items are still in the warehouse, so the quantity can change.
QUANTITY_EDITABLE = {Status.NEW, Status.HOLD, Status.PICKUP_LATER, Status.PACKAGING}


class OrderChangeError(Exception):
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
        self.message = message


def allowed_statuses(order):
    return {order.status} | OPERATOR_TRANSITIONS[order.status]


def _label(status):
    return Status(status).label


@transaction.atomic
def apply_operator_change(order_id, *, status, quantity):
    """Check an operator's edit against the rules and move stock to match.

    Call inside the view's transaction, before saving the order. Reads the order's
    current status and quantity from the database under a row lock: a ModelForm has
    already copied the submitted values onto its instance by the time it validates.
    """
    order = Order.objects.select_for_update().get(pk=order_id)
    old_status, old_quantity = order.status, order.quantity

    if status != old_status and status not in OPERATOR_TRANSITIONS[old_status]:
        raise OrderChangeError(
            'status',
            f"«{_label(old_status)}» holatidan «{_label(status)}» holatiga o'tib bo'lmaydi.",
        )

    if quantity != old_quantity:
        if old_status not in QUANTITY_EDITABLE:
            raise OrderChangeError(
                'quantity', f"«{_label(old_status)}» holatidagi buyurtma miqdorini o'zgartirib bo'lmaydi.",
            )
        extra = quantity - old_quantity
        if extra > 0:
            taken = (Product.objects
                     .filter(pk=order.product_id, stock__gte=extra)
                     .update(stock=F('stock') - extra))
            if not taken:
                raise OrderChangeError('quantity', "Omborda yetarli mahsulot qolmadi.")
        else:
            Product.objects.filter(pk=order.product_id).update(stock=F('stock') - extra)

    if status in RETURNS_STOCK and old_status not in RETURNS_STOCK:
        Product.objects.filter(pk=order.product_id).update(stock=F('stock') + quantity)
