import math
import os
import random
import threading
from typing import List, Optional

import pygame

from card_factory import build_opening_hand, draw_random_card
from education import build_local_explanation, build_physics_prompt
from gemini_education import request_gemini_explanation
from game_constants import (
    ACCENT_BLUE,
    ACCENT_GOLD,
    ACCENT_GREEN,
    ACCENT_RED,
    BASE_FRICTION,
    BG_COLOR,
    BG_LINE,
    BG_WASH,
    CARD_BG,
    CARD_BORDER,
    CARD_DISABLED,
    DODGE_DURATION,
    DODGE_OFFSET,
    DRAW_PER_TURN,
    ENERGY_PER_TURN,
    FOLLOW_GAP,
    FORCE_SUCCESS,
    FPS,
    GLOW_COLOR,
    GRAVITY,
    IMPACT_TIME,
    LINE_MARGIN,
    MAX_ENERGY,
    MAX_HAND_SIZE,
    MUTED_COLOR,
    PANEL_COLOR,
    PLAYER_MASS,
    PUSH_CONTACT_GAP,
    PUSH_DURATION,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SHADOW_COLOR,
    STAGE_COLOR,
    STAGE_LENGTH,
    START_HAND,
    START_POSITIONS,
    TEXT_COLOR,
    VOID_COLOR,
)
from game_models import Card, PendingRestore, Player
from ui_components import Button


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Physics Card Duel")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("georgia", 30, bold=True)
        self.hero_font = pygame.font.SysFont("georgia", 64, bold=True)
        self.menu_font = pygame.font.SysFont("georgia", 28, bold=True)
        self.body_font = pygame.font.SysFont("georgia", 22)
        self.small_font = pygame.font.SysFont("georgia", 18)
        self.tiny_font = pygame.font.SysFont("georgia", 15)
        self.hand_card_width = 220
        self.hand_card_height = 282
        self.end_turn_button = Button(pygame.Rect(1040, 680, 200, 58), "End Turn")
        self.reset_button = Button(pygame.Rect(1040, 612, 200, 50), "Restart Match")
        self.log_button = Button(pygame.Rect(0, 0, 180, 42), "Battle Log")
        self.education_toggle_button = Button(pygame.Rect(0, 0, 180, 40), "Education: On")
        self.log_prev_button = Button(pygame.Rect(0, 0, 130, 40), "Previous")
        self.log_next_button = Button(pygame.Rect(0, 0, 130, 40), "Next")
        self.log_close_button = Button(pygame.Rect(0, 0, 130, 40), "Close")
        self.education_exit_button = Button(pygame.Rect(0, 0, 130, 40), "Exit")
        self.menu_buttons = {
            "play": Button(pygame.Rect(0, 0, 260, 58), "Play"),
            "instruction": Button(pygame.Rect(0, 0, 260, 58), "Instruction"),
            "about": Button(pygame.Rect(0, 0, 260, 58), "About"),
        }
        self.back_button = Button(pygame.Rect(0, 0, 180, 46), "Back")
        self.current_screen = "menu"
        self.transition = None
        self.card_images = self.load_card_images()
        self.card_back_image = self.load_card_back_image()
        self.education_enabled = True
        self.initialize_match()

    def initialize_match(self, animated_setup: bool = False) -> None:
        self.players = [
            Player(name="p1", position=START_POSITIONS[0]),
            Player(name="p2", position=START_POSITIONS[1]),
        ]
        self.current_player_index = 0
        self.round_number = 1
        self.turn_started = False
        self.turn_phase = "turn_start"
        self.winner = None
        self.stage_friction = BASE_FRICTION
        self.selected_card_index = None
        self.effect_used_this_turn = False
        self.conservation_used_this_turn = False
        self.action_used_this_turn = False
        self.animation = None
        self.pending_winner = None
        self.deal_sequence = None
        self.opening_hands = None
        self.pending_transition_action = None
        self.card_use_animation = None
        self.drag_state = None
        self.messages = []
        self.battle_log_pages: List[dict] = []
        self.log_view_open = False
        self.log_page_index = 0
        self.log_scroll_offset = 0
        self.card_rects = []
        self.board_rect = pygame.Rect(0, 0, 0, 0)
        self.side_order = 1 if self.players[0].position <= self.players[1].position else -1
        self.turn_effect_cards: List[str] = []
        self.pending_education_context = None
        self.queued_education_context = None
        self.education_popup = None
        self.education_generation = None
        self.education_scroll_offset = 0
        self.education_request_counter = 0
        if animated_setup:
            self.turn_phase = "dealing"
            self.opening_hands = [build_opening_hand(START_HAND) for _ in self.players]
            self.pending_transition_action = {"type": "opening_deal"}
        else:
            for player in self.players:
                player.hand.extend(build_opening_hand(START_HAND))
            self.start_turn(initial=True)

    def load_card_images(self) -> dict[str, pygame.Surface]:
        image_dir = os.path.join(os.path.dirname(__file__), "card_image")
        image_map = {
            "Force 50N": "impluse.png",
            "Force 75N": "momentum.png",
            "Force 100N": "inertia.png",
            "Force 125N": "magnitude.png",
            "Dodge": "dodge.png",
            "Conservation": "conserv_of_energy.png",
            "Smooth": "smoother.png",
            "Rough": "rougher.png",
        }
        loaded_images: dict[str, pygame.Surface] = {}
        for card_name, filename in image_map.items():
            image_path = os.path.join(image_dir, filename)
            if os.path.exists(image_path):
                loaded_images[card_name] = pygame.image.load(image_path).convert_alpha()
        return loaded_images

    def load_card_back_image(self) -> Optional[pygame.Surface]:
        image_dir = os.path.join(os.path.dirname(__file__), "card_image")
        for filename in ("back_card.jpg", "back_card.png"):
            image_path = os.path.join(image_dir, filename)
            if os.path.exists(image_path):
                return pygame.image.load(image_path).convert()
        return None

    def begin_game_transition(self) -> None:
        self.transition = {
            "start_ticks": pygame.time.get_ticks(),
            "duration": 1100,
        }
        self.current_screen = "game"

    def update_transition(self) -> None:
        if not self.transition:
            return
        elapsed = pygame.time.get_ticks() - self.transition["start_ticks"]
        if elapsed >= self.transition["duration"]:
            self.transition = None
            if self.pending_transition_action:
                action = self.pending_transition_action
                self.pending_transition_action = None
                if action["type"] == "opening_deal":
                    self.begin_opening_deal_sequence()

    def transition_progress(self) -> float:
        if not self.transition:
            return 1.0
        elapsed = pygame.time.get_ticks() - self.transition["start_ticks"]
        return max(0.0, min(1.0, elapsed / self.transition["duration"]))

    def log(self, message: str) -> None:
        self.messages.append(message)
        self.messages = self.messages[-8:]
        if not self.battle_log_pages or self.battle_log_pages[-1]["round"] != self.round_number:
            self.battle_log_pages.append(
                {
                    "round": self.round_number,
                    "title": f"Round {self.round_number}",
                    "entries": [],
                }
            )
        self.battle_log_pages[-1]["entries"].append(message)
        if self.log_view_open:
            self.log_page_index = len(self.battle_log_pages) - 1

    def current_player(self) -> Player:
        return self.players[self.current_player_index]

    def other_player_index(self) -> int:
        return 1 - self.current_player_index

    def other_player(self) -> Player:
        return self.players[self.other_player_index()]

    def relative_side_order(self) -> int:
        if self.players[0].position < self.players[1].position:
            self.side_order = 1
        elif self.players[0].position > self.players[1].position:
            self.side_order = -1
        return self.side_order

    def player_facing_direction(self, player_index: int) -> float:
        side_order = self.relative_side_order()
        return float(side_order if player_index == 0 else -side_order)

    def arena_geometry(self, rect: pygame.Rect) -> tuple[tuple[int, int], int, int]:
        arena_center = (rect.centerx, rect.y + 328)
        arena_radius_x = min(560, max(450, (rect.width // 2) - 240))
        arena_radius_y = min(290, max(220, (rect.height // 2) - 150))
        if self.transition:
            progress = self.transition_progress()
            eased = 1.0 - ((1.0 - progress) ** 3)
            arena_center = (arena_center[0], int(arena_center[1] - 430 * (1.0 - eased)))
            arena_radius_x = max(180, int(arena_radius_x * (0.58 + 0.42 * eased)))
            arena_radius_y = max(96, int(arena_radius_y * (0.58 + 0.42 * eased)))
        return arena_center, arena_radius_x, arena_radius_y

    def arena_ellipse_rect(self, rect: pygame.Rect) -> pygame.Rect:
        arena_center, arena_radius_x, arena_radius_y = self.arena_geometry(rect)
        return pygame.Rect(
            arena_center[0] - arena_radius_x,
            arena_center[1] - arena_radius_y,
            arena_radius_x * 2,
            arena_radius_y * 2,
        )

    def side_stack_anchor(self, rect: pygame.Rect, player_index: int) -> tuple[int, int]:
        arena_center, arena_radius_x, _ = self.arena_geometry(rect)
        offset = arena_radius_x + 136
        x = arena_center[0] - offset if player_index == 0 else arena_center[0] + offset
        return x, arena_center[1] + 18

    def deck_anchor(self, rect: pygame.Rect) -> tuple[int, int]:
        arena_center, _, _ = self.arena_geometry(rect)
        return arena_center[0], arena_center[1] - 4

    def deal_target_anchor(self, rect: pygame.Rect, player_index: int) -> tuple[int, int]:
        return self.side_stack_anchor(rect, player_index)

    def begin_deal_sequence(
        self,
        player_order: List[int],
        final_action: str,
        caption: str,
        cards: Optional[List[Card]] = None,
    ) -> None:
        if self.board_rect.width <= 0:
            self.board_rect = pygame.Rect(12, 12, SCREEN_WIDTH - 24, SCREEN_HEIGHT - 24)
        self.deal_sequence = {
            "phase": "shuffle",
            "start_ticks": pygame.time.get_ticks(),
            "shuffle_duration": 900,
            "card_interval": 150,
            "travel_duration": 420,
            "pulse_duration": 300,
            "player_order": player_order,
            "cards": cards or [],
            "next_index": 0,
            "last_spawn_ticks": 0,
            "active_cards": [],
            "pulses": [],
            "caption": caption,
            "final_action": final_action,
        }
        self.turn_phase = "dealing"

    def begin_opening_deal_sequence(self) -> None:
        opening_order: List[int] = []
        opening_cards: List[Card] = []
        for _ in range(START_HAND):
            opening_order.extend([0, 1])
            if self.opening_hands:
                opening_cards.append(self.opening_hands[0].pop(0))
                opening_cards.append(self.opening_hands[1].pop(0))
        self.begin_deal_sequence(
            opening_order,
            "opening_complete",
            "Summoning deck and distributing opening hands",
            cards=opening_cards,
        )

    def complete_deal_sequence(self) -> None:
        if not self.deal_sequence:
            return
        final_action = self.deal_sequence["final_action"]
        self.deal_sequence = None
        if final_action == "opening_complete":
            self.start_turn(initial=True)
        elif final_action == "round_draw_complete":
            self.turn_phase = "playing"

    def update_deal_sequence(self) -> None:
        if not self.deal_sequence:
            return

        now = pygame.time.get_ticks()
        sequence = self.deal_sequence
        if sequence["phase"] == "shuffle":
            if now - sequence["start_ticks"] >= sequence["shuffle_duration"]:
                sequence["phase"] = "deal"
                sequence["last_spawn_ticks"] = now - sequence["card_interval"]
            return

        while (
            sequence["next_index"] < len(sequence["player_order"])
            and now - sequence["last_spawn_ticks"] >= sequence["card_interval"]
        ):
            player_index = sequence["player_order"][sequence["next_index"]]
            predetermined_cards = sequence["cards"]
            card = predetermined_cards.pop(0) if predetermined_cards else draw_random_card()
            sequence["next_index"] += 1
            sequence["last_spawn_ticks"] += sequence["card_interval"]
            sequence["active_cards"].append(
                {
                    "player_index": player_index,
                    "card": card,
                    "start_ticks": now,
                }
            )

        remaining_cards = []
        for moving_card in sequence["active_cards"]:
            if now - moving_card["start_ticks"] >= sequence["travel_duration"]:
                player = self.players[moving_card["player_index"]]
                if len(player.hand) < MAX_HAND_SIZE:
                    player.hand.append(moving_card["card"])
                sequence["pulses"].append(
                    {
                        "player_index": moving_card["player_index"],
                        "start_ticks": now,
                    }
                )
            else:
                remaining_cards.append(moving_card)
        sequence["active_cards"] = remaining_cards

        sequence["pulses"] = [
            pulse
            for pulse in sequence["pulses"]
            if now - pulse["start_ticks"] < sequence["pulse_duration"]
        ]

        if (
            sequence["next_index"] >= len(sequence["player_order"])
            and not sequence["active_cards"]
            and not sequence["pulses"]
        ):
            self.complete_deal_sequence()

    def start_turn(self, initial: bool = False) -> None:
        player = self.current_player()
        self.selected_card_index = None
        self.effect_used_this_turn = False
        self.conservation_used_this_turn = False
        self.action_used_this_turn = False
        self.turn_effect_cards = []
        self.pending_education_context = None
        self.queued_education_context = None
        self.education_generation = None
        self.turn_phase = "playing"

        if not player.has_started_turn:
            player.has_started_turn = True
            return

        if not initial:
            if player.dodge_ready:
                player.dodge_ready = False
                self.log(f"{player.name}'s prepared dodge fades because no shove came last round.")
            gained = min(ENERGY_PER_TURN, MAX_ENERGY - player.energy)
            player.energy += gained
            current_draws = max(0, min(DRAW_PER_TURN, MAX_HAND_SIZE - len(player.hand)))
            other_player = self.other_player()
            other_draws = max(0, min(DRAW_PER_TURN, MAX_HAND_SIZE - len(other_player.hand)))
            self.resolve_delayed_energy(player)
            self.log(
                f"Round {self.round_number}: {player.name} gains {gained} energy. "
                f"Cards are dealt to both players."
            )
            deal_order: List[int] = []
            for _ in range(max(current_draws, other_draws)):
                if current_draws > 0:
                    deal_order.append(self.current_player_index)
                    current_draws -= 1
                if other_draws > 0:
                    deal_order.append(self.other_player_index())
                    other_draws -= 1
            if deal_order:
                self.begin_deal_sequence(
                    deal_order,
                    "round_draw_complete",
                    "Distributing round cards to both players",
                )
            else:
                self.turn_phase = "playing"

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
        if (
            self.log_view_open
            or self.education_popup is not None
            or self.education_generation is not None
            or self.animation
            or self.deal_sequence
            or self.card_use_animation
            or self.winner is not None
            or self.turn_phase != "playing"
        ):
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
        if self.selected_card_index is None or self.log_view_open or self.education_popup is not None or self.education_generation is not None or self.animation or self.card_use_animation or self.winner is not None:
            return
        self.play_card_by_index(self.selected_card_index)

    def play_card_by_index(self, index: int) -> None:
        if self.log_view_open or self.education_popup is not None or self.education_generation is not None or self.animation or self.card_use_animation or self.winner is not None:
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
            self.open_education_popup(
                {
                    "actor": player.name,
                    "target": self.other_player().name,
                    "action_card": card.name,
                    "action_kind": card.kind,
                    "effect_cards": list(self.turn_effect_cards),
                    "enemy_response": "No immediate enemy response",
                    "force": card.force,
                    "friction": self.stage_friction,
                    "mass": PLAYER_MASS,
                    "gravity": GRAVITY,
                    "impact_time": IMPACT_TIME,
                    "outcome": "The player stored a dodge state for the next incoming shove and did not create immediate linear motion.",
                    "motions": [],
                }
            )
        elif card.kind == "conservation":
            self.conservation_used_this_turn = True
            self.effect_used_this_turn = True
            self.turn_effect_cards.append(card.name)
            self.resolve_conservation()
        elif card.kind == "smooth":
            self.effect_used_this_turn = True
            self.turn_effect_cards.append(card.name)
            old = self.stage_friction
            self.stage_friction = max(0.0, self.stage_friction - 0.05)
            self.log(f"{player.name} smooths the arena. Friction {old:.2f} -> {self.stage_friction:.2f}.")
        elif card.kind == "rough":
            self.effect_used_this_turn = True
            self.turn_effect_cards.append(card.name)
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

    def attack_direction(self, attacker_index: int, defender_index: int) -> float:
        attacker = self.players[attacker_index]
        defender = self.players[defender_index]
        if math.isclose(attacker.position, defender.position, abs_tol=0.01):
            return self.player_facing_direction(attacker_index)
        return 1.0 if defender.position > attacker.position else -1.0

    def resolve_force_card(self, card: Card) -> None:
        attacker = self.current_player()
        defender = self.other_player()
        direction = self.attack_direction(self.current_player_index, self.other_player_index())
        self.pending_education_context = {
            "actor": attacker.name,
            "target": defender.name,
            "action_card": card.name,
            "action_kind": card.kind,
            "effect_cards": list(self.turn_effect_cards),
            "enemy_response": "No dodge response",
            "force": card.force,
            "friction": self.stage_friction,
            "mass": PLAYER_MASS,
            "gravity": GRAVITY,
            "impact_time": IMPACT_TIME,
            "outcome": "",
            "motions": [],
        }
        if direction > 0:
            attacker.position = min(attacker.position if defender.position <= attacker.position else defender.position - PUSH_CONTACT_GAP, STAGE_LENGTH)
        else:
            attacker.position = max(attacker.position if defender.position >= attacker.position else defender.position + PUSH_CONTACT_GAP, 0.0)
        self.log(f"{attacker.name} uses a {int(card.force)}N push on {defender.name}.")
        self.begin_push_event(self.current_player_index, self.other_player_index(), card)

    def resolve_force_impact(self, card: Card) -> None:
        attacker = self.current_player()
        defender = self.other_player()
        direction = self.attack_direction(self.current_player_index, self.other_player_index())

        if defender.dodge_ready:
            defender.dodge_ready = False
            success_chance = FORCE_SUCCESS[int(card.force)]
            if random.random() <= success_chance:
                stumble_motion = self.build_motion_profile(self.current_player_index, direction, card.force)
                if self.pending_education_context is not None:
                    self.pending_education_context["enemy_response"] = "Dodge success"
                    self.pending_education_context["outcome"] = (
                        f"{defender.name} avoided the shove, so {attacker.name} kept moving and stumbled past under friction."
                    )
                    self.pending_education_context["motions"] = [self.motion_to_summary(stumble_motion)]
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
            if self.pending_education_context is not None:
                self.pending_education_context["enemy_response"] = "Dodge failed"
            self.log(f"{defender.name}'s dodge fails against {int(card.force)}N.")
        elif self.pending_education_context is not None:
            self.pending_education_context["enemy_response"] = "No dodge used"

        self.log(
            f"{attacker.name} launches a {int(card.force)}N shove. "
            f"{defender.name} is pushed away and {attacker.name} follows through."
        )
        defender_motion = self.build_motion_profile(self.other_player_index(), direction, card.force)
        if self.pending_education_context is not None:
            self.pending_education_context["outcome"] = (
                f"{defender.name} was pushed across the arena while {attacker.name} followed into the new space."
            )
            self.pending_education_context["motions"] = [self.motion_to_summary(defender_motion)]
        target_position = defender_motion["end_pos"] - direction * FOLLOW_GAP
        target_position = max(0.0, min(STAGE_LENGTH, target_position))
        if direction > 0:
            target_position = min(target_position, defender_motion["end_pos"] - 0.2)
            target_position = max(target_position, attacker.position)
        else:
            target_position = max(target_position, defender_motion["end_pos"] + 0.2)
            target_position = min(target_position, attacker.position)
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

    def motion_to_summary(self, motion: dict) -> dict:
        return {
            "subject": self.players[motion["player_index"]].name,
            "distance": abs(motion["end_pos"] - motion["start_pos"]),
            "initial_velocity": motion["initial_velocity"],
            "friction_accel": motion["friction_accel"],
            "duration": motion["duration"],
        }

    def finalize_education_context(self, motions: List[dict], followup_distance: float = 0.0) -> Optional[dict]:
        if self.pending_education_context is None:
            return None
        context = dict(self.pending_education_context)
        if motions:
            context["motions"] = [self.motion_to_summary(motion) for motion in motions]
        if followup_distance > 0:
            context["outcome"] += f" Follow-up distance: {followup_distance:.2f} m."
        self.pending_education_context = None
        return context

    def open_education_popup(self, context: dict) -> None:
        if not self.education_enabled:
            return
        self.education_request_counter += 1
        request_id = self.education_request_counter
        self.education_generation = {
            "request_id": request_id,
            "status": "loading",
            "body": None,
            "context": dict(context),
        }

        prompt = build_physics_prompt(context)
        fallback_text = build_local_explanation(context)

        def worker() -> None:
            try:
                result = request_gemini_explanation(prompt)
            except Exception as exc:  # noqa: BLE001
                result = fallback_text + f"\n\nGemini fallback reason: {exc}"
            if self.education_generation and self.education_generation.get("request_id") == request_id:
                self.education_generation["status"] = "ready"
                self.education_generation["body"] = result

        threading.Thread(target=worker, daemon=True).start()

    def update_education_generation(self) -> None:
        if not self.education_enabled:
            self.education_generation = None
            return
        if self.education_generation is None:
            return
        if self.education_generation["status"] != "ready":
            return
        self.education_scroll_offset = 0
        self.education_popup = {
            "request_id": self.education_generation["request_id"],
            "title": "What happened?",
            "body": self.education_generation["body"] or "",
            "context": dict(self.education_generation.get("context") or {}),
            "opened_ticks": pygame.time.get_ticks(),
            "flip_duration": 620,
            "flip_state": "back",
            "flip_target": "front",
            "flip_started_ticks": None,
        }
        self.education_generation = None

    def close_education_popup(self) -> None:
        self.education_popup = None
        self.education_scroll_offset = 0

    def set_education_enabled(self, enabled: bool) -> None:
        self.education_enabled = enabled
        self.education_toggle_button.label = "Education: On" if enabled else "Education: Off"
        if not enabled:
            self.pending_education_context = None
            self.queued_education_context = None
            self.education_generation = None
            self.close_education_popup()

    def toggle_education_enabled(self) -> None:
        self.set_education_enabled(not self.education_enabled)

    def scroll_education_popup(self, amount: int) -> None:
        if self.education_popup is None:
            return
        self.education_scroll_offset = max(0, self.education_scroll_offset + amount)

    def handle_education_click(self, pos) -> bool:
        if self.education_popup is None:
            return False
        panel, exit_rect = self.education_layout()
        if exit_rect.collidepoint(pos):
            self.close_education_popup()
            return True
        if panel.collidepoint(pos):
            if self.education_popup["flip_state"] == "back":
                self.education_popup["flip_state"] = "animating"
                self.education_popup["flip_target"] = "front"
                self.education_popup["flip_started_ticks"] = pygame.time.get_ticks()
            elif self.education_popup["flip_state"] == "front":
                self.education_popup["flip_state"] = "animating"
                self.education_popup["flip_target"] = "back"
                self.education_popup["flip_started_ticks"] = pygame.time.get_ticks()
            return True
        return True

    def education_layout(self) -> tuple[pygame.Rect, pygame.Rect]:
        panel = pygame.Rect(0, 0, 900, 620)
        panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        exit_rect = pygame.Rect(panel.right - 164, panel.bottom - 62, 130, 40)
        return panel, exit_rect

    def draw_education_popup(self) -> None:
        if self.education_popup is None:
            return

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((1, 8, 18, 188))
        self.screen.blit(overlay, (0, 0))

        panel, exit_rect = self.education_layout()
        flip_state = self.education_popup["flip_state"]
        flip_target = self.education_popup["flip_target"]
        if flip_state == "animating":
            flip_elapsed = pygame.time.get_ticks() - self.education_popup["flip_started_ticks"]
            flip_progress = min(1.0, flip_elapsed / self.education_popup["flip_duration"])
            if flip_progress >= 1.0:
                self.education_popup["flip_state"] = flip_target
                self.education_popup["flip_started_ticks"] = None
                flip_state = flip_target
                flip_progress = 1.0
        else:
            flip_progress = 1.0 if flip_state == "front" else 0.0

        flip_angle = flip_progress * math.pi
        width_scale = max(0.05, abs(math.cos(flip_angle)))
        if self.education_popup["flip_state"] == "animating":
            show_front = flip_progress >= 0.5
        else:
            show_front = self.education_popup["flip_state"] == "front"

        if show_front:
            card_surface = self.render_education_front(panel.size, exit_rect)
        else:
            card_surface = self.render_education_back(panel.size, exit_rect)

        scaled_width = max(18, int(panel.width * width_scale))
        scaled_surface = pygame.transform.smoothscale(card_surface, (scaled_width, panel.height))
        scaled_rect = scaled_surface.get_rect(center=panel.center)
        self.screen.blit(scaled_surface, scaled_rect.topleft)

        if scaled_width < 42:
            edge_rect = pygame.Rect(0, 0, 10, panel.height - 18)
            edge_rect.center = panel.center
            edge_surface = pygame.Surface((edge_rect.width, edge_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(edge_surface, (142, 230, 255, 220), edge_surface.get_rect(), border_radius=6)
            self.screen.blit(edge_surface, edge_rect.topleft)

    def render_education_back(self, size: tuple[int, int], exit_rect: pygame.Rect) -> pygame.Surface:
        surface = pygame.Surface(size, pygame.SRCALPHA)
        rect = surface.get_rect()
        pygame.draw.rect(surface, (8, 22, 52, 245), rect, border_radius=28)
        pygame.draw.rect(surface, (88, 196, 255, 220), rect, width=3, border_radius=28)
        context = self.education_popup.get("context", {})
        effect_cards = list(context.get("effect_cards") or [])
        action_card = context.get("action_card")
        if action_card:
            effect_cards.append(action_card)
        actor_name = str(context.get("actor", "p1")).upper()
        target_name = str(context.get("target", "p2")).upper()
        actor_text = f"{actor_name}: {' + '.join(effect_cards) if effect_cards else 'Action'}"

        enemy_response = str(context.get("enemy_response", "")).lower()
        reaction_text = f"{target_name}: Dodge" if "dodge" in enemy_response else None
        actor_lines = self.wrap_text(actor_text, self.body_font, rect.width - 160, 4)
        reaction_lines = self.wrap_text(reaction_text, self.body_font, rect.width - 160, 2) if reaction_text else []

        y = rect.y + 150
        for line in actor_lines:
            text = self.body_font.render(line, True, TEXT_COLOR)
            surface.blit(text, text.get_rect(center=(rect.centerx, y)))
            y += 32

        if reaction_lines:
            plus = self.title_font.render("+", True, ACCENT_BLUE)
            surface.blit(plus, plus.get_rect(center=(rect.centerx, y + 18)))
            y += 56
            for line in reaction_lines:
                text = self.body_font.render(line, True, TEXT_COLOR)
                surface.blit(text, text.get_rect(center=(rect.centerx, y)))
                y += 32

        equation = self.hero_font.render("= What Happen?", True, TEXT_COLOR)
        surface.blit(equation, equation.get_rect(center=(rect.centerx, rect.bottom - 152)))

        local_exit_rect = pygame.Rect(exit_rect.x - rect.x, exit_rect.y - rect.y, exit_rect.width, exit_rect.height)
        self.education_exit_button.rect = local_exit_rect
        self.education_exit_button.draw(surface, self.small_font, True)
        return surface

    def draw_back_card_on_surface(self, surface: pygame.Surface, rect: pygame.Rect, alpha: int) -> None:
        if self.card_back_image is not None:
            image = pygame.transform.smoothscale(self.card_back_image, (rect.width, rect.height))
            if alpha < 255:
                image = image.copy()
                image.set_alpha(alpha)
            surface.blit(image, rect.topleft)
            return
        pygame.draw.rect(surface, (*CARD_BG, alpha), rect, border_radius=22)
        pygame.draw.rect(surface, (*CARD_BORDER, alpha), rect, width=3, border_radius=22)

    def render_education_front(self, size: tuple[int, int], exit_rect: pygame.Rect) -> pygame.Surface:
        surface = pygame.Surface(size, pygame.SRCALPHA)
        rect = surface.get_rect()
        pygame.draw.rect(surface, (8, 22, 52, 245), rect, border_radius=28)
        pygame.draw.rect(surface, (88, 196, 255, 220), rect, width=3, border_radius=28)

        title = self.hero_font.render("Details", True, TEXT_COLOR)
        subtitle = self.small_font.render("Gemini explanation of the resolved action", True, MUTED_COLOR)
        surface.blit(title, (34, 28))
        surface.blit(subtitle, (36, 92))

        content_rect = pygame.Rect(34, 132, rect.width - 68, rect.height - 210)
        pygame.draw.rect(surface, (7, 18, 40), content_rect, border_radius=20)
        pygame.draw.rect(surface, CARD_BORDER, content_rect, width=1, border_radius=20)

        body = self.education_popup["body"]
        content_surface = pygame.Surface((content_rect.width - 30, 2400), pygame.SRCALPHA)
        content_y = 0
        for paragraph in body.splitlines() or [""]:
            if not paragraph.strip():
                content_y += 16
                continue
            wrapped = self.wrap_text(paragraph, self.small_font, content_rect.width - 58, 12)
            for line in wrapped:
                text = self.small_font.render(line, True, TEXT_COLOR)
                content_surface.blit(text, (8, content_y))
                content_y += 25
            content_y += 8

        visible_height = content_rect.height - 24
        max_scroll = max(0, content_y - visible_height)
        self.education_scroll_offset = min(self.education_scroll_offset, max_scroll)
        clip = pygame.Rect(0, self.education_scroll_offset, content_rect.width - 30, visible_height)
        surface.blit(content_surface, (content_rect.x + 14, content_rect.y + 12), area=clip)

        if max_scroll > 0:
            track_rect = pygame.Rect(content_rect.right - 12, content_rect.y + 16, 6, content_rect.height - 32)
            pygame.draw.rect(surface, (15, 44, 78), track_rect, border_radius=3)
            thumb_height = max(42, int(track_rect.height * (visible_height / max(content_y, 1))))
            thumb_y = track_rect.y + int((track_rect.height - thumb_height) * (self.education_scroll_offset / max(max_scroll, 1)))
            thumb_rect = pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_height)
            pygame.draw.rect(surface, ACCENT_BLUE, thumb_rect, border_radius=3)

        close_hint = self.small_font.render("Use mouse wheel to scroll. Click the card to flip back.", True, MUTED_COLOR)
        surface.blit(close_hint, (34, rect.bottom - 56))

        local_exit_rect = pygame.Rect(exit_rect.x - rect.x, exit_rect.y - rect.y, exit_rect.width, exit_rect.height)
        self.education_exit_button.rect = local_exit_rect
        self.education_exit_button.draw(surface, self.small_font, True)
        return surface

    def update_animation(self) -> None:
        if not self.animation:
            return

        now = pygame.time.get_ticks()
        elapsed = (now - self.animation["start_ticks"]) / 1000.0

        if self.animation["type"] == "fall":
            duration = self.animation["duration"]
            if elapsed < duration:
                return
            self.winner = self.animation["winner_index"]
            self.pending_winner = None
            self.log(f"{self.players[self.winner].name} wins the duel.")
            self.animation = {
                "type": "victory",
                "winner_index": self.winner,
                "loser_index": self.animation["player_index"],
                "duration": 2.6,
                "start_ticks": pygame.time.get_ticks(),
                "label": "Victory cutscene",
            }
            self.turn_phase = "game_over"
            return

        if self.animation["type"] == "victory":
            if elapsed < self.animation["duration"]:
                return
            self.initialize_match()
            self.current_screen = "menu"
            return

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
        if self.animation and self.animation["type"] == "fall":
            context = self.finalize_education_context(moved["motions"])
            if context is not None:
                self.queued_education_context = context
            return
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
            if self.animation and self.animation["type"] == "fall":
                context = self.finalize_education_context(moved["motions"])
                if context is not None:
                    self.queued_education_context = context
                return
            if self.winner is None:
                meters = abs(target_position - start_position)
                self.log(f"{current_player.name} follows up {meters:.2f}m.")
                context = self.finalize_education_context(moved["motions"], meters)
                if context is not None:
                    self.open_education_popup(context)
            self.turn_phase = "turn_complete"
            return
        if self.winner is None:
            for motion in moved["motions"]:
                meters = abs(motion["end_pos"] - motion["start_pos"])
                self.log(
                    f"{self.players[motion['player_index']].name} slides {meters:.2f}m "
                    f"under friction {self.stage_friction:.2f}."
                )
            context = self.finalize_education_context(moved["motions"])
            if context is not None:
                self.open_education_popup(context)
        self.turn_phase = "turn_complete"

    def check_winner(self) -> None:
        if self.winner is not None or (self.animation and self.animation.get("type") == "fall"):
            return
        for index, player in enumerate(self.players):
            if player.position < 0 or player.position > STAGE_LENGTH:
                fell_left = player.position < 0
                player.position = 0.0 if fell_left else STAGE_LENGTH
                self.pending_winner = 1 - index
                self.turn_phase = "game_over"
                self.animation = {
                    "type": "fall",
                    "player_index": index,
                    "winner_index": self.pending_winner,
                    "duration": 0.95,
                    "drop_distance": 300,
                    "drift": -56 if fell_left else 56,
                    "label": "Void fall",
                    "start_ticks": pygame.time.get_ticks(),
                }
                self.log(f"{player.name} falls into the void.")
                break

    def end_turn(self) -> None:
        if self.animation or self.education_popup is not None or self.education_generation is not None or self.winner is not None:
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
        self.initialize_match()

    def open_log_view(self) -> None:
        self.log_view_open = True
        if self.battle_log_pages:
            self.log_page_index = len(self.battle_log_pages) - 1
        else:
            self.log_page_index = 0
        self.log_scroll_offset = 0

    def close_log_view(self) -> None:
        self.log_view_open = False

    def change_log_page(self, delta: int) -> None:
        if not self.battle_log_pages:
            return
        self.log_page_index = max(0, min(len(self.battle_log_pages) - 1, self.log_page_index + delta))
        self.log_scroll_offset = 0

    def current_log_page(self) -> Optional[dict]:
        if not self.battle_log_pages:
            return None
        return self.battle_log_pages[self.log_page_index]

    def scroll_log(self, amount: int) -> None:
        if not self.log_view_open:
            return
        self.log_scroll_offset = max(0, self.log_scroll_offset + amount)

    def battlefield_position(self, meters: float, rect: pygame.Rect, player_index: Optional[int] = None) -> tuple[int, int]:
        (arena_center_x, arena_center_y), arena_radius_x, _ = self.arena_geometry(rect)
        x = arena_center_x - arena_radius_x + (meters / STAGE_LENGTH) * (arena_radius_x * 2)
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

        if (
            player_index is not None
            and self.animation
            and self.animation["type"] == "fall"
            and self.animation["player_index"] == player_index
        ):
            elapsed = (pygame.time.get_ticks() - self.animation["start_ticks"]) / 1000.0
            progress = min(1.0, elapsed / self.animation["duration"])
            eased = progress * progress
            x += self.animation["drift"] * eased
            y += self.animation["drop_distance"] * eased

        return int(x), int(y)

    def point_in_arena(self, pos: tuple[int, int], rect: pygame.Rect) -> bool:
        center, radius_x, radius_y = self.arena_geometry(rect)
        dx = pos[0] - center[0]
        dy = pos[1] - center[1]
        return ((dx * dx) / ((radius_x + 22) ** 2)) + ((dy * dy) / ((radius_y + 22) ** 2)) <= 1.0

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
            arena_center, _, _ = self.arena_geometry(self.board_rect)
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

    def draw_back_card(self, rect: pygame.Rect, angle: float = 0.0, alpha: int = 255) -> None:
        if self.card_back_image is not None:
            image = pygame.transform.smoothscale(self.card_back_image, (rect.width, rect.height))
            if angle:
                image = pygame.transform.rotate(image, angle)
            if alpha < 255:
                image = image.copy()
                image.set_alpha(alpha)
            image_rect = image.get_rect(center=rect.center)
            self.screen.blit(image, image_rect.topleft)
            return

        fallback = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        fallback.fill((*CARD_BG, alpha))
        pygame.draw.rect(fallback, (*CARD_BORDER, alpha), fallback.get_rect(), width=3, border_radius=16)
        pygame.draw.rect(fallback, (*ACCENT_BLUE, min(255, alpha)), pygame.Rect(10, 12, rect.width - 20, 12), border_radius=6)
        if angle:
            fallback = pygame.transform.rotate(fallback, angle)
        fallback_rect = fallback.get_rect(center=rect.center)
        self.screen.blit(fallback, fallback_rect.topleft)

    def draw_victory_cutscene(self) -> None:
        if not self.animation or self.animation["type"] != "victory" or self.winner is None:
            return

        progress = min(1.0, (pygame.time.get_ticks() - self.animation["start_ticks"]) / (self.animation["duration"] * 1000.0))
        eased = 1.0 - ((1.0 - progress) ** 3)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 6, 18, min(170, int(170 * (0.35 + eased * 0.65)))))
        self.screen.blit(overlay, (0, 0))

        bar_height = int(86 * min(1.0, eased * 1.4))
        if bar_height > 0:
            top_bar = pygame.Surface((SCREEN_WIDTH, bar_height), pygame.SRCALPHA)
            top_bar.fill((2, 12, 30, 235))
            bottom_bar = pygame.Surface((SCREEN_WIDTH, bar_height), pygame.SRCALPHA)
            bottom_bar.fill((2, 12, 30, 235))
            self.screen.blit(top_bar, (0, 0))
            self.screen.blit(bottom_bar, (0, SCREEN_HEIGHT - bar_height))

        winner = self.players[self.winner]
        winner_x, winner_y = self.battlefield_position(max(0.0, min(STAGE_LENGTH, winner.position)), self.board_rect, self.winner)
        spotlight_radius = 88 + int(18 * math.sin(progress * math.pi * 3.0))
        spotlight_surface = pygame.Surface((spotlight_radius * 2 + 40, spotlight_radius * 2 + 40), pygame.SRCALPHA)
        center = (spotlight_surface.get_width() // 2, spotlight_surface.get_height() // 2)
        pygame.draw.circle(spotlight_surface, (*ACCENT_BLUE, 42), center, spotlight_radius + 14)
        pygame.draw.circle(spotlight_surface, (*ACCENT_GOLD, 120), center, spotlight_radius, 3)
        pygame.draw.circle(spotlight_surface, (*ACCENT_BLUE, 190), center, spotlight_radius - 18, 2)
        self.screen.blit(spotlight_surface, (winner_x - center[0], winner_y - center[1]))

        title_y = 120 - int((1.0 - eased) * 40)
        title = self.hero_font.render("Victory", True, TEXT_COLOR)
        name = self.title_font.render(f"{winner.name.upper()} controls the arena", True, ACCENT_BLUE)
        hint = self.small_font.render("Press R or click Restart Match to begin the next duel.", True, MUTED_COLOR)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, title_y)))
        self.screen.blit(name, name.get_rect(center=(SCREEN_WIDTH // 2, title_y + 58)))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 74)))

        subtitle = self.small_font.render("Winning Cutscene", True, ACCENT_GOLD)
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, title_y - 36)))

    def draw_side_hand_stacks(self, rect: pygame.Rect) -> None:
        card_size = (92, 126)
        now = pygame.time.get_ticks()
        for player_index, player in enumerate(self.players):
            anchor_x, anchor_y = self.side_stack_anchor(rect, player_index)
            is_active = player_index == self.current_player_index and self.winner is None
            panel_rect = pygame.Rect(0, 0, 124, 182)
            panel_rect.center = (anchor_x, anchor_y)
            fill = (12, 34, 74, 205) if is_active else (8, 20, 46, 182)
            border = ACCENT_BLUE if is_active else CARD_BORDER
            self.draw_overlay_panel(panel_rect, fill, border, radius=22)

            stack_count = min(4, max(1, len(player.hand))) if player.hand else 0
            for layer in range(stack_count):
                offset = layer * 6
                card_rect = pygame.Rect(
                    panel_rect.centerx - card_size[0] // 2 + (offset if player_index == 0 else -offset),
                    panel_rect.y + 26 + layer * 2,
                    card_size[0],
                    card_size[1],
                )
                self.draw_back_card(card_rect, angle=(-4 + layer * 2) if player_index == 0 else (4 - layer * 2), alpha=220)

            if self.deal_sequence:
                for pulse in self.deal_sequence["pulses"]:
                    if pulse["player_index"] != player_index:
                        continue
                    progress = min(1.0, (now - pulse["start_ticks"]) / self.deal_sequence["pulse_duration"])
                    pulse_radius = 18 + int(progress * 32)
                    pulse_alpha = max(0, 180 - int(progress * 180))
                    pulse_surface = pygame.Surface((pulse_radius * 2 + 6, pulse_radius * 2 + 6), pygame.SRCALPHA)
                    pygame.draw.circle(
                        pulse_surface,
                        (*ACCENT_BLUE, pulse_alpha),
                        (pulse_surface.get_width() // 2, pulse_surface.get_height() // 2),
                        pulse_radius,
                        3,
                    )
                    self.screen.blit(
                        pulse_surface,
                        (
                            panel_rect.centerx - pulse_surface.get_width() // 2,
                            panel_rect.centery - 10 - pulse_surface.get_height() // 2,
                        ),
                    )

            name = self.small_font.render(player.name, True, TEXT_COLOR)
            count = self.body_font.render(str(len(player.hand)), True, TEXT_COLOR)
            self.screen.blit(name, name.get_rect(center=(panel_rect.centerx, panel_rect.y + 16)))
            self.screen.blit(count, count.get_rect(center=(panel_rect.centerx, panel_rect.bottom - 22)))

    def draw_deal_sequence(self, rect: pygame.Rect) -> None:
        if not self.deal_sequence:
            return

        sequence = self.deal_sequence
        now = pygame.time.get_ticks()
        deck_center = self.deck_anchor(rect)
        deck_rect = pygame.Rect(0, 0, 94, 128)
        deck_rect.center = deck_center

        caption = self.small_font.render(sequence["caption"], True, TEXT_COLOR)
        self.screen.blit(caption, caption.get_rect(center=(deck_center[0], deck_center[1] - 112)))

        if sequence["phase"] == "shuffle":
            shuffle_progress = min(1.0, (now - sequence["start_ticks"]) / sequence["shuffle_duration"])
            wave = math.sin(shuffle_progress * math.pi * 4.0)
            for layer in range(4):
                offset = (layer - 1.5) * 10
                card_rect = deck_rect.move(int(offset + wave * 18 * ((-1) ** layer)), -layer * 3)
                self.draw_back_card(card_rect, angle=wave * (8 - layer), alpha=255 - layer * 18)
        else:
            for layer in range(3):
                self.draw_back_card(deck_rect.move(0, -layer * 3), alpha=255 - layer * 22)

        for moving_card in sequence["active_cards"]:
            progress = min(1.0, (now - moving_card["start_ticks"]) / sequence["travel_duration"])
            eased = 1.0 - ((1.0 - progress) ** 3)
            target_x, target_y = self.deal_target_anchor(rect, moving_card["player_index"])
            start_x, start_y = deck_center
            x = start_x + (target_x - start_x) * eased
            y = start_y + (target_y - start_y) * eased - math.sin(eased * math.pi) * 62
            card_rect = pygame.Rect(0, 0, 86, 118)
            card_rect.center = (int(x), int(y))
            self.draw_back_card(card_rect, angle=(1.0 - eased) * (12 if moving_card["player_index"] == 0 else -12))

        for pulse in sequence["pulses"]:
            target_x, target_y = self.deal_target_anchor(rect, pulse["player_index"])
            progress = min(1.0, (now - pulse["start_ticks"]) / sequence["pulse_duration"])
            pulse_radius = 18 + int(progress * 28)
            pulse_alpha = max(0, 180 - int(progress * 180))
            pulse_surface = pygame.Surface((pulse_radius * 2 + 6, pulse_radius * 2 + 6), pygame.SRCALPHA)
            pygame.draw.circle(
                pulse_surface,
                (*ACCENT_BLUE, pulse_alpha),
                (pulse_surface.get_width() // 2, pulse_surface.get_height() // 2),
                pulse_radius,
                3,
            )
            self.screen.blit(
                pulse_surface,
                (target_x - pulse_surface.get_width() // 2, target_y - pulse_surface.get_height() // 2),
            )

        info = self.tiny_font.render("Opening hands and round draws are dealt from the central deck.", True, MUTED_COLOR)
        self.screen.blit(info, info.get_rect(center=(deck_center[0], deck_center[1] + 96)))

    def draw_background(self) -> None:
        self.screen.fill(BG_COLOR)
        glow_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, (*BG_WASH, 70), (SCREEN_WIDTH // 2, 280), 340)
        pygame.draw.circle(glow_surface, (*ACCENT_BLUE, 38), (SCREEN_WIDTH // 2, 280), 250)
        pygame.draw.circle(glow_surface, (*ACCENT_BLUE, 18), (220, 120), 190)
        pygame.draw.circle(glow_surface, (*ACCENT_BLUE, 18), (SCREEN_WIDTH - 200, 120), 210)
        self.screen.blit(glow_surface, (0, 0))

        for x in range(0, SCREEN_WIDTH, 56):
            pygame.draw.line(self.screen, BG_LINE, (x, 0), (x, SCREEN_HEIGHT), 1)
        for y in range(0, SCREEN_HEIGHT, 56):
            pygame.draw.line(self.screen, BG_LINE, (0, y), (SCREEN_WIDTH, y), 1)

    def draw(self) -> None:
        self.draw_background()

        if self.current_screen != "game":
            if self.current_screen == "menu":
                self.draw_menu()
            elif self.current_screen == "instruction":
                self.draw_instruction_screen()
            else:
                self.draw_info_screen(
                    "About Us",
                    [
                        "Physics Card Duel is a local pygame prototype built from your physics setting.",
                        "It mixes force, friction, energy management, and positional play into a PvP card duel.",
                        "The project is designed as a playable learning game with a strong visual card focus.",
                    ],
                )
            pygame.display.flip()
            return

        board_rect = pygame.Rect(12, 12, SCREEN_WIDTH - 24, SCREEN_HEIGHT - 24)
        hud_rect = pygame.Rect(28, 28, 360, 142)
        friction_rect = pygame.Rect(SCREEN_WIDTH - 206, 28, 178, 44)
        hand_rect = pygame.Rect(24, SCREEN_HEIGHT - 312, SCREEN_WIDTH - 48, 288)
        self.board_rect = board_rect

        self.end_turn_button.rect = pygame.Rect(SCREEN_WIDTH - 314, SCREEN_HEIGHT - 128, 270, 48)
        self.reset_button.rect = pygame.Rect(SCREEN_WIDTH - 314, SCREEN_HEIGHT - 72, 270, 40)
        self.log_button.rect = pygame.Rect(SCREEN_WIDTH - 314, SCREEN_HEIGHT - 176, 270, 40)
        self.education_toggle_button.rect = pygame.Rect(SCREEN_WIDTH - 314, SCREEN_HEIGHT - 224, 270, 40)

        self.draw_board(board_rect)
        self.draw_header(hud_rect)
        self.draw_turn_banner()
        self.draw_friction_chip(friction_rect)
        self.draw_side_hand_stacks(board_rect)
        self.draw_deal_sequence(board_rect)
        self.draw_hand(hand_rect)
        self.draw_dragging_card()
        self.draw_card_use_animation()

        can_end_turn = (
            not self.log_view_open
            and self.education_popup is None
            and self.education_generation is None
            and not self.animation
            and not self.deal_sequence
            and self.winner is None
            and self.turn_phase in {"playing", "turn_complete"}
        )
        self.education_toggle_button.label = "Education: On" if self.education_enabled else "Education: Off"
        self.education_toggle_button.draw(self.screen, self.small_font, True)
        self.log_button.draw(self.screen, self.small_font, True)
        self.end_turn_button.draw(self.screen, self.body_font, can_end_turn)
        self.reset_button.draw(self.screen, self.small_font, True)

        if self.deal_sequence:
            prompt = "Cards are being dealt. Wait for the draw sequence to finish."
        elif not self.education_enabled:
            prompt = "Education mode is off. Toggle it on to see Gemini physics explanations."
        elif self.education_generation is not None:
            prompt = "Generating the physics explanation before showing the flip card."
        elif self.selected_card_index is not None and self.turn_phase == "playing":
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

        self.draw_victory_cutscene()
        self.draw_education_popup()

        if self.log_view_open:
            self.draw_log_overlay()

        self.draw_transition_overlay()

        pygame.display.flip()

    def draw_log_overlay(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((2, 8, 20, 188))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(0, 0, 980, 690)
        panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.draw_overlay_panel(panel, (8, 22, 52, 242), (88, 196, 255, 220), radius=28)

        page = self.current_log_page()
        title_text = "Battle Log" if page is None else f"Battle Log - {page['title']}"
        title = self.hero_font.render(title_text, True, TEXT_COLOR)
        self.screen.blit(title, (panel.x + 34, panel.y + 28))

        page_counter = self.small_font.render(
            f"Page {self.log_page_index + 1}/{max(1, len(self.battle_log_pages))}",
            True,
            MUTED_COLOR,
        )
        self.screen.blit(page_counter, (panel.right - 160, panel.y + 54))

        log_view_rect = pygame.Rect(panel.x + 36, panel.y + 132, panel.width - 72, panel.height - 232)
        pygame.draw.rect(self.screen, (7, 18, 40), log_view_rect, border_radius=20)
        pygame.draw.rect(self.screen, CARD_BORDER, log_view_rect, width=1, border_radius=20)

        content_surface = pygame.Surface((log_view_rect.width - 28, 2000), pygame.SRCALPHA)
        content_y = 0
        if page is None or not page["entries"]:
            empty = self.body_font.render("No battle log entries yet.", True, MUTED_COLOR)
            content_surface.blit(empty, (8, 8))
            content_y = 40
        else:
            for entry_index, entry in enumerate(page["entries"], start=1):
                bullet = self.small_font.render(f"{entry_index}.", True, TEXT_COLOR)
                content_surface.blit(bullet, (4, content_y + 2))
                wrapped = self.wrap_text(entry, self.small_font, log_view_rect.width - 86, 5)
                for line in wrapped:
                    text = self.small_font.render(line, True, TEXT_COLOR)
                    content_surface.blit(text, (34, content_y))
                    content_y += 26
                content_y += 10

        visible_height = log_view_rect.height - 24
        max_scroll = max(0, content_y - visible_height)
        self.log_scroll_offset = min(self.log_scroll_offset, max_scroll)
        content_clip = pygame.Rect(0, self.log_scroll_offset, log_view_rect.width - 28, visible_height)
        self.screen.blit(content_surface, (log_view_rect.x + 14, log_view_rect.y + 12), area=content_clip)

        if max_scroll > 0:
            track_rect = pygame.Rect(log_view_rect.right - 12, log_view_rect.y + 16, 6, log_view_rect.height - 32)
            pygame.draw.rect(self.screen, (15, 44, 78), track_rect, border_radius=3)
            thumb_height = max(42, int(track_rect.height * (visible_height / max(content_y, 1))))
            thumb_y = track_rect.y + int((track_rect.height - thumb_height) * (self.log_scroll_offset / max(max_scroll, 1)))
            thumb_rect = pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_height)
            pygame.draw.rect(self.screen, ACCENT_BLUE, thumb_rect, border_radius=3)

        self.log_prev_button.rect = pygame.Rect(panel.x + 36, panel.bottom - 74, 140, 42)
        self.log_next_button.rect = pygame.Rect(panel.x + 188, panel.bottom - 74, 140, 42)
        self.log_close_button.rect = pygame.Rect(panel.right - 176, panel.bottom - 74, 140, 42)
        self.log_prev_button.draw(self.screen, self.small_font, self.log_page_index > 0)
        self.log_next_button.draw(self.screen, self.small_font, self.log_page_index < len(self.battle_log_pages) - 1)
        self.log_close_button.draw(self.screen, self.small_font, True)

        hint = self.small_font.render("Use mouse wheel to scroll this round's actions.", True, MUTED_COLOR)
        self.screen.blit(hint, (panel.x + 36, panel.bottom - 116))

    def draw_menu(self) -> None:
        title = self.hero_font.render("Physics Card Duel", True, TEXT_COLOR)
        subtitle = self.body_font.render("A local PvP card game powered by force, friction, and timing.", True, MUTED_COLOR)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 190)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 246)))

        menu_panel = pygame.Rect(0, 0, 420, 300)
        menu_panel.center = (SCREEN_WIDTH // 2, 500)
        self.draw_overlay_panel(menu_panel, (10, 24, 56, 220), (88, 196, 255, 200), radius=28)

        labels = ["play", "instruction", "about"]
        for index, key in enumerate(labels):
            button = self.menu_buttons[key]
            button.rect.center = (menu_panel.centerx, menu_panel.y + 78 + index * 78)
            button.draw(self.screen, self.menu_font, True)

        footer = self.small_font.render("Choose an option to begin.", True, MUTED_COLOR)
        self.screen.blit(footer, footer.get_rect(center=(SCREEN_WIDTH // 2, menu_panel.bottom + 36)))

    def draw_info_screen(self, title_text: str, lines: List[str]) -> None:
        panel = pygame.Rect(0, 0, 980, 600)
        panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.draw_overlay_panel(panel, (10, 24, 56, 225), (88, 196, 255, 210), radius=28)

        title = self.hero_font.render(title_text, True, TEXT_COLOR)
        self.screen.blit(title, (panel.x + 42, panel.y + 42))

        y = panel.y + 150
        for line in lines:
            wrapped = self.wrap_text(line, self.body_font, panel.width - 84, 3)
            for wrapped_line in wrapped:
                text = self.body_font.render(wrapped_line, True, TEXT_COLOR)
                self.screen.blit(text, (panel.x + 42, y))
                y += 34
            y += 10

        self.back_button.rect = pygame.Rect(panel.x + 42, panel.bottom - 82, 180, 46)
        self.back_button.draw(self.screen, self.body_font, True)

    def draw_instruction_screen(self) -> None:
        panel = pygame.Rect(0, 0, 980, 620)
        panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.draw_overlay_panel(panel, (10, 24, 56, 225), (88, 196, 255, 210), radius=28)

        title = self.hero_font.render("How To Play", True, TEXT_COLOR)
        self.screen.blit(title, (panel.x + 42, panel.y + 42))

        info_lines = [
            "1. Each player starts with 5 energy and 2 cards.",
            "2. At the start of every turn, the active player gains 2 energy and draws 2 cards.",
            "3. Drag a card from the bottom row into the arena to use it.",
            "4. You may use effect cards first, then one action card for the turn.",
            "5. Force cards push the opponent. Dodge prepares an evasion against the next shove.",
            "6. Smooth lowers friction and Rough raises friction.",
            "7. Push the other player past the edge of the stage to win.",
        ]
        y = panel.y + 150
        for line in info_lines:
            wrapped = self.wrap_text(line, self.body_font, panel.width - 84, 3)
            for wrapped_line in wrapped:
                text = self.body_font.render(wrapped_line, True, TEXT_COLOR)
                self.screen.blit(text, (panel.x + 42, y))
                y += 34
            y += 8

        self.back_button.rect = pygame.Rect(panel.x + 42, panel.bottom - 82, 180, 46)
        self.back_button.draw(self.screen, self.body_font, True)

    def draw_transition_overlay(self) -> None:
        if not self.transition:
            return
        progress = self.transition_progress()
        alpha = int((1.0 - progress) * 235)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((4, 10, 28, alpha))
        self.screen.blit(overlay, (0, 0))

        title_alpha = int((1.0 - progress) * 255)
        title_surface = self.hero_font.render("Entering Arena", True, TEXT_COLOR)
        title_surface.set_alpha(title_alpha)
        self.screen.blit(title_surface, title_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

    def draw_header(self, rect: pygame.Rect) -> None:
        current = self.current_player()
        self.draw_overlay_panel(rect, (9, 24, 58, 225), (88, 196, 255, 180))
        title = self.body_font.render("Physics Card Duel", True, TEXT_COLOR)
        subtitle = self.small_font.render(f"Round {self.round_number}", True, MUTED_COLOR)
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

    def draw_turn_banner(self) -> None:
        if self.current_screen != "game":
            return
        rect = pygame.Rect(0, 0, 240, 50)
        rect.midtop = (SCREEN_WIDTH // 2, 22)
        self.draw_overlay_panel(rect, (9, 24, 58, 225), (88, 196, 255, 190), radius=18)
        label = self.small_font.render("Current Turn", True, MUTED_COLOR)
        value = self.body_font.render(self.current_player().name, True, TEXT_COLOR)
        self.screen.blit(label, label.get_rect(center=(rect.centerx, rect.y + 15)))
        self.screen.blit(value, value.get_rect(center=(rect.centerx, rect.y + 35)))

    def draw_friction_chip(self, rect: pygame.Rect) -> None:
        self.draw_overlay_panel(rect, (9, 24, 58, 225), (88, 196, 255, 180), radius=16)
        label = self.tiny_font.render("Coefficient of Friction", True, MUTED_COLOR)
        value = self.body_font.render(f"{self.stage_friction:.2f}", True, TEXT_COLOR)
        self.screen.blit(label, (rect.x + 14, rect.y + 8))
        self.screen.blit(value, (rect.right - value.get_width() - 16, rect.y + 16))

    def draw_card_frame(self, card_rect: pygame.Rect, card: Card, selected: bool, playable: bool) -> None:
        fill = CARD_BG if playable else CARD_DISABLED
        border = ACCENT_GOLD if selected else CARD_BORDER
        strip = ACCENT_BLUE if card.kind in {"force", "conservation", "smooth"} else ACCENT_RED if card.kind == "rough" else ACCENT_GREEN
        image = self.card_images.get(card.name)

        if image is not None:
            image_width, image_height = image.get_size()
            scale = min(card_rect.width / image_width, card_rect.height / image_height)
            scaled_size = (max(1, int(image_width * scale)), max(1, int(image_height * scale)))
            scaled = pygame.transform.smoothscale(image, scaled_size)
            image_rect = scaled.get_rect(center=card_rect.center)
            self.screen.blit(scaled, image_rect.topleft)
            if selected:
                glow_rect = image_rect.inflate(14, 14)
                glow = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*ACCENT_BLUE, 55), glow.get_rect(), border_radius=24)
                pygame.draw.rect(glow, ACCENT_BLUE, glow.get_rect(), width=2, border_radius=24)
                self.screen.blit(glow, glow_rect.topleft)
                self.screen.blit(scaled, image_rect.topleft)
            if not playable:
                disabled_overlay = pygame.Surface((scaled_size[0], scaled_size[1]), pygame.SRCALPHA)
                disabled_overlay.fill((12, 20, 34, 150))
                self.screen.blit(disabled_overlay, image_rect.topleft)
            return

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
        draw_rect = pygame.Rect(mouse_x - offset_x, mouse_y - offset_y, self.hand_card_width, self.hand_card_height)
        self.draw_card_frame(draw_rect, card, True, self.can_play(player, card))

    def draw_card_use_animation(self) -> None:
        if not self.card_use_animation:
            return
        rect = self.current_card_use_rect()
        if rect is None:
            return
        self.draw_card_frame(rect, self.card_use_animation["card"], True, True)

    def draw_board(self, rect: pygame.Rect) -> None:
        arena_center, arena_radius_x, arena_radius_y = self.arena_geometry(rect)
        arena_rect = self.arena_ellipse_rect(rect)
        outer_rect = arena_rect.inflate(92, 92)
        mid_rect = arena_rect.inflate(44, 44)
        inner_rect = arena_rect.inflate(-22, -22)

        glow_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for inflate_x, inflate_y, alpha in [(120, 120, 22), (82, 82, 30), (44, 44, 52)]:
            glow_rect = arena_rect.inflate(inflate_x, inflate_y)
            pygame.draw.ellipse(glow_surface, (*ACCENT_BLUE, alpha), glow_rect)
        self.screen.blit(glow_surface, (0, 0))

        pygame.draw.ellipse(self.screen, VOID_COLOR, outer_rect)
        pygame.draw.ellipse(self.screen, (7, 20, 46), mid_rect)
        pygame.draw.ellipse(self.screen, STAGE_COLOR, arena_rect)

        arena_surface = pygame.Surface((arena_rect.width, arena_rect.height), pygame.SRCALPHA)
        grid_surface = pygame.Surface((arena_rect.width, arena_rect.height), pygame.SRCALPHA)
        mask_surface = pygame.Surface((arena_rect.width, arena_rect.height), pygame.SRCALPHA)
        pygame.draw.ellipse(mask_surface, (255, 255, 255, 255), mask_surface.get_rect())
        arena_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MAX)
        arena_surface.fill((0, 0, 0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.ellipse(arena_surface, (14, 34, 74, 255), arena_surface.get_rect())

        for x in range(0, arena_rect.width, 46):
            line_color = (*ACCENT_BLUE, 46 if x % 92 else 72)
            pygame.draw.line(grid_surface, line_color, (x, 0), (x, arena_rect.height), 1)
        for y in range(0, arena_rect.height, 46):
            line_color = (*ACCENT_BLUE, 42 if y % 92 else 68)
            pygame.draw.line(grid_surface, line_color, (0, y), (arena_rect.width, y), 1)
        grid_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        arena_surface.blit(grid_surface, (0, 0))
        self.screen.blit(arena_surface, arena_rect.topleft)

        pygame.draw.ellipse(self.screen, ACCENT_BLUE, outer_rect, 2)
        pygame.draw.ellipse(self.screen, ACCENT_GOLD, mid_rect, 2)
        pygame.draw.ellipse(self.screen, ACCENT_BLUE, arena_rect, 3)
        pygame.draw.ellipse(self.screen, ACCENT_GOLD, inner_rect, 2)

        top_bracket = pygame.Rect(arena_center[0] - 74, arena_rect.y - 8, 148, 12)
        bottom_bracket = pygame.Rect(arena_center[0] - 74, arena_rect.bottom - 4, 148, 12)
        pygame.draw.rect(self.screen, ACCENT_BLUE, top_bracket, border_radius=4)
        pygame.draw.rect(self.screen, ACCENT_BLUE, bottom_bracket, border_radius=4)

        left_bound = self.battlefield_position(0.0, rect)
        center_mark = self.battlefield_position(STAGE_LENGTH / 2, rect)
        right_bound = self.battlefield_position(STAGE_LENGTH, rect)
        pygame.draw.line(self.screen, ACCENT_GOLD, left_bound, right_bound, 3)
        for meter in [0, 5, 10, 15, 20, 25]:
            x, y = self.battlefield_position(float(meter), rect)
            pygame.draw.line(self.screen, ACCENT_BLUE, (x, y - 12), (x, y + 12), 2)
            label = self.tiny_font.render(str(meter), True, MUTED_COLOR)
            self.screen.blit(label, (x - label.get_width() // 2, arena_center[1] + arena_radius_y + 20))
        pygame.draw.circle(self.screen, ACCENT_GOLD, center_mark, 5)

        for index, player in enumerate(self.players):
            clamped = max(0.0, min(STAGE_LENGTH, player.position))
            x, y = self.battlefield_position(clamped, rect, index)
            color = ACCENT_BLUE if index == 0 else ACCENT_RED
            radius = 20
            alpha = 255
            if self.animation and self.animation["type"] == "fall" and self.animation["player_index"] == index:
                elapsed = (pygame.time.get_ticks() - self.animation["start_ticks"]) / 1000.0
                progress = min(1.0, elapsed / self.animation["duration"])
                radius = max(10, int(radius * (1.0 - (progress * 0.24))))
                alpha = max(55, int(255 * (1.0 - progress * 0.72)))
            facing = int(self.player_facing_direction(index))
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
                glow_radius = radius + (10 if alpha == 255 else 6)
                pygame.draw.circle(self.screen, GLOW_COLOR, (x, y), glow_radius)

            player_surface = pygame.Surface((radius * 6, radius * 6), pygame.SRCALPHA)
            center = (player_surface.get_width() // 2, player_surface.get_height() // 2)
            offset = (center[0] - x, center[1] - y)

            def shift(point: tuple[int, int]) -> tuple[int, int]:
                return point[0] + offset[0], point[1] + offset[1]

            arm_color = (*TEXT_COLOR, alpha)
            hand_color = (*ACCENT_GOLD, alpha)
            body_color = (*color, alpha)
            outline_color = (*TEXT_COLOR, alpha)
            pygame.draw.line(player_surface, arm_color, shift(shoulder_front), shift(front_hand), 4)
            pygame.draw.line(player_surface, arm_color, shift(shoulder_rear), shift(rear_hand), 4)
            pygame.draw.circle(player_surface, hand_color, shift(front_hand), 4)
            pygame.draw.circle(player_surface, hand_color, shift(rear_hand), 4)
            pygame.draw.circle(player_surface, body_color, center, radius)
            pygame.draw.circle(player_surface, outline_color, center, radius, 3)
            self.screen.blit(player_surface, (x - center[0], y - center[1]))
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
            elif self.animation["type"] == "motion":
                display_force = int(self.animation["motions"][0]["force"])
                label_text = f"{self.animation['label']}: {display_force}N resolving"
            else:
                display_force = 0
                label_text = "Void fall resolving"
            if self.animation["type"] != "fall":
                label_text = f"{self.animation['label']}: {display_force}N resolving"
            anim_text = self.small_font.render(label_text, True, TEXT_COLOR)
            self.screen.blit(anim_text, (rect.right - 340, rect.y + 24))

        if self.winner is not None and not (self.animation and self.animation["type"] == "victory"):
            win_text = self.title_font.render(f"{self.players[self.winner].name} Wins", True, ACCENT_GREEN)
            self.screen.blit(win_text, (rect.right - 320, rect.y + 62))
        elif self.animation and self.animation["type"] == "fall":
            void_text = self.title_font.render("Void Breach", True, ACCENT_BLUE)
            self.screen.blit(void_text, (rect.right - 320, rect.y + 62))

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
        if self.deal_sequence:
            current_rect = pygame.Rect(rect.x, rect.y + 20, rect.width, rect.height - 20)
            label = self.body_font.render(f"{self.current_player().name} hand", True, MUTED_COLOR)
            self.screen.blit(label, label.get_rect(midtop=(current_rect.centerx, current_rect.y)))
            self.card_rects = []
            return

        player = self.current_player()
        self.card_rects = []
        if not player.hand:
            empty = self.body_font.render("No cards in hand.", True, MUTED_COLOR)
            self.screen.blit(empty, (rect.x + 20, rect.y + 20))
            return

        cards_per_row = MAX_HAND_SIZE
        gap_x = 14
        gap_y = 0
        card_width = self.hand_card_width
        card_height = self.hand_card_height
        total_row_width = (card_width * cards_per_row) + (gap_x * (cards_per_row - 1))
        start_x = rect.x + max(20, (rect.width - total_row_width) // 2)

        for index, card in enumerate(player.hand[:MAX_HAND_SIZE]):
            row = index // cards_per_row
            col = index % cards_per_row
            card_rect = pygame.Rect(
                start_x + col * (card_width + gap_x),
                rect.bottom - card_height,
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

    def handle_log_click(self, pos) -> bool:
        if not self.log_view_open:
            return False
        if self.log_close_button.contains(pos):
            self.close_log_view()
            return True
        if self.log_prev_button.contains(pos) and self.log_page_index > 0:
            self.change_log_page(-1)
            return True
        if self.log_next_button.contains(pos) and self.log_page_index < len(self.battle_log_pages) - 1:
            self.change_log_page(1)
            return True
        return True

    def handle_menu_click(self, pos) -> None:
        if self.current_screen == "menu":
            if self.menu_buttons["play"].contains(pos):
                self.initialize_match(animated_setup=True)
                self.begin_game_transition()
            elif self.menu_buttons["instruction"].contains(pos):
                self.current_screen = "instruction"
            elif self.menu_buttons["about"].contains(pos):
                self.current_screen = "about"
        elif self.current_screen in {"instruction", "about"} and self.back_button.contains(pos):
            self.current_screen = "menu"

    def run(self) -> None:
        running = True
        while running:
            self.clock.tick(FPS)
            self.update_card_use_animation()
            self.update_animation()
            self.update_education_generation()
            self.update_deal_sequence()
            self.update_transition()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.current_screen == "game" and self.education_popup is not None:
                            self.close_education_popup()
                        elif self.current_screen == "game" and self.log_view_open:
                            self.close_log_view()
                        elif self.current_screen == "game":
                            running = False
                        elif self.current_screen in {"instruction", "about"}:
                            self.current_screen = "menu"
                    elif self.current_screen != "game":
                        continue
                    elif event.key == pygame.K_SPACE:
                        self.play_selected_card()
                    elif event.key == pygame.K_RETURN:
                        if not self.animation and self.winner is None and self.turn_phase in {"playing", "turn_complete"}:
                            self.end_turn()
                    elif event.key == pygame.K_r:
                        self.restart()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.current_screen != "game":
                        self.handle_menu_click(event.pos)
                        continue
                    if self.education_popup is not None:
                        self.handle_education_click(event.pos)
                        continue
                    if self.log_view_open:
                        self.handle_log_click(event.pos)
                        continue
                    if self.reset_button.contains(event.pos):
                        self.restart()
                    elif self.education_toggle_button.contains(event.pos):
                        self.toggle_education_enabled()
                    elif self.log_button.contains(event.pos):
                        self.open_log_view()
                    elif self.end_turn_button.contains(event.pos):
                        if not self.animation and self.winner is None and self.turn_phase in {"playing", "turn_complete"}:
                            self.end_turn()
                    else:
                        self.on_card_click(event.pos)
                elif event.type == pygame.MOUSEWHEEL:
                    if self.current_screen == "game" and self.education_popup is not None:
                        self.scroll_education_popup(-event.y * 36)
                    elif self.current_screen == "game" and self.log_view_open:
                        self.scroll_log(-event.y * 36)
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
