"""Money in and money out. Nothing here touches a real card."""
from .orders import get_order

LEDGER = []


def charge_card(order_id):
    order = get_order(order_id)
    LEDGER.append(("charge", order_id, order["amount"]))
    return {"charged": order["amount"]}


def refund_order(order_id, amount):
    order = get_order(order_id)
    if order is None:
        raise ValueError(f"No order {order_id}")
    if order["refunded"] + amount > order["amount"]:
        raise ValueError("Refund is more than was paid")
    order["refunded"] += amount
    LEDGER.append(("refund", order_id, amount))
    return {"refunded": amount}
