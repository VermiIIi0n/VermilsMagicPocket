"""A Tiny Event Hook Framework"""
from __future__ import annotations
from typing import Iterable, Any, Callable, TypeVar, Mapping
from ..collections import StrChain
from .actionchain import *


__all__ = ("EventHook", "EventHint")
ActionVar = TypeVar("ActionVar", bound=Callable)


class EventHook(dict[str, BaseActionChain]):
    """
    # Event Hook Class
    Binds events to action chains.
    """

    def __init__(self, chain: Mapping[str, Iterable[ActionVar]] | None = None):
        dict.__init__(self)
        if chain is not None:
            chain = dict(chain)
            for event, actions in chain.items():
                if isinstance(actions, ActionChain):
                    self[event] = type(actions)(actions)
                else:
                    self[event] = ActionChain[ActionVar](actions)

        self._on = EventHint(self)

    def hook(self, event: str, hook: BaseActionChain, force: bool = False) -> None:
        """Hook an event, equivalent to `self[event] = hook`"""
        if not force and event in self:
            raise ValueError(f"Event '{event}' already exists")
        self[event] = hook

    def unhook(self, event: str) -> BaseActionChain:
        """Unhook an event, equivalent to `del self[event]` or `pop()`"""
        return self.pop(event)

    def clear_actions(self):
        """Clear all actions from all events, but keep the events."""
        for event in self:
            self[event].clear()

    def emit(self, event: str, *args: Any, **kw: Any) -> tuple | Any:
        """Trigger an event"""
        if event not in self:
            raise ValueError(f"Event '{event}' not found, add it first")
        return self[event].trigger(event, *args, **kw)

    async def aemit(self, event: str, *args: Any, **kw: Any) -> tuple | Any:
        """Trigger an event, asynchronously"""
        if event not in self:
            raise ValueError(f"Event '{event}' not found, add it first")
        return await self[event].atrigger(event, *args, **kw)

    @property
    def events(self) -> tuple[str, ...]:
        return tuple(self.keys())

    @property
    def on(self) -> EventHint:
        return self._on

    def __getitem__(self, event: str) -> BaseActionChain:
        if event not in self:
            raise KeyError(f"Event '{event}' not found, add it first")
        return super().__getitem__(event)


class EventHint:
    """# Event Hint
    * This class is used to hint the event name to the event hook.
    * It is also used to prevent typos in the event name.
    * Inherit this class and add the event names as class attributes."""

    def __init__(self, event_hook: EventHook = None, strchain: StrChain = None):
        if strchain is None:
            if event_hook is None:
                raise ValueError(
                    "Either event_hook or strchain must be provided")

            def callback(event: StrChain, action: ActionVar) -> ActionVar:
                event_hook[str(event)].append(action)  # type: ignore
                return action
            self._chain = StrChain(joint='.', callback=callback)

        else:
            self._chain = strchain

    def __call__(self, *args, **kwargs):
        return self._chain(*args, **kwargs)

    def __getattribute__(self, event: str) -> EventHint:
        if event.startswith("_"):
            return super().__getattribute__(event)
        return EventHint(strchain=self._chain[event])
