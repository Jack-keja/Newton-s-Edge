import math
import random
from dataclasses import dataclass, field
from typing import List, Optional

import pygame


SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 960
FPS = 60

STAGE_LENGTH = 25.0
START_POSITIONS = [11.0, 15.0]
MAX_ENERGY = 10
START_ENERGY = 5
START_HAND = 4
DRAW_PER_TURN = 2
ENERGY_PER_TURN = 2
MAX_HAND_SIZE = 10
FOLLOW_GAP = 3.0

PLAYER_MASS = 50.0
GRAVITY = 10.0
BASE_FRICTION = 0.2
IMPACT_TIME = 2.0
LINE_MARGIN = 120
DODGE_DURATION = 0.42
DODGE_OFFSET = 58
PUSH_DURATION = 0.22
PUSH_CONTACT_GAP = 1.6

BG_COLOR = (245, 241, 232)
PANEL_COLOR = (255, 252, 246)
TEXT_COLOR = (40, 40, 45)
MUTED_COLOR = (102, 95, 87)
ACCENT_BLUE = (47, 101, 196)
ACCENT_RED = (194, 78, 69)
ACCENT_GREEN = (53, 130, 84)
ACCENT_GOLD = (201, 153, 72)
BG_WASH = (232, 223, 206)
BG_LINE = (225, 216, 200)
SHADOW_COLOR = (196, 184, 164)
CARD_BG = (255, 249, 235)
CARD_BORDER = (138, 121, 102)
CARD_DISABLED = (220, 214, 205)
STAGE_COLOR = (98, 87, 75)
VOID_COLOR = (51, 53, 72)
GLOW_COLOR = (234, 213, 142)

FORCE_SUCCESS = {
    50: 0.65,
    75: 0.45,
    100: 0.25,
    125: 0.10,
}


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


