"""Returns: an item comes back, the money goes back."""
from .orders import get_order
from .payments import refund_order

RESTOCK_FEE = 0.10  # opened items lose 10 percent


def accept_return(order_id, opened):
    order = get_order(order_id)
    amount = order["amount"]
    if opened:
        amount = round(amount * (1 - RESTOCK_FEE), 2)
    order["status"] = "returned"
    return refund_order(order_id, amount)
