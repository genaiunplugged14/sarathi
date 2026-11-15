"""Shipping labels and tracking."""
from .orders import get_order


def ship(order_id, carrier="parcel-post"):
    order = get_order(order_id)
    order["status"] = "shipped"
    order["carrier"] = carrier
    return {"tracking": f"{carrier}-{order_id}"}
