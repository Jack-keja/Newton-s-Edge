from dataclasses import dataclass, field
from typing import List

from game_constants import START_ENERGY


@dataclass
class Card:
    name: str
    kind: str
    energy_cost: int
    force: float = 0.0
    description: str = ""


@dataclass
class PendingRestore:
    rounds_left: int
    energy: int


@dataclass
class Player:
    name: str
    position: float
    energy: int = START_ENERGY
    hand: List[Card] = field(default_factory=list)
    dodge_ready: bool = False
    pending_restores: List[PendingRestore] = field(default_factory=list)
    has_started_turn: bool = False
