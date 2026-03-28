import random

from game_models import Card


def draw_random_card() -> Card:
    deck = [
        Card("Force 50N", "force", 1, force=50, description="A light shove. Lower impact, high dodge risk."),
        Card("Force 75N", "force", 2, force=75, description="A balanced push with steady control."),
        Card("Force 100N", "force", 3, force=100, description="A heavy shove that threatens big movement."),
        Card("Force 125N", "force", 4, force=125, description="Maximum push. Hardest to dodge cleanly."),
        Card("Dodge", "dodge", 3, description="Brace to evade the next shove. Bigger attacks are harder to avoid."),
        Card("Conservation", "conservation", 1, description="Steal 3 energy now. The target regains 3 energy in 3 turns."),
        Card("Smooth", "smooth", 1, description="Reduce stage friction by 0.05."),
        Card("Rough", "rough", 1, description="Increase stage friction by 0.10."),
    ]
    weights = [22, 12, 8, 2, 10, 2, 8, 8]
    return random.choices(deck, weights=weights, k=1)[0]
