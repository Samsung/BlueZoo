# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

from pyventus.events import AsyncIOEventEmitter, EventLinker, EventSubscriber


class Subscription:
    """Convenience wrapper for EventSubscriber."""

    def __init__(self, subscriber: EventSubscriber | None = None):
        self.subscriber = subscriber

    def unsubscribe(self):
        if self.subscriber:
            self.subscriber.unsubscribe()
            self.subscriber = None


emitter = AsyncIOEventEmitter()


def emit(event, **kwargs):
    return emitter.emit(event, **kwargs)


def subscribe(event, callback, once: bool = False):
    return EventLinker.subscribe(event, event_callback=callback, once=once)
