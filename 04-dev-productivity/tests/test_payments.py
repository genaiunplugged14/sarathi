import unittest

from store import orders, payments


class Payments(unittest.TestCase):
    def setUp(self):
        orders.ORDERS.clear()
        orders.place_order("O-1", "C-1", "P-100")

    def test_refund_order_up_to_the_price(self):
        self.assertEqual(payments.refund_order("O-1", 89.0),
                         {"refunded": 89.0})

    def test_refund_order_refuses_more_than_paid(self):
        with self.assertRaises(ValueError):
            payments.refund_order("O-1", 90.0)
