# Newton's Edge

**Newton's Edge** is a local hot-seat PvP physics card game built with **Python** and **Pygame**.
The objective is to push your opponent into the void before they do the same to you.

This prototype combines card-based decision making with classical mechanics, turning force, friction, and momentum into direct gameplay.

## Prototype Overview

- Two players duel on a `25m` arena.
- Each player starts with `5` energy and `4` cards.
- At the start of each new turn, the active player gains `2` energy and draws `2` cards.
- Players can use effect cards, then one action card.
- The match is won by forcing the opponent past `0m` or `25m`.

## Current Gameplay

- Force cards resolve through a short shove animation and then physics-driven displacement.
- Dodge can evade the next incoming shove.
- Conservation transfers energy now and restores it later.
- Smooth and Rough cards modify the stage friction.
- The game uses a stylized arena-focused layout with drag-to-play cards.

## Physics Model

- Player mass: `50kg`
- Gravity: `10m/s^2`
- Impact time: `2s`
- Starting friction: `0.2`
- Max energy: `10`

## Cards

### Action Cards

| Card | Force | Energy Cost |
|------|-------|-------------|
| Force 50 | 50 N | 1 |
| Force 75 | 75 N | 2 |
| Force 100 | 100 N | 3 |
| Force 125 | 125 N | 4 |
| Dodge | State | 3 |

### Effect Cards

- `Conservation`: steal energy now, return it later
- `Smooth`: reduce friction
- `Rough`: increase friction

## Controls

- Drag a card into the arena to use it.
- Press `Enter`, or click `End Turn`, after the action resolves.
- Press `R` to restart.
- Press `Esc` to quit.

## Installation

```powershell
pip install -r requirements.txt
python main.py
```

## Notes

- Hands are capped at `10` cards for readability.
- Conservation restores delayed energy after `3` of the affected player's turns.
- The current project is a playable prototype and can be extended with more cards, AI, audio, and stronger visual effects.
