from __future__ import annotations

from pydantic import BaseModel, Field
from .actionchain import ActionChain, ActionCentipede

__all__ = ("EventGroup", "ChainField", "CentipedeField")

ChainField = Field(default_factory=ActionChain)
CentipedeField = Field(default_factory=ActionCentipede)

class EventGroup(BaseModel):
    """
    # Typed Event Group Class

    Must be subclassed to define the event types.
    """


    class Config:
        arbitrary_types_allowed = True