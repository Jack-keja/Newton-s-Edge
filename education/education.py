from __future__ import annotations

from typing import Any


def _format_effects(effects: list[str]) -> str:
    return ", ".join(effects) if effects else "None"


def _reaction_card_name(context: dict[str, Any]) -> str | None:
    enemy_response = str(context.get("enemy_response", "")).lower()
    if enemy_response in {"dodge success", "dodge failed"}:
        return "Dodge"
    return None


def build_physics_prompt(context: dict[str, Any]) -> str:
    effects_text = _format_effects(context["effect_cards"])
    motion_lines = []
    for motion in context["motions"]:
        motion_lines.append(
            (
                f"- {motion['subject']} moved {motion['distance']:.2f} m with initial speed "
                f"{motion['initial_velocity']:.2f} m/s, friction deceleration "
                f"{motion['friction_accel']:.2f} m/s^2, and motion time {motion['duration']:.2f} s."
            )
        )
    motion_text = "\n".join(motion_lines) if motion_lines else "- No linear motion resolved."
    return f"""Role: You are a Physics Engine for a tactical card game. Your job is to translate game mechanics into realistic physical consequences. Explain the interaction using real-world physics principles (Newton’s Laws, momentum, etc.) in a way that is accessible to a high schooler.
    
    Context Constants:
    - Target Mass: {context['mass']:.1f} kg
    - Gravity: {context['gravity']:.2f} m/s²
    - Impact Duration: {context['impact_time']:.2f} s
    - Friction (mu): {context['friction']:.2f}

    Interaction Data:
    - Action: {context['actor']} used {context['action_card']} ({context['action_kind']}) on {context['target']}.
    - Force Applied: {context['force']:.0f} N
    - Modifiers: {effects_text} | Enemy Response: {context['enemy_response']}
    - Motion Data: {motion_text}

    Constraint: Total response must be under 150 words, using plain text. Use the exact numbers provided.

    Required Format: 
    1. Physics Breakdown: (Name the core principle, e.g., "Inertia" or "Impulse").
    2. Calculation: (Show a simple $F = ma$ or $p = mv$ calculation using the numbers).
    3. What Happened: (Describe the visual impact briefly)."""


def build_local_explanation(context: dict[str, Any]) -> str:
    effects_text = _format_effects(context["effect_cards"])
    lines = [
        "Physics Breakdown:",
    ]
    if context["action_kind"] == "force":
        lines.append(
            (
                f"{context['actor']} used {context['action_card']} with {effects_text} active. "
                f"The push uses impulse, where force over the impact time changes velocity, and "
                f"friction then slows the sliding object."
            )
        )
    else:
        lines.append(
            (
                f"{context['actor']} used {context['action_card']} with {effects_text} active. "
                f"This stores an evasive state, so no direct shove calculation happens yet."
            )
        )

    lines.append("")
    lines.append("Calculation:")
    if context["action_kind"] == "force":
        base_velocity = context["force"] * context["impact_time"] / context["mass"]
        friction_accel = context["friction"] * context["gravity"]
        lines.append(
            f"Impulse model: delta_v = F*dt/m = {context['force']:.0f}*{context['impact_time']:.2f}/{context['mass']:.1f} = {base_velocity:.2f} m/s."
        )
        lines.append(f"Friction model: a_f = mu*g = {context['friction']:.2f}*{context['gravity']:.2f} = {friction_accel:.2f} m/s^2.")
        if context["motions"]:
            motion = context["motions"][0]
            lines.append(
                (
                    f"Slide distance: d = v0*t - 0.5*a*t^2 = {motion['initial_velocity']:.2f}*{motion['duration']:.2f} "
                    f"- 0.5*{motion['friction_accel']:.2f}*{motion['duration']:.2f}^2 = {motion['distance']:.2f} m."
                )
            )
        else:
            lines.append("No slide distance was produced because the action did not resolve into a shove.")
    else:
        lines.append("No direct force calculation yet. The dodge card prepares a lateral response against the next incoming shove.")

    lines.append("")
    lines.append("What Happened:")
    lines.append(
        (
            f"Enemy response: {context['enemy_response']}. "
            f"{context['outcome']}"
        )
    )
    if context["motions"]:
        motion_bits = [f"{motion['subject']} moved {motion['distance']:.2f} m" for motion in context["motions"]]
        lines.append("Resolved motion: " + ", ".join(motion_bits) + ".")
    return "\n".join(lines)


def build_interaction_summary(context: dict[str, Any]) -> dict[str, str | None]:
    actor = str(context.get("actor", "p1"))
    target = str(context.get("target", "p2"))
    actor_cards = list(context.get("effect_cards") or [])
    action_card = context.get("action_card")
    if action_card:
        actor_cards.append(str(action_card))

    actor_expression = f"{actor} used: {' + '.join(actor_cards) if actor_cards else 'Action card'}"
    reaction_card = _reaction_card_name(context)
    reaction_expression = f"{target} used: {reaction_card}" if reaction_card else f"{target} did no action"

    reasons: list[str] = []
    enemy_response = str(context.get("enemy_response", "")).lower()
    if context.get("action_kind") == "dodge":
        reasons.append(f"{actor} prepared a dodge for the next shove.")
    elif "dodge success" in enemy_response:
        reasons.append(f"{target} dodged the shove.")
    elif "dodge failed" in enemy_response:
        reasons.append(f"{target}'s dodge failed.")

    motions = context.get("motions") or []
    motion_bits = [f"{motion['subject']} moved {motion['distance']:.2f}m" for motion in motions if motion.get("distance", 0) > 0]
    if motion_bits:
        reasons.append(", ".join(motion_bits) + ".")

    if not reasons:
        outcome = str(context.get("outcome", "")).strip()
        if outcome:
            reasons.append(outcome)
        else:
            reasons.append("The action resolved without a visible movement change.")

    return {
        "actor_expression": actor_expression,
        "reaction_expression": reaction_expression,
        "reasoning": " ".join(reasons).strip(),
    }


def build_markdown_document(context: dict[str, Any], gemini_text: str) -> str:
    summary = build_interaction_summary(context)
    lines = [
        "# What happen?",
        "",
        "## Card Interaction",
        summary["actor_expression"] or "",
    ]
    if summary["reaction_expression"]:
        lines.append(summary["reaction_expression"])
    lines.extend(
        [
            "",
            "## Result",
            summary["reasoning"] or "",
            "",
            "## Physics Behind It",
            gemini_text.strip() or "No Gemini response was returned.",
            "",
        ]
    )
    return "\n".join(lines)


def extract_explanation_sections(text: str) -> dict[str, str]:
    sections = {
        "Physics Breakdown": "",
        "Calculation": "",
        "What Happened": "",
    }
    current_key: str | None = None
    for raw_line in str(text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched = False
        for key in sections:
            prefix = f"{key}:"
            if line.startswith(prefix):
                current_key = key
                sections[key] = line[len(prefix):].strip()
                matched = True
                break
        if matched:
            continue
        if current_key is not None:
            sections[current_key] = (sections[current_key] + " " + line).strip()
    return sections
