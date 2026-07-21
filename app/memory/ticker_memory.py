"""Per-ticker cached research memory.

Status: not implemented — scaffold only.
"""

from __future__ import annotations


class TickerMemory:
    def get(self, *args, **kwargs):
        raise NotImplementedError("ticker_memory is not implemented yet")

    def set(self, *args, **kwargs):
        raise NotImplementedError("ticker_memory is not implemented yet")
