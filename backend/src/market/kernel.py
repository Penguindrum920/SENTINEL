"""Discrete Event Simulation Kernel for scheduling market events."""

import heapq
from enum import Enum, auto
from typing import Any, Callable, List
from dataclasses import dataclass, field

class EventType(Enum):
    WAKEUP = auto()           # An agent evaluates the market
    ORDER_ARRIVAL = auto()    # An order reaches the exchange
    CANCEL_ARRIVAL = auto()   # A cancel request reaches the exchange
    MARKET_DATA = auto()      # Exchange broadcasts data to agents

@dataclass(order=True)
class Event:
    timestamp: float
    event_id: int
    event_type: EventType = field(compare=False)
    callback: Callable = field(compare=False)
    data: Any = field(compare=False, default=None)

class EventKernel:
    """A priority queue-based discrete event scheduler."""
    def __init__(self):
        self.queue: List[Event] = []
        self.current_time: float = 0.0
        self._event_counter: int = 0
        
    def schedule(self, delay: float, event_type: EventType, callback: Callable, data: Any = None) -> int:
        """Schedules an event to occur `delay` seconds into the future."""
        self._event_counter += 1
        trigger_time = self.current_time + delay
        event = Event(trigger_time, self._event_counter, event_type, callback, data)
        heapq.heappush(self.queue, event)
        return self._event_counter

    def run_until(self, target_time: float):
        """Processes all events in the queue up to `target_time`."""
        while self.queue and self.queue[0].timestamp <= target_time:
            event = heapq.heappop(self.queue)
            self.current_time = event.timestamp
            event.callback(event.data)
        
        # Advance clock to target_time if no more events exist before it
        self.current_time = max(self.current_time, target_time)
        
    def clear(self):
        """Resets the kernel."""
        self.queue.clear()
        self.current_time = 0.0
        self._event_counter = 0
