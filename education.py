from __future__ import annotations

from typing import Any


def _format_effects(effects: list[str]) -> str:
    return ", ".join(effects) if effects else "None"


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
    - Friction ($\mu$): {context['friction']:.2f}

    Interaction Data:
    - Action: {context['actor']} used {context['action_card']} ({context['action_kind']}) on {context['target']}.
    - Force Applied: {context['force']:.0f} N
    - Modifiers: {effects_text} | Enemy Response: {context['enemy_response']}
    - Motion Data: {motion_text}

    Constraint: Total response must be under 100 words. Use the exact numbers provided.

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
