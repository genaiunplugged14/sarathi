"""Scenario 1 tools, backed by fake data. No real money moves."""

CUSTOMERS = {
    "asha@example.com": {
        "customer_id": "C-1001",
        "name": "Asha Rao",
        "member_since": "2024-03-14T09:30:00Z",
    },
}

ORDERS = {
    "O-5001": {
        "customer_id": "C-1001",
        "item": "Wireless headphones",
        "amount": 89.00,
        "placed_at": 1789948800,
        "status": 3,
    },
    "O-5002": {
        "customer_id": "C-1001",
        "item": "27 inch monitor",
        "amount": 640.00,
        "placed_at": 1790553600,
        "status": 3,
    },
}

REFUNDS = []   # every refund lands here and goes nowhere else
HANDOFFS = []  # every escalation lands here


def get_customer(email):
    customer = CUSTOMERS.get(email.strip().lower())
    if customer is None:
        return {"error": "No customer with that email."}
    return {**customer, "verified": True}


def lookup_order(order_id):
    order = ORDERS.get(order_id)
    if order is None:
        return {"error": f"No order {order_id}."}
    return {"order_id": order_id, **order}


def process_refund(customer_id, order_id, amount):
    REFUNDS.append({"customer_id": customer_id,
                    "order_id": order_id, "amount": amount})
    return {"refund_id": f"R-{len(REFUNDS):04d}",
            "status": "issued", "amount": amount}


def escalate_to_human(customer_id, root_cause, refund_amount,
                      recommended_action):
    HANDOFFS.append({"customer_id": customer_id,
                     "root_cause": root_cause,
                     "refund_amount": refund_amount,
                     "recommended_action": recommended_action})
    return {"ticket": f"H-{len(HANDOFFS):04d}",
            "status": "queued for a human"}


def reset():
    REFUNDS.clear()
    HANDOFFS.clear()


def _schema(properties, required):
    return {"type": "object", "properties": properties,
            "required": required}


TEXT = {"type": "string"}
MONEY = {"type": "number"}

TOOLS = [
    {"name": "get_customer",
     "description": "Find and verify a customer by email address. "
                    "Returns customer_id and verified. Call this "
                    "before any refund.",
     "input_schema": _schema({"email": TEXT}, ["email"])},
    {"name": "lookup_order",
     "description": "Look up one order by its id, like O-5001. "
                    "Returns the item, amount, date and status.",
     "input_schema": _schema({"order_id": TEXT}, ["order_id"])},
    {"name": "process_refund",
     "description": "Refund an order to a verified customer.",
     "input_schema": _schema(
         {"customer_id": TEXT, "order_id": TEXT, "amount": MONEY},
         ["customer_id", "order_id", "amount"])},
    {"name": "escalate_to_human",
     "description": "Hand the case to a human agent. The human "
                    "cannot see this chat, so the summary must "
                    "stand on its own.",
     "input_schema": _schema(
         {"customer_id": TEXT, "root_cause": TEXT,
          "refund_amount": MONEY, "recommended_action": TEXT},
         ["customer_id", "root_cause", "refund_amount",
          "recommended_action"])},
]

FUNCTIONS = {"get_customer": get_customer,
             "lookup_order": lookup_order,
             "process_refund": process_refund,
             "escalate_to_human": escalate_to_human}


def run_tool(name, args):
    return FUNCTIONS[name](**args)
