"""A stand-in for the Claude API that replays scripted replies.

Nothing here calls Claude. Each reply has the same shape the
Messages API returns (stop_reason, content blocks, usage), so a
loop cannot tell the difference. The scripts are written by
hand to show one behaviour the same way every time.
"""
from types import SimpleNamespace as NS

ASK = ("Hi, I am Asha Rao, asha@example.com. My headphones from "
       "order O-5001 arrived broken. Please refund me.")


def text(words):
    return NS(type="text", text=words)


def tool(tool_id, name, **args):
    return NS(type="tool_use", id=tool_id, name=name, input=args)


def reply(stop_reason, *content):
    return NS(stop_reason=stop_reason, content=list(content),
              usage=NS(input_tokens=0, output_tokens=0))


class ReplayClient:
    """Answers client.messages.create() from a list of replies.

    With repeat=True the last reply is sent again forever, the
    way a model that has finished keeps giving the same answer.
    """

    def __init__(self, script, repeat=False):
        self.script = list(script)
        self.repeat = repeat
        self.calls = 0
        self.messages = self

    def create(self, **request):
        self.calls += 1
        self.last_request = request
        last = len(self.script) == 1
        if self.script and not (last and self.repeat):
            return self.script.pop(0)
        if self.script:
            return self.script[0]
        raise RuntimeError("The replay script ran out of replies")


# The happy path: verify, look up, refund, answer.
REFUND = [
    reply("tool_use",
          text("Let me look up your account first."),
          tool("t1", "get_customer", email="asha@example.com")),
    reply("tool_use",
          text("I am done with the account check. "
               "Now the order."),
          tool("t2", "lookup_order", order_id="O-5001")),
    reply("tool_use",
          tool("t3", "process_refund", customer_id="C-1001",
               order_id="O-5001", amount=89.0)),
    reply("end_turn",
          text("Your refund of 89 dollars for the headphones "
               "is issued. The refund id is R-0001.")),
]

# The model skips verification, the way sample Question 1 says.
SKIP_VERIFY = [
    reply("tool_use",
          tool("t1", "lookup_order", order_id="O-5001")),
    reply("tool_use",
          tool("t2", "process_refund", customer_id="C-1001",
               order_id="O-5001", amount=89.0)),
    reply("tool_use",
          tool("t3", "get_customer", email="asha@example.com")),
    reply("tool_use",
          tool("t4", "process_refund", customer_id="C-1001",
               order_id="O-5001", amount=89.0)),
    reply("end_turn",
          text("Your refund of 89 dollars is issued.")),
]

# A 640 dollar refund, over the 500 dollar line.
OVER_LIMIT = [
    reply("tool_use",
          tool("t1", "get_customer", email="asha@example.com")),
    reply("tool_use",
          tool("t2", "lookup_order", order_id="O-5002")),
    reply("tool_use",
          tool("t3", "process_refund", customer_id="C-1001",
               order_id="O-5002", amount=640.0)),
    reply("tool_use",
          tool("t4", "escalate_to_human", customer_id="C-1001",
               root_cause="Monitor from O-5002 arrived broken. "
                          "Customer verified, order delivered.",
               refund_amount=640.0,
               recommended_action="Approve the full refund of "
                                  "640 dollars for O-5002.")),
    reply("end_turn",
          text("A teammate will review your 640 dollar refund. "
               "Your ticket is H-0001.")),
]
