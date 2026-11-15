"""What a support agent can do for a customer."""
from .api import find_order, issue_refund


def goodwill_credit(order_id, amount):
    """A partial refund when a delivery was late."""
    if amount > 20:
        raise ValueError("Goodwill is 20 dollars at most")
    return issue_refund(order_id, amount)


def order_summary(order_id):
    order = find_order(order_id)
    return f"{order_id}: {order['status']}, {order['amount']}"
