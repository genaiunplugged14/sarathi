import unittest

from store import orders, returns


class Returns(unittest.TestCase):
    def setUp(self):
        orders.ORDERS.clear()
        orders.place_order("O-2", "C-1", "P-200")

    def test_an_opened_item_loses_the_restock_fee(self):
        self.assertEqual(returns.accept_return("O-2", True),
                         {"refunded": 576.0})
