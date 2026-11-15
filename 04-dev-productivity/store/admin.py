"""Tools for the finance team."""
from . import api
from .payments import LEDGER


def cancel_and_refund(order_id):
    order = api.find_order(order_id)
    order["status"] = "cancelled"
    return api.issue_refund(order_id, order["amount"])


def ledger_total():
    return sum(a if kind == "charge" else -a
               for kind, _, a in LEDGER)
