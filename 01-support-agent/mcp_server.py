"""Sarathi v2: the four support tools as an MCP server.

Lesson 20. Claude Code starts this server from the .mcp.json file
in the repo root. Every description has four parts (lesson 15),
and every failure is a structured error (lesson 16).

    uv run python 01-support-agent/mcp_server.py   (stdio)

Fake data only (tools.py). No real money moves.
Switches, all optional:
  SARATHI_STORE_KEY=any-value   lets process_refund run
  SARATHI_FLAKY_ORDERS=1        first lookup of each order
                                times out, the retry works
"""
import functools
import json
import os
import re

from mcp.server import MCPServer
from mcp.types import CallToolResult, TextContent

import tools

REFUND_LIMIT = 500
ORDER_ID = re.compile(r"^O-\d{4}$")
STATUS = {1: "placed", 2: "shipped", 3: "delivered",
          4: "returned"}

verified = set()  # customer ids get_customer has verified
lookups = {}      # order id -> lookups so far (flaky mode)

server = MCPServer("sarathi")


class Failure(Exception):
    """A failure we saw coming, with its structured error."""
    def __init__(self, error):
        super().__init__(error["message"])
        self.error = error


def fail(category, message, retryable=False, customer=None):
    error = {"errorCategory": category,
             "isRetryable": retryable,
             "message": message}
    if customer:
        error["customerMessage"] = customer
    raise Failure(error)


def store_tool(description):
    """Register a tool. A Failure goes back as isError true,
    with the structured error as the text the agent reads."""
    def register(fn):
        @functools.wraps(fn)
        def run(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Failure as f:
                text = json.dumps(f.error)
                return CallToolResult(
                    content=[TextContent(type="text", text=text)],
                    is_error=True)
        return server.tool(description=description)(run)
    return register


def reset():
    verified.clear()
    lookups.clear()
    tools.reset()


GET_CUSTOMER = (
    "Find and verify a customer by email address. "
    "Input: one email, like asha@example.com. "
    "Use it first in any chat about a refund or an account, "
    "for example 'I am Asha, asha@example.com'. "
    "If the customer gives only an order id, use lookup_order "
    "instead. Returns found true with customer_id and name, "
    "or found false when no customer has that email, which "
    "is not an error: ask the customer to check the address.")


@store_tool(GET_CUSTOMER)
def get_customer(email: str) -> dict:
    email = email.strip().lower()
    if "@" not in email:
        fail("validation", f"'{email}' is not an email address.")
    customer = tools.CUSTOMERS.get(email)
    if customer is None:
        return {"found": False, "email": email}
    verified.add(customer["customer_id"])
    return {"found": True, "verified": True, **customer}


LOOKUP_ORDER = (
    "Look up one order by its order id. Input: an id like "
    "O-5001, the letter O, a dash and four digits. Use it for "
    "questions about an order: where it is, what it cost, "
    "when it shipped, for example 'where is my order O-5001?'. "
    "If the customer gives an email and no order id, call "
    "get_customer first. Never use it to find a customer. "
    "Returns found true with item, amount, date and status, "
    "or found false when the order does not exist, which is "
    "not an error: ask the customer to check the number.")


@store_tool(LOOKUP_ORDER)
def lookup_order(order_id: str) -> dict:
    order_id = order_id.strip().upper()
    if not ORDER_ID.match(order_id):
        fail("validation",
             f"'{order_id}' is not an order id. Order ids look "
             "like O-5001.")
    if os.environ.get("SARATHI_FLAKY_ORDERS") == "1":
        lookups[order_id] = lookups.get(order_id, 0) + 1
        if lookups[order_id] == 1:
            fail("transient", "The order system did not answer "
                 "in 5 seconds. Try again.", retryable=True)
    order = tools.ORDERS.get(order_id)
    if order is None:
        return {"found": False, "order_id": order_id}
    return {"found": True, "order_id": order_id,
            "customer_id": order["customer_id"],
            "item": order["item"], "amount": order["amount"],
            "status": STATUS[order["status"]]}


PROCESS_REFUND = (
    "Refund one order, in dollars, to the card it was paid "
    "with. Input: the customer_id from get_customer, the "
    "order id and the amount. Call get_customer first: an "
    "unverified customer is refused. Refunds over 500 dollars "
    "are refused too; use escalate_to_human for those. Never "
    "use it for store credit or to check an order. Returns "
    "refund_id and status issued.")


@store_tool(PROCESS_REFUND)
def process_refund(customer_id: str, order_id: str,
                   amount: float) -> dict:
    if not os.environ.get("SARATHI_STORE_KEY"):
        fail("permission", "This server has no store key, so it "
             "cannot issue refunds. Set SARATHI_STORE_KEY.")
    order = tools.ORDERS.get(order_id)
    if order is None or order["customer_id"] != customer_id:
        fail("validation", f"Order {order_id} does not belong "
             f"to customer {customer_id}.")
    if not 0 < amount <= order["amount"]:
        fail("validation", f"The amount must be more than 0 and "
             f"at most {order['amount']:.2f}.")
    if customer_id not in verified:
        fail("business", "The customer is not verified. Call "
             "get_customer first.")
    if amount > REFUND_LIMIT:
        fail("business", f"Refunds over {REFUND_LIMIT} dollars "
             "need a person. Call escalate_to_human.",
             customer="Refunds over 500 dollars need a person "
             "to approve them. I have passed your case to our "
             "team, and they will reply within one working day.")
    return tools.process_refund(customer_id, order_id, amount)


ESCALATE = (
    "Hand the case to a human agent. Use it for refunds over "
    "500 dollars, or when the customer asks for a person. The "
    "human cannot see this chat, so every field must stand on "
    "its own: root_cause in one sentence, the refund_amount "
    "(0 if none) and the recommended_action. Returns a "
    "ticket id.")


@store_tool(ESCALATE)
def escalate_to_human(customer_id: str, root_cause: str,
                      refund_amount: float,
                      recommended_action: str) -> dict:
    if not root_cause.strip() or not recommended_action.strip():
        fail("validation", "root_cause and recommended_action "
             "must not be empty.")
    return tools.escalate_to_human(customer_id, root_cause,
                                   refund_amount,
                                   recommended_action)


if __name__ == "__main__":
    server.run("stdio")
