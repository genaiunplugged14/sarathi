import unittest

from store import admin, orders, support_desk


class SupportDesk(unittest.TestCase):
    def setUp(self):
        orders.ORDERS.clear()
        orders.place_order("O-3", "C-2", "P-300")

    def test_goodwill_is_capped(self):
        with self.assertRaises(ValueError):
            support_desk.goodwill_credit("O-3", 25)

    def test_cancel_refunds_in_full(self):
        self.assertEqual(admin.cancel_and_refund("O-3"),
                         {"refunded": 12.0})
