# Newton's Edge

The purpose of our game:<br>
- One of our team memebers (Dior) finds difficulties of learning abstract physics concepts while he was preparing the AP Physics C: Mechanics, and he was not alone in this situation.<br>
- Therefore, we are creating a interactive game to help them learning abstract physics concepts with detailed animation<br>

Why Card Games?<br>
- Card can present the ideas and concept through multimedia and provides the strategy point of view of the game.

The advantage of our game:
- easy access (small app, simple instruction, play immediately)
- simple rules (easy for new-comers to play the game)
- displaying the replay of the actions to present detailed animation on abstract physics concepts


## Game Design

<figure>
  <img width="709" height="500" alt="Menu" src="https://github.com/Jack-keja/Newton-s-Edge/blob/3f702bd1d40eccc8bf52def0efd3eea4cbbe7843/game_design/menu.png" />
  <figcaption>
    Fig. 1: main menu
  </figcaption>
</figure>
<figure>
  
  <img width="709" height="500" alt="gaming" src="https://github.com/Jack-keja/Newton-s-Edge/blob/7d2e9dee2b559a3b75d7456e32bba4ec01c2d57c/game_design/gaming.png" />
  <figcaption>Fig. 2: playing interface</figcaption>
</figure>

<figure> 
  <img width="709" height="500" alt="how_to_play" src="https://github.com/Jack-keja/Newton-s-Edge/blob/7d2e9dee2b559a3b75d7456e32bba4ec01c2d57c/game_design/How_to_play.png" />
  <figcaption>Fig. 3: instruction pop out window</figcaption>
</figure>

<figure>
  <img width="709" height="500" alt="about" src="https://github.com/Jack-keja/Newton-s-Edge/blob/7d2e9dee2b559a3b75d7456e32bba4ec01c2d57c/game_design/about.png" />
  <figcaption>Fig. 4: about us pop out window</figcaption>
</figure>

## What is in the prototype

- Two players start at `12m` and `14m` on a `25m` stage.
- Each player begins with `5` energy and `2` random cards.
- At the start of each new turn, the active player gains `2` energy and draws `2` cards.
- Players can play any number of effect cards, then one action card.
- Force cards resolve with a short physics simulation using:
  - mass = `50kg`
  - gravity = `10m/s^2`
  - friction starts at `0.2`
  - impact time cap = `2s`
- Direct hits now use action-reaction force:
  - the defender is pushed away
  - the attacker recoils in the opposite direction
- A successful dodge makes the attacker lunge forward instead.
- A player loses by being pushed past `0m` or `25m`.

## Controls

- Click a card to select it.
- Click the selected card again, or press `Space`, to play it.
- Press `Enter`, or click `End Turn`, after the action resolves.
- Press `R` to restart.
- Press `Esc` to quit.

## Run

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Start the game:

```powershell
python main.py
```

## Assumptions used for playability

- Hands are capped at `6` cards so the UI stays readable.
- Conservation of Energy restores `3` energy after `3` of the affected player's turns.
- Friction slows movement after a shove instead of canceling weaker cards completely.