class Button:
    def __init__(self, rect: pygame.Rect, label: str):
        self.rect = rect
        self.label = label

    def draw(self, screen: pygame.Surface, font: pygame.font.Font, enabled: bool) -> None:
        fill = ACCENT_BLUE if enabled else CARD_DISABLED
        pygame.draw.rect(screen, fill, self.rect, border_radius=14)
        pygame.draw.rect(screen, TEXT_COLOR, self.rect, width=2, border_radius=14)
        text = font.render(self.label, True, TEXT_COLOR if enabled else MUTED_COLOR)
        screen.blit(text, text.get_rect(center=self.rect.center))

    def contains(self, pos) -> bool:
        return self.rect.collidepoint(pos)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Physics Card Duel")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("georgia", 30, bold=True)
        self.body_font = pygame.font.SysFont("georgia", 22)
        self.small_font = pygame.font.SysFont("georgia", 18)
        self.tiny_font = pygame.font.SysFont("georgia", 15)

        self.players = [
            Player(name="Player 1", position=START_POSITIONS[0]),
            Player(name="Player 2", position=START_POSITIONS[1]),
        ]
        self.current_player_index = 0
        self.round_number = 1
        self.turn_started = False
        self.turn_phase = "turn_start"
        self.winner: Optional[int] = None
        self.stage_friction = BASE_FRICTION
        self.selected_card_index: Optional[int] = None
        self.effect_used_this_turn = False
        self.conservation_used_this_turn = False
        self.action_used_this_turn = False
        self.animation = None
        self.card_use_animation = None
        self.drag_state = None
        self.messages: List[str] = []
        self.card_rects: List[pygame.Rect] = []
        self.board_rect = pygame.Rect(0, 0, 0, 0)
        self.end_turn_button = Button(pygame.Rect(1040, 680, 200, 58), "End Turn")
        self.reset_button = Button(pygame.Rect(1040, 612, 200, 50), "Restart Match")

        for player in self.players:
            for _ in range(START_HAND):
                player.hand.append(self.random_card())

        self.log("Physics Card Duel begins. Push your rival into the void to win.")
        self.log("Each turn: gain 2 energy, draw 2 cards, then play effects and one action card.")
        self.start_turn(initial=True)

    def random_card(self) -> Card:
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
        weights = [18, 16, 14, 10, 10, 8, 8, 8]
        return random.choices(deck, weights=weights, k=1)[0]

    def log(self, message: str) -> None:
        self.messages.append(message)
        self.messages = self.messages[-8:]

    def current_player(self) -> Player:
        return self.players[self.current_player_index]

    def other_player_index(self) -> int:
        return 1 - self.current_player_index

    def other_player(self) -> Player:
        return self.players[self.other_player_index()]

    def arena_geometry(self, rect: pygame.Rect) -> tuple[tuple[int, int], int]:
        arena_center = (rect.centerx, rect.y + 320)
        arena_radius = min(228, max(170, (rect.height // 2) - 100))
        return arena_center, arena_radius

    def start_turn(self, initial: bool = False) -> None:
        player = self.current_player()
        self.selected_card_index = None
        self.effect_used_this_turn = False
        self.conservation_used_this_turn = False
        self.action_used_this_turn = False
        self.turn_phase = "playing"

        if not player.has_started_turn:
            player.has_started_turn = True
            self.log(f"{player.name} takes an opening turn with {player.energy} energy and {len(player.hand)} cards.")
            return

        if not initial:
            if player.dodge_ready:
                player.dodge_ready = False
                self.log(f"{player.name}'s prepared dodge fades because no shove came last round.")
            gained = min(ENERGY_PER_TURN, MAX_ENERGY - player.energy)
            player.energy += gained
            draws = max(0, min(DRAW_PER_TURN, MAX_HAND_SIZE - len(player.hand)))
            for _ in range(draws):
                player.hand.append(self.random_card())
            self.resolve_delayed_energy(player)
            self.log(f"Round {self.round_number}: {player.name} gains {gained} energy and draws {draws} cards.")

    def resolve_delayed_energy(self, player: Player) -> None:
        updated: List[PendingRestore] = []
        restored = 0
        for entry in player.pending_restores:
            if entry.rounds_left <= 1:
                restored += entry.energy
            else:
                updated.append(PendingRestore(entry.rounds_left - 1, entry.energy))
        player.pending_restores = updated
        if restored:
            previous = player.energy
            player.energy = min(MAX_ENERGY, player.energy + restored)
            actual = player.energy - previous
            self.log(f"{player.name} regains {actual} delayed energy from Conservation of Energy.")

    def can_play(self, player: Player, card: Card) -> bool:
        if self.animation or self.card_use_animation or self.winner is not None or self.turn_phase != "playing":
            return False
        if player.energy < card.energy_cost:
            return False
        if card.kind == "conservation" and self.conservation_used_this_turn:
            return False
        if card.kind in {"force", "dodge"} and self.action_used_this_turn:
            return False
        return True

    def remove_card(self, index: int) -> Card:
        player = self.current_player()
        if index < 0 or index >= len(player.hand):
            raise IndexError("Card index out of range")
        return player.hand.pop(index)

    def play_selected_card(self) -> None:
        if self.selected_card_index is None or self.animation or self.card_use_animation or self.winner is not None:
            return
        self.play_card_by_index(self.selected_card_index)

    def play_card_by_index(self, index: int) -> None:
        if self.animation or self.card_use_animation or self.winner is not None:
            return
        player = self.current_player()
        if index >= len(player.hand):
            self.selected_card_index = None
            return

        card = player.hand[index]
        if not self.can_play(player, card):
            self.log(f"{card.name} cannot be played right now.")
            return

        self.selected_card_index = index
        self.remove_card(index)
        self.selected_card_index = None
        player.energy -= card.energy_cost

        if card.kind == "force":
            self.action_used_this_turn = True
            self.resolve_force_card(card)
        elif card.kind == "dodge":
            self.action_used_this_turn = True
            player.dodge_ready = True
            self.turn_phase = "turn_complete"
            self.log(f"{player.name} prepares a dodge. If no shove comes, it fizzles harmlessly.")
        elif card.kind == "conservation":
            self.conservation_used_this_turn = True
            self.effect_used_this_turn = True
            self.resolve_conservation()
        elif card.kind == "smooth":
            self.effect_used_this_turn = True
            old = self.stage_friction
            self.stage_friction = max(0.0, self.stage_friction - 0.05)
            self.log(f"{player.name} smooths the arena. Friction {old:.2f} -> {self.stage_friction:.2f}.")
        elif card.kind == "rough":
            self.effect_used_this_turn = True
            old = self.stage_friction
            self.stage_friction = min(1.0, self.stage_friction + 0.10)
            self.log(f"{player.name} roughens the arena. Friction {old:.2f} -> {self.stage_friction:.2f}.")

    def resolve_conservation(self) -> None:
        player = self.current_player()
        target = self.other_player()
        stolen = min(3, target.energy)
        target.energy -= stolen
        gained_room = MAX_ENERGY - player.energy
        gained = min(stolen, gained_room)
        player.energy += gained
        target.pending_restores.append(PendingRestore(rounds_left=3, energy=3))
        self.log(
            f"{player.name} steals {stolen} energy from {target.name}. "
            f"{target.name} will recover 3 energy in 3 turns."
        )

    def attack_direction(self, attacker: Player, defender: Player) -> float:
        if math.isclose(attacker.position, defender.position, abs_tol=0.01):
            return 1.0 if self.current_player_index == 0 else -1.0
        return 1.0 if defender.position > attacker.position else -1.0

    def resolve_force_card(self, card: Card) -> None:
        attacker = self.current_player()
        defender = self.other_player()
        direction = self.attack_direction(attacker, defender)
        if direction > 0:
            attacker.position = min(attacker.position if defender.position <= attacker.position else defender.position - PUSH_CONTACT_GAP, STAGE_LENGTH)
        else:
            attacker.position = max(attacker.position if defender.position >= attacker.position else defender.position + PUSH_CONTACT_GAP, 0.0)
        self.log(f"{attacker.name} uses a {int(card.force)}N push on {defender.name}.")
        self.begin_push_event(self.current_player_index, self.other_player_index(), card)

    def resolve_force_impact(self, card: Card) -> None:
        attacker = self.current_player()
        defender = self.other_player()
        direction = self.attack_direction(attacker, defender)

        if defender.dodge_ready:
            defender.dodge_ready = False
            success_chance = FORCE_SUCCESS[int(card.force)]
            if random.random() <= success_chance:
                self.log(
                    f"{defender.name} dodges {attacker.name}'s {int(card.force)}N shove. "
                    f"{attacker.name} stumbles forward instead."
                )
                self.begin_dodge_event(
                    self.other_player_index(),
                    [{"player_index": self.current_player_index, "direction": direction, "force": card.force}],
                    "Dodge success",
                )
                return
            self.log(f"{defender.name}'s dodge fails against {int(card.force)}N.")

        self.log(
            f"{attacker.name} launches a {int(card.force)}N shove. "
            f"{defender.name} is pushed away and {attacker.name} follows through."
        )
        self.begin_motion_event(
            [
                {"player_index": self.other_player_index(), "direction": direction, "force": card.force},
            ],
            "Direct hit",
            {
                "type": "follow",
                "player_index": self.current_player_index,
                "target_player_index": self.other_player_index(),
                "direction": direction,
                "gap": FOLLOW_GAP,
                "force": card.force,
            },
        )

    def begin_dodge_event(self, player_index: int, followup_motions: List[dict], followup_label: str) -> None:
        force = followup_motions[0]["force"] if followup_motions else 0
        self.animation = {
            "type": "dodge",
            "player_index": player_index,
            "duration": DODGE_DURATION,
            "offset": DODGE_OFFSET,
            "label": "Dodge",
            "force": force,
            "followup_motions": followup_motions,
            "followup_label": followup_label,
            "start_ticks": pygame.time.get_ticks(),
        }

    def begin_push_event(self, attacker_index: int, defender_index: int, card: Card) -> None:
        self.animation = {
            "type": "push",
            "attacker_index": attacker_index,
            "defender_index": defender_index,
            "duration": PUSH_DURATION,
            "card": card,
            "label": "Push",
            "force": card.force,
            "start_ticks": pygame.time.get_ticks(),
        }

    def build_motion_profile(self, player_index: int, direction: float, force: float) -> dict:
        player = self.players[player_index]
        friction_accel = self.stage_friction * GRAVITY
        initial_velocity = force * IMPACT_TIME / PLAYER_MASS
        duration = IMPACT_TIME if friction_accel <= 0 else min(IMPACT_TIME, initial_velocity / friction_accel)
        distance = initial_velocity * duration - 0.5 * friction_accel * (duration ** 2)
        clamped_distance = max(0.0, distance)
        end_position = player.position + direction * clamped_distance
        return {
            "player_index": player_index,
            "start_pos": player.position,
            "direction": direction,
            "force": force,
            "friction_accel": friction_accel,
            "initial_velocity": initial_velocity,
            "duration": duration,
            "distance": clamped_distance,
            "end_pos": end_position,
        }

    def begin_motion_event(self, motions: List[dict], label: str, followup: Optional[dict] = None) -> None:
        self.animation = {
            "type": "motion",
            "motions": [self.build_motion_profile(**motion) for motion in motions],
            "label": label,
            "followup": followup,
            "start_ticks": pygame.time.get_ticks(),
        }

    def update_animation(self) -> None:
        if not self.animation:
            return

        now = pygame.time.get_ticks()
        elapsed = (now - self.animation["start_ticks"]) / 1000.0

        if self.animation["type"] == "dodge":
            duration = self.animation["duration"]
            if elapsed < duration:
                return

            followup_motions = self.animation["followup_motions"]
            followup_label = self.animation["followup_label"]
            self.animation = None
            self.begin_motion_event(followup_motions, followup_label)
            return

        if self.animation["type"] == "push":
            duration = self.animation["duration"]
            if elapsed < duration:
                return

            card = self.animation["card"]
            self.animation = None
            self.resolve_force_impact(card)
            return

        all_finished = True
        for motion in self.animation["motions"]:
            player = self.players[motion["player_index"]]
            duration = motion["duration"]
            if elapsed < duration:
                traveled = motion["initial_velocity"] * elapsed - 0.5 * motion["friction_accel"] * (elapsed ** 2)
                player.position = motion["start_pos"] + motion["direction"] * max(0.0, traveled)
                all_finished = False
            else:
                player.position = motion["end_pos"]

        if not all_finished:
            return

        moved = self.animation
        self.animation = None
        self.check_winner()
        if self.winner is None and moved.get("followup"):
            followup = moved["followup"]
            target_player = self.players[followup["target_player_index"]]
            target_position = target_player.position - followup["direction"] * followup["gap"]
            target_position = max(0.0, min(STAGE_LENGTH, target_position))
            current_player = self.players[followup["player_index"]]
            if followup["direction"] > 0:
                target_position = min(target_position, target_player.position - 0.2)
                target_position = max(target_position, current_player.position)
            else:
                target_position = max(target_position, target_player.position + 0.2)
                target_position = min(target_position, current_player.position)
            start_position = current_player.position
            current_player.position = target_position
            self.check_winner()
            if self.winner is None:
                meters = abs(target_position - start_position)
                self.log(f"{current_player.name} follows up {meters:.2f}m.")
            self.turn_phase = "turn_complete"
            return
        if self.winner is None:
            for motion in moved["motions"]:
                meters = abs(motion["end_pos"] - motion["start_pos"])
                self.log(
                    f"{self.players[motion['player_index']].name} slides {meters:.2f}m "
                    f"under friction {self.stage_friction:.2f}."
                )
        self.turn_phase = "turn_complete"

    def check_winner(self) -> None:
        for index, player in enumerate(self.players):
            if player.position < 0 or player.position > STAGE_LENGTH:
                self.winner = 1 - index
                self.turn_phase = "game_over"
                self.log(f"{player.name} falls into the void.")
                self.log(f"{self.players[self.winner].name} wins the duel.")
                break

    def end_turn(self) -> None:
        if self.animation or self.winner is not None:
            return

        if self.turn_phase != "turn_complete":
            player = self.current_player()
            if player.dodge_ready and not self.action_used_this_turn:
                player.dodge_ready = False
            self.log(f"{player.name} ends the turn without an action.")

        outgoing_player = self.current_player()
        if outgoing_player.dodge_ready and self.action_used_this_turn:
            self.log(f"{outgoing_player.name}'s dodge remains active for the next incoming shove.")

        incoming = self.other_player()
        if incoming.dodge_ready and self.turn_phase != "game_over":
            self.log(f"{incoming.name} still has a dodge primed.")

        self.current_player_index = self.other_player_index()
        self.round_number += 1
        self.start_turn(initial=False)

    def restart(self) -> None:
        self.__init__()

    def battlefield_position(self, meters: float, rect: pygame.Rect, player_index: Optional[int] = None) -> tuple[int, int]:
        (arena_center_x, arena_center_y), arena_radius = self.arena_geometry(rect)
        x = arena_center_x - arena_radius + (meters / STAGE_LENGTH) * (arena_radius * 2)
        y = arena_center_y

        if (
            player_index is not None
            and self.animation
            and self.animation["type"] == "dodge"
            and self.animation["player_index"] == player_index
        ):
            elapsed = (pygame.time.get_ticks() - self.animation["start_ticks"]) / 1000.0
            progress = min(1.0, elapsed / self.animation["duration"])
            arc = math.sin(progress * math.pi) * self.animation["offset"]
            dodge_sign = -1 if player_index == 0 else 1
            y += dodge_sign * arc

        return int(x), int(y)

    def point_in_arena(self, pos: tuple[int, int], rect: pygame.Rect) -> bool:
        center, radius = self.arena_geometry(rect)
        return math.hypot(pos[0] - center[0], pos[1] - center[1]) <= radius + 18

    def wrap_text(self, text: str, font: pygame.font.Font, max_width: int, max_lines: int) -> List[str]:
        words = text.split()
        if not words:
            return [""]

        lines: List[str] = []
        current = words[0]
        for word in words[1:]:
            test = f"{current} {word}"
            if font.size(test)[0] <= max_width:
                current = test
            else:
                lines.append(current)
                current = word
                if len(lines) == max_lines - 1:
                    break
        lines.append(current)

        if len(lines) > max_lines:
            lines = lines[:max_lines]
        if len(lines) == max_lines and " ".join(words) != " ".join(lines):
            trimmed = lines[-1]
            while trimmed and font.size(trimmed + "...")[0] > max_width:
                trimmed = trimmed[:-1]
            lines[-1] = trimmed.rstrip() + "..."
        return lines

    def start_drag(self, index: int, mouse_pos: tuple[int, int]) -> None:
        player = self.current_player()
        if self.animation or self.card_use_animation or self.winner is not None or self.turn_phase != "playing":
            return
        if index >= len(player.hand):
            return
        card = player.hand[index]
        if not self.can_play(player, card):
            self.log(f"{card.name} cannot be played right now.")
            return
        rect = self.card_rects[index]
        self.drag_state = {
            "index": index,
            "offset": (mouse_pos[0] - rect.x, mouse_pos[1] - rect.y),
            "mouse_pos": mouse_pos,
        }
        self.selected_card_index = index

    def release_drag(self, mouse_pos: tuple[int, int]) -> None:
        if not self.drag_state:
            return
        index = self.drag_state["index"]
        self.drag_state = None
        player = self.current_player()
        if index >= len(player.hand):
            self.selected_card_index = None
            return
        card = player.hand[index]
        if self.point_in_arena(mouse_pos, self.board_rect) and self.can_play(player, card):
            arena_center, _ = self.arena_geometry(self.board_rect)
            target_rect = pygame.Rect(0, 0, 164, 152)
            target_rect.center = (arena_center[0], arena_center[1] - 6)
            self.card_use_animation = {
                "index": index,
                "card": card,
                "start_rect": self.card_rects[index].copy(),
                "end_rect": target_rect,
                "duration": 0.22,
                "start_ticks": pygame.time.get_ticks(),
            }
            return
        self.selected_card_index = None

    def update_card_use_animation(self) -> None:
        if not self.card_use_animation:
            return
        elapsed = (pygame.time.get_ticks() - self.card_use_animation["start_ticks"]) / 1000.0
        if elapsed < self.card_use_animation["duration"]:
            return
        index = self.card_use_animation["index"]
        self.card_use_animation = None
        self.play_card_by_index(index)

    def current_card_use_rect(self) -> Optional[pygame.Rect]:
        if not self.card_use_animation:
            return None
        elapsed = (pygame.time.get_ticks() - self.card_use_animation["start_ticks"]) / 1000.0
        progress = min(1.0, elapsed / self.card_use_animation["duration"])
        start_rect = self.card_use_animation["start_rect"]
        end_rect = self.card_use_animation["end_rect"]
        x = start_rect.x + (end_rect.x - start_rect.x) * progress
        y = start_rect.y + (end_rect.y - start_rect.y) * progress
        w = start_rect.width + (end_rect.width - start_rect.width) * progress
        h = start_rect.height + (end_rect.height - start_rect.height) * progress
        return pygame.Rect(int(x), int(y), int(w), int(h))

    def draw_panel(self, rect: pygame.Rect, fill: tuple[int, int, int] = PANEL_COLOR, border: tuple[int, int, int] = CARD_BORDER) -> None:
        shadow = rect.move(0, 6)
        pygame.draw.rect(self.screen, SHADOW_COLOR, shadow, border_radius=24)
        pygame.draw.rect(self.screen, fill, rect, border_radius=24)
        pygame.draw.rect(self.screen, border, rect, width=2, border_radius=24)

    def draw_overlay_panel(self, rect: pygame.Rect, fill: tuple[int, int, int], border: tuple[int, int, int], radius: int = 18) -> None:
        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(panel, fill, panel.get_rect(), border_radius=radius)
        pygame.draw.rect(panel, border, panel.get_rect(), width=2, border_radius=radius)
        self.screen.blit(panel, rect.topleft)

    def draw_background(self) -> None:
        self.screen.fill(BG_COLOR)
        pygame.draw.circle(self.screen, BG_WASH, (220, 120), 220)
        pygame.draw.circle(self.screen, BG_WASH, (SCREEN_WIDTH - 180, 100), 240)
        for y in range(0, SCREEN_HEIGHT, 32):
            pygame.draw.line(self.screen, BG_LINE, (0, y), (SCREEN_WIDTH, y), 1)

    def draw(self) -> None:
        self.draw_background()

        board_rect = pygame.Rect(12, 12, SCREEN_WIDTH - 24, SCREEN_HEIGHT - 24)
        hud_rect = pygame.Rect(28, 28, 360, 142)
        friction_rect = pygame.Rect(SCREEN_WIDTH - 206, 28, 178, 44)
        hand_rect = pygame.Rect(120, SCREEN_HEIGHT - 248, SCREEN_WIDTH - 240, 196)
        self.board_rect = board_rect

        self.end_turn_button.rect = pygame.Rect(SCREEN_WIDTH - 314, SCREEN_HEIGHT - 128, 270, 48)
        self.reset_button.rect = pygame.Rect(SCREEN_WIDTH - 314, SCREEN_HEIGHT - 72, 270, 40)

        self.draw_board(board_rect)
        self.draw_header(hud_rect)
        self.draw_friction_chip(friction_rect)
        self.draw_hand(hand_rect)
        self.draw_dragging_card()
        self.draw_card_use_animation()

        can_end_turn = not self.animation and self.winner is None and self.turn_phase in {"playing", "turn_complete"}
        self.end_turn_button.draw(self.screen, self.body_font, can_end_turn)
        self.reset_button.draw(self.screen, self.small_font, True)

        if self.selected_card_index is not None and self.turn_phase == "playing":
            prompt = "Drag the selected card into the arena to use it."
        elif self.turn_phase == "turn_complete" and can_end_turn:
            prompt = "Action resolved. Press ENTER or click End Turn to pass the duel."
        elif self.turn_phase == "playing" and can_end_turn:
            prompt = "You can still pass the turn if you do not want to use an action card."
        elif self.winner is not None:
            prompt = "Press R or click Restart Match to begin again."
        else:
            prompt = "Click cards to play them. You may use any number of effects, then one action card."
        prompt_text = self.small_font.render(prompt, True, MUTED_COLOR)
        self.screen.blit(prompt_text, (28, SCREEN_HEIGHT - 30))

        pygame.display.flip()

    def draw_header(self, rect: pygame.Rect) -> None:
        current = self.current_player()
        self.draw_overlay_panel(rect, (255, 251, 243, 225), (138, 121, 102, 180))
        title = self.body_font.render("Physics Card Duel", True, TEXT_COLOR)
        subtitle = self.small_font.render(f"Round {self.round_number} | Active {current.name}", True, MUTED_COLOR)
        energy = self.small_font.render(f"Energy {current.energy}/{MAX_ENERGY}", True, TEXT_COLOR)
        cards = self.small_font.render(f"Cards {len(current.hand)}", True, TEXT_COLOR)
        opponent = self.small_font.render(
            f"Opponent {self.other_player().name}  E {self.other_player().energy}/{MAX_ENERGY}",
            True,
            MUTED_COLOR,
        )
        self.screen.blit(title, (rect.x + 18, rect.y + 14))
        self.screen.blit(subtitle, (rect.x + 18, rect.y + 44))
        self.screen.blit(energy, (rect.x + 18, rect.y + 76))
        self.screen.blit(cards, (rect.x + 18, rect.y + 100))
        self.screen.blit(opponent, (rect.x + 156, rect.y + 88))

    def draw_friction_chip(self, rect: pygame.Rect) -> None:
        self.draw_overlay_panel(rect, (255, 251, 243, 225), (138, 121, 102, 180), radius=16)
        label = self.tiny_font.render("Coefficient of Friction", True, MUTED_COLOR)
        value = self.body_font.render(f"{self.stage_friction:.2f}", True, TEXT_COLOR)
        self.screen.blit(label, (rect.x + 14, rect.y + 8))
        self.screen.blit(value, (rect.right - value.get_width() - 16, rect.y + 16))

    def draw_card_frame(self, card_rect: pygame.Rect, card: Card, selected: bool, playable: bool) -> None:
        fill = CARD_BG if playable else CARD_DISABLED
        border = ACCENT_GOLD if selected else CARD_BORDER
        strip = ACCENT_BLUE if card.kind in {"force", "conservation", "smooth"} else ACCENT_RED if card.kind == "rough" else ACCENT_GREEN
        pygame.draw.rect(self.screen, fill, card_rect, border_radius=18)
        pygame.draw.rect(self.screen, border, card_rect, width=3, border_radius=18)
        pygame.draw.rect(self.screen, strip, pygame.Rect(card_rect.x, card_rect.y, 10, card_rect.height), border_top_left_radius=18, border_bottom_left_radius=18)

        title_rect = pygame.Rect(card_rect.x + 14, card_rect.y + 10, card_rect.width - 28, 24)
        pygame.draw.rect(self.screen, (240, 233, 217), title_rect, border_radius=10)
        pygame.draw.rect(self.screen, border, title_rect, width=1, border_radius=10)
        title = self.small_font.render(card.name.upper(), True, TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=title_rect.center))

        cost_center = (card_rect.x + 20, card_rect.y + 18)
        pygame.draw.circle(self.screen, (92, 29, 39), cost_center, 15)
        pygame.draw.circle(self.screen, ACCENT_GOLD, cost_center, 15, 2)
        cost = self.small_font.render(str(card.energy_cost), True, TEXT_COLOR)
        self.screen.blit(cost, cost.get_rect(center=cost_center))

        if card.kind == "force":
            art_fill = (102, 128, 74)
            art_primary = f"{int(card.force)}N"
            art_secondary = "PUSH"
            attack_value = f"{int(card.force)}N"
            range_value = "LINE"
        elif card.kind == "dodge":
            art_fill = (88, 132, 127)
            art_primary = "DODGE"
            art_secondary = "SHIFT"
            attack_value = "EVADE"
            range_value = "SELF"
        elif card.kind == "conservation":
            art_fill = (145, 133, 82)
            art_primary = "ENERGY"
            art_secondary = "LOOP"
            attack_value = "STEAL"
            range_value = "3T"
        elif card.kind == "smooth":
            art_fill = (132, 149, 173)
            art_primary = "SMOOTH"
            art_secondary = "FIELD"
            attack_value = "-0.05"
            range_value = "ARENA"
        else:
            art_fill = (156, 105, 98)
            art_primary = "ROUGH"
            art_secondary = "FIELD"
            attack_value = "+0.10"
            range_value = "ARENA"

        art_rect = pygame.Rect(card_rect.x + 18, card_rect.y + 40, card_rect.width - 36, 62)
        pygame.draw.rect(self.screen, art_fill, art_rect, border_radius=12)
        pygame.draw.rect(self.screen, CARD_BORDER, art_rect, width=1, border_radius=12)
        for glow_step in range(4):
            pygame.draw.rect(
                self.screen,
                (
                    min(255, art_fill[0] + glow_step * 6),
                    min(255, art_fill[1] + glow_step * 8),
                    min(255, art_fill[2] + glow_step * 8),
                ),
                pygame.Rect(art_rect.x + 6 + glow_step * 10, art_rect.y + 6 + glow_step * 6, art_rect.width - 12 - glow_step * 20, 4),
                border_radius=3,
            )
        art_text = self.body_font.render(art_primary, True, TEXT_COLOR)
        art_subtext = self.small_font.render(art_secondary, True, MUTED_COLOR)
        self.screen.blit(art_text, art_text.get_rect(center=(art_rect.centerx, art_rect.y + 24)))
        self.screen.blit(art_subtext, art_subtext.get_rect(center=(art_rect.centerx, art_rect.y + 46)))

        attack_rect = pygame.Rect(card_rect.x + 18, card_rect.y + 108, 62, 24)
        range_rect = pygame.Rect(card_rect.right - 80, card_rect.y + 108, 62, 24)
        pygame.draw.rect(self.screen, (240, 233, 217), attack_rect, border_radius=10)
        pygame.draw.rect(self.screen, (240, 233, 217), range_rect, border_radius=10)
        pygame.draw.rect(self.screen, ACCENT_RED, attack_rect, width=1, border_radius=10)
        pygame.draw.rect(self.screen, ACCENT_BLUE, range_rect, width=1, border_radius=10)
        attack_label = self.tiny_font.render(attack_value, True, TEXT_COLOR)
        range_label = self.tiny_font.render(range_value, True, TEXT_COLOR)
        self.screen.blit(attack_label, attack_label.get_rect(center=attack_rect.center))
        self.screen.blit(range_label, range_label.get_rect(center=range_rect.center))

        desc_rect = pygame.Rect(card_rect.x + 18, card_rect.y + 136, card_rect.width - 36, 18)
        pygame.draw.rect(self.screen, (240, 233, 217), desc_rect, border_radius=6)
        pygame.draw.rect(self.screen, CARD_BORDER, desc_rect, width=1, border_radius=6)
        wrapped = self.wrap_text(card.description.upper(), self.tiny_font, desc_rect.width - 8, 1)
        for i, line in enumerate(wrapped):
            desc = self.tiny_font.render(line, True, MUTED_COLOR)
            self.screen.blit(desc, desc.get_rect(center=(desc_rect.centerx, desc_rect.centery + i * 12)))

    def draw_dragging_card(self) -> None:
        if not self.drag_state:
            return
        index = self.drag_state["index"]
        player = self.current_player()
        if index >= len(player.hand):
            return
        card = player.hand[index]
        mouse_x, mouse_y = self.drag_state["mouse_pos"]
        offset_x, offset_y = self.drag_state["offset"]
        draw_rect = pygame.Rect(mouse_x - offset_x, mouse_y - offset_y, 172, 160)
        self.draw_card_frame(draw_rect, card, True, self.can_play(player, card))

    def draw_card_use_animation(self) -> None:
        if not self.card_use_animation:
            return
        rect = self.current_card_use_rect()
        if rect is None:
            return
        self.draw_card_frame(rect, self.card_use_animation["card"], True, True)

    def draw_board(self, rect: pygame.Rect) -> None:
        arena_center = (rect.centerx, rect.y + 320)
        arena_radius = min(228, max(170, (rect.height // 2) - 100))
        outer_radius = arena_radius + 30
        inner_radius = arena_radius - 26

        pygame.draw.circle(self.screen, VOID_COLOR, arena_center, outer_radius + 18)
        pygame.draw.circle(self.screen, (183, 166, 133), arena_center, outer_radius)
        pygame.draw.circle(self.screen, ACCENT_GOLD, arena_center, outer_radius, 3)
        pygame.draw.circle(self.screen, (233, 223, 199), arena_center, arena_radius)
        pygame.draw.circle(self.screen, STAGE_COLOR, arena_center, arena_radius, 3)
        pygame.draw.circle(self.screen, (176, 154, 120), arena_center, inner_radius, 2)
        pygame.draw.circle(self.screen, (176, 154, 120), arena_center, inner_radius - 34, 1)
        pygame.draw.circle(self.screen, (176, 154, 120), arena_center, inner_radius - 68, 1)

        # Newton-style orbit and gravity cues.
        pygame.draw.ellipse(
            self.screen,
            ACCENT_GOLD,
            pygame.Rect(arena_center[0] - arena_radius + 16, arena_center[1] - 52, (arena_radius - 16) * 2, 104),
            1,
        )
        pygame.draw.ellipse(
            self.screen,
            ACCENT_GOLD,
            pygame.Rect(arena_center[0] - 68, arena_center[1] - arena_radius + 18, 136, (arena_radius - 18) * 2),
            1,
        )
        apple_center = (arena_center[0], arena_center[1] - arena_radius + 30)
        pygame.draw.circle(self.screen, ACCENT_RED, apple_center, 10)
        pygame.draw.line(self.screen, ACCENT_GREEN, (apple_center[0], apple_center[1] - 10), (apple_center[0] + 6, apple_center[1] - 20), 2)
        pygame.draw.line(self.screen, ACCENT_GREEN, (apple_center[0] + 5, apple_center[1] - 20), (apple_center[0] + 11, apple_center[1] - 16), 2)

        left_bound = self.battlefield_position(0.0, rect)
        center_mark = self.battlefield_position(STAGE_LENGTH / 2, rect)
        right_bound = self.battlefield_position(STAGE_LENGTH, rect)
        pygame.draw.line(self.screen, CARD_BORDER, left_bound, right_bound, 2)
        for meter in [0, 5, 10, 15, 20, 25]:
            x, y = self.battlefield_position(float(meter), rect)
            pygame.draw.line(self.screen, CARD_BORDER, (x, y - 10), (x, y + 10), 2)
            label = self.tiny_font.render(str(meter), True, MUTED_COLOR)
            self.screen.blit(label, (x - label.get_width() // 2, arena_center[1] + arena_radius + 18))
        pygame.draw.circle(self.screen, CARD_BORDER, center_mark, 4)

        for index, player in enumerate(self.players):
            clamped = max(0.0, min(STAGE_LENGTH, player.position))
            x, y = self.battlefield_position(clamped, rect, index)
            color = ACCENT_BLUE if index == 0 else ACCENT_RED
            radius = 20
            facing = 1 if index == 0 else -1
            shoulder_front = (x + facing * (radius - 4), y - 2)
            shoulder_rear = (x + facing * (radius - 10), y + 8)
            front_hand = (x + facing * (radius + 12), y - 8)
            rear_hand = (x + facing * (radius + 8), y + 14)
            if self.animation and self.animation["type"] == "push":
                active_player_index = self.animation["attacker_index"]
                target_player_index = self.animation["defender_index"]
                if index in {active_player_index, target_player_index}:
                    other_index = target_player_index if index == active_player_index else active_player_index
                    other_player = self.players[other_index]
                    other_x, other_y = self.battlefield_position(max(0.0, min(STAGE_LENGTH, other_player.position)), rect, other_index)
                    progress = min(1.0, (pygame.time.get_ticks() - self.animation["start_ticks"]) / (self.animation["duration"] * 1000.0))
                    touch_x = int((x + other_x) / 2)
                    touch_y = int((y + other_y) / 2 - 8)
                    front_hand = (touch_x, touch_y)
            if index == self.current_player_index and self.winner is None:
                pygame.draw.circle(self.screen, GLOW_COLOR, (x, y), radius + 8)
            pygame.draw.line(self.screen, TEXT_COLOR, shoulder_front, front_hand, 4)
            pygame.draw.line(self.screen, TEXT_COLOR, shoulder_rear, rear_hand, 4)
            pygame.draw.circle(self.screen, ACCENT_GOLD, front_hand, 4)
            pygame.draw.circle(self.screen, ACCENT_GOLD, rear_hand, 4)
            pygame.draw.circle(self.screen, color, (x, y), radius)
            pygame.draw.circle(self.screen, TEXT_COLOR, (x, y), radius, 3)
            name = self.small_font.render(player.name, True, TEXT_COLOR)
            self.screen.blit(name, name.get_rect(center=(x, y - 46)))
            if player.dodge_ready:
                dodge_text = self.tiny_font.render("DODGE READY", True, ACCENT_GREEN)
                self.screen.blit(dodge_text, dodge_text.get_rect(center=(x, y + 34)))

        if self.animation and self.animation["type"] == "push":
            attacker = self.players[self.animation["attacker_index"]]
            defender = self.players[self.animation["defender_index"]]
            attacker_x, attacker_y = self.battlefield_position(max(0.0, min(STAGE_LENGTH, attacker.position)), rect, self.animation["attacker_index"])
            defender_x, defender_y = self.battlefield_position(max(0.0, min(STAGE_LENGTH, defender.position)), rect, self.animation["defender_index"])
            impact_center = (int((attacker_x + defender_x) / 2), int((attacker_y + defender_y) / 2 - 8))
            progress = min(1.0, (pygame.time.get_ticks() - self.animation["start_ticks"]) / (self.animation["duration"] * 1000.0))
            pulse_radius = 7 + int(math.sin(progress * math.pi) * 10)
            pygame.draw.circle(self.screen, ACCENT_GOLD, impact_center, pulse_radius, 2)
            pygame.draw.circle(self.screen, PANEL_COLOR, impact_center, max(3, pulse_radius - 5))

        if self.animation:
            if self.animation["type"] in {"dodge", "push"}:
                display_force = int(self.animation["force"])
            else:
                display_force = int(self.animation["motions"][0]["force"])
            anim_text = self.small_font.render(
                f"{self.animation['label']}: {display_force}N resolving",
                True,
                TEXT_COLOR,
            )
            self.screen.blit(anim_text, (rect.right - 340, rect.y + 24))

        if self.winner is not None:
            win_text = self.title_font.render(f"{self.players[self.winner].name} Wins", True, ACCENT_GREEN)
            self.screen.blit(win_text, (rect.right - 320, rect.y + 62))

    def draw_sidebar(self, rect: pygame.Rect) -> None:
        current = self.current_player()
        opponent = self.other_player()
        title = self.body_font.render("SYSTEM PANEL", True, TEXT_COLOR)
        subtitle = self.small_font.render("Live combat state and control interface", True, MUTED_COLOR)
        self.screen.blit(title, (rect.x + 18, rect.y + 16))
        self.screen.blit(subtitle, (rect.x + 18, rect.y + 46))

        current_rect = pygame.Rect(rect.x + 18, rect.y + 76, rect.width - 36, 96)
        opponent_rect = pygame.Rect(rect.x + 18, rect.y + 184, rect.width - 36, 78)
        for panel_rect, fill in [(current_rect, (18, 38, 56)), (opponent_rect, (22, 31, 45))]:
            pygame.draw.rect(self.screen, fill, panel_rect, border_radius=18)
            pygame.draw.rect(self.screen, CARD_BORDER, panel_rect, width=1, border_radius=18)

        current_name = self.body_font.render(current.name, True, TEXT_COLOR)
        current_stats = [
            f"Energy {current.energy}/{MAX_ENERGY}",
            f"Cards in hand {len(current.hand)}",
            f"Action used {str(self.action_used_this_turn).upper()}",
        ]
        self.screen.blit(current_name, (current_rect.x + 14, current_rect.y + 10))
        for i, line in enumerate(current_stats):
            text = self.small_font.render(line, True, MUTED_COLOR)
            self.screen.blit(text, (current_rect.x + 14, current_rect.y + 40 + i * 18))

        opp_name = self.body_font.render(f"Opponent: {opponent.name}", True, TEXT_COLOR)
        opp_stats = self.small_font.render(
            f"Energy {opponent.energy}/{MAX_ENERGY}   Cards {len(opponent.hand)}",
            True,
            MUTED_COLOR,
        )
        self.screen.blit(opp_name, (opponent_rect.x + 14, opponent_rect.y + 10))
        self.screen.blit(opp_stats, (opponent_rect.x + 14, opponent_rect.y + 42))

        state_text = "Winner declared" if self.winner is not None else self.turn_phase.replace("_", " ").title()
        state_rect = pygame.Rect(rect.x + 18, rect.y + 282, 118, 34)
        pygame.draw.rect(self.screen, CARD_BG, state_rect, border_radius=16)
        pygame.draw.rect(self.screen, ACCENT_GREEN if self.winner is None else ACCENT_RED, state_rect, width=1, border_radius=16)
        state_label = self.tiny_font.render(state_text, True, TEXT_COLOR)
        self.screen.blit(state_label, state_label.get_rect(center=state_rect.center))

        friction_rect = pygame.Rect(rect.x + 148, rect.y + 282, rect.width - 166, 34)
        pygame.draw.rect(self.screen, CARD_BG, friction_rect, border_radius=16)
        pygame.draw.rect(self.screen, ACCENT_BLUE, friction_rect, width=1, border_radius=16)
        friction_label = self.tiny_font.render(f"FRICTION {self.stage_friction:.2f}", True, TEXT_COLOR)
        self.screen.blit(friction_label, friction_label.get_rect(center=friction_rect.center))

    def draw_hand(self, rect: pygame.Rect) -> None:
        player = self.current_player()
        self.draw_overlay_panel(rect, (255, 251, 243, 210), (138, 121, 102, 180), radius=22)
        title = self.body_font.render(f"{player.name.upper()} CARD BUFFER", True, TEXT_COLOR)
        helper = self.small_font.render(
            "Drag a card into the arena to deploy it. Effects first, then one action card.",
            True,
            MUTED_COLOR,
        )
        self.screen.blit(title, (rect.x + 20, rect.y + 16))
        self.screen.blit(helper, (rect.x + 20, rect.y + 46))

        self.card_rects = []
        if not player.hand:
            empty = self.body_font.render("No cards in hand.", True, MUTED_COLOR)
            self.screen.blit(empty, (rect.x + 20, rect.y + 120))
            return

        cards_per_row = 5
        gap_x = 18
        gap_y = 16
        card_width = 172
        card_height = 160
        total_row_width = (card_width * cards_per_row) + (gap_x * (cards_per_row - 1))
        start_x = rect.x + max(20, (rect.width - total_row_width) // 2)

        for index, card in enumerate(player.hand[:MAX_HAND_SIZE]):
            row = index // cards_per_row
            col = index % cards_per_row
            card_rect = pygame.Rect(
                start_x + col * (card_width + gap_x),
                rect.y + 78 + row * (card_height + gap_y),
                card_width,
                card_height,
            )
            self.card_rects.append(card_rect)
            if self.drag_state and self.drag_state["index"] == index:
                continue
            if self.card_use_animation and self.card_use_animation["index"] == index:
                continue
            selected = index == self.selected_card_index
            playable = self.can_play(player, card)
            self.draw_card_frame(card_rect, card, selected, playable)

    def on_card_click(self, pos) -> None:
        if self.turn_phase != "playing" or self.animation or self.card_use_animation or self.winner is not None:
            return
        for index, rect in enumerate(self.card_rects):
            if rect.collidepoint(pos):
                self.start_drag(index, pos)
                return

    def run(self) -> None:
        running = True
        while running:
            self.clock.tick(FPS)
            self.update_card_use_animation()
            self.update_animation()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        self.play_selected_card()
                    elif event.key == pygame.K_RETURN:
                        if not self.animation and self.winner is None and self.turn_phase in {"playing", "turn_complete"}:
                            self.end_turn()
                    elif event.key == pygame.K_r:
                        self.restart()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.reset_button.contains(event.pos):
                        self.restart()
                    elif self.end_turn_button.contains(event.pos):
                        if not self.animation and self.winner is None and self.turn_phase in {"playing", "turn_complete"}:
                            self.end_turn()
                    else:
                        self.on_card_click(event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    if self.drag_state:
                        self.drag_state["mouse_pos"] = event.pos
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if self.drag_state:
                        self.release_drag(event.pos)

            self.draw()

        pygame.quit()


if __name__ == "__main__":
    Game().run()
