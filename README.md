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

<figure>
  <img width="500" height="700" alt="card_design" src="https://github.com/Jack-keja/Newton-s-Edge/blob/544d55f3b23373a424465a40d7e79064f35cec82/game_design/card_design.png" />
  <figcaption>Fig. 5: card design</figcaption>
</figure>


## What is in the prototype

- Two players start around the center of the stage (`11.8m` and `13.8m` on a `25m` stage).
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
- Drag the card to the battleground to use it         
- Click `End Round` to end your turn
- Press `Restart Game' to reset
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
  
### Poster
<figure>
  <img width="709" height="500" alt="about" src="https://github.com/Jack-keja/Newton-s-Edge/blob/7d2e9dee2b559a3b75d7456e32bba4ec01c2d57c/game_design/poster.png" />
</figure>


### Short essay:

Newton’s Edge is a PvP card game inspired by the idea that physics can be just as thrilling as any competitive strategy game. Our goal is to help high school students explore core mechanics like force, friction, and Newton’s Laws through interactive gameplay. Two players battle on a 25-meter stage, using energy and cards to shove, dodge, and outplay each other. Instead of relying on simple damage numbers, action cards trigger a short physics simulation with realistic values for mass, friction, and impact time.
One challenge was balancing realism with fun, since accurate friction and movement could easily make weaker cards useless. We solved this by letting friction slow movement rather than cancel it entirely. We’re proud that the prototype successfully turns physics equations into exciting player decisions. Next, we plan to expand the card pool, improve UI clarity, and add more physics concepts like momentum combos and variable mass.

### Links
Powerpoint link:https://www.canva.com/design/DAHFOKGbWqU/25AXEmTw8w_TrJAMzSpQgw/edit?referrer=https%3A%2F%2Fwww.canva.com%2F<br>
Video: https://www.bilibili.com/video/BV18nXjBbEC8/?vd_source=6e5c8626e5747cf39485144316360c17<br>

Game link:https://dyeus-wwww.itch.io/newtons-edge



#### AI use
Nano Banana was used for designing the cards; Codex OpenAI was used for syntax and debugging code.
