"""Orders, kept in memory."""
from .catalog import price_of

ORDERS = {}


def place_order(order_id, customer_id, product_id):
    ORDERS[order_id] = {"customer_id": customer_id,
                        "product_id": product_id,
                        "amount": price_of(product_id),
                        "status": "placed",
                        "refunded": 0.0}
    return ORDERS[order_id]


def get_order(order_id):
    return ORDERS.get(order_id)
