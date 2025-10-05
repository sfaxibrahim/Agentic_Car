"""
Callback handlers for streaming responses
"""
import queue
from langchain.callbacks.base import BaseCallbackHandler


class QueueCallback(BaseCallbackHandler):
    """
    Callback handler that puts tokens into a queue for streaming responses.
    Only starts collecting after 'Final Answer:' is detected.
    """
    
    def __init__(self, q: queue.Queue):
        self.q = q
        self.collecting = False
        self.buffer = ""

    def on_llm_new_token(self, token: str, **kwargs):
        """Called when a new token is generated"""
        self.buffer += token

        if not self.collecting and "Final Answer:" in self.buffer:
            self.collecting = True
            token = self.buffer.split("Final Answer:", 1)[1]
            self.q.put(token)
        elif self.collecting:
            self.q.put(token)

    def on_chain_end(self, outputs, **kwargs):
        """Called when the chain ends - signal completion"""
        self.q.put(None)