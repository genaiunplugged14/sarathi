"""Products and prices."""

PRODUCTS = {
    "P-100": {"name": "Wireless headphones", "price": 89.00},
    "P-200": {"name": "27 inch monitor", "price": 640.00},
    "P-300": {"name": "USB-C cable", "price": 12.00},
}


def price_of(product_id):
    return PRODUCTS[product_id]["price"]
