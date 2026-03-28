# Void Push

**Void Push** is a turn-based physics strategy card game built with **Python** and **Pygame**.  
The objective is to **push your opponent into the void** before they do the same to you.

This game combines **card-based decision making** with **classical mechanics concepts**, making it both a strategy game and a physics-learning project.

## Target Audience

This game is mainly designed for:

- **senior high school or college-level physics students**
- students interested in both **physics** and **game development**
- learners who want to see how formulas and mechanics can be translated into gameplay
- developers experimenting with educational games in **Python + Pygame**

---

## Game Features

- **Built with Python and Pygame**
  - Lightweight and suitable for educational or prototype development.

- **Turn-based strategic gameplay**
  - Players make decisions each round based on available cards and energy.

- **Physics-based combat system**
  - Movement and displacement are influenced by:
    - force
    - mass
    - gravity
    - friction
    - impact time

- **Energy management**
  - Players must spend energy carefully to attack, defend, or change the environment.

- **Card-based mechanics**
  - Includes force cards, dodge mechanics, and environmental effect cards.

- **Interactive friction control**
  - Players can increase or decrease friction to influence movement distance.

- **Educational value**
  - Encourages players to think about motion in terms of physical quantities rather than pure animation.

- **Expandable architecture**
  - Can be extended with more cards, more complex formulas, AI opponents, and better visualization.

---

## Core Idea

Unlike traditional fighting games, **Void Push** focuses on **calculated movement** rather than direct damage.

Players do not win by reducing HP.  
Instead, they win by using physics and strategy to control motion and force the opponent off the stage.

This design makes the game especially suitable for physics learners, because every move can be connected to a real-world concept such as:

- Newton’s Second Law
- acceleration under force
- frictional resistance
- displacement during a time interval
- resource constraints in decision-making

---

## Game Rules

### Goal
Push the opponent out of the stage into the **void** to win.

---

## Initial Setup

At the beginning of the game:

- Each player starts with **5 energy**
- Each player gets **4 cards**
- Player starts at position **(12, 0)**
- Enemy starts at position **(14, 0)**
- Initial velocity `u = 0`

---

## Round System

At the beginning of each round:

- Recharge **2 energy**
- Draw **2 random cards**

---

## Physics Settings

- Mass of each player: **50 kg**
- Gravity: **10 m/s²**
- Direction convention: **right is positive**
- Impact time: **2 s**
- Initial coefficient of friction: **0.01**
- Maximum energy capacity: **10**
- Total stage length: **25 m**

---

## Cards

### Action Cards

#### Force Cards

These cards apply force to push the opponent.

| Card | Force | Energy Cost |
|------|-------|-------------|
| Force 25 | 25 N | 1 |
| Force 50 | 50 N | 2 |
| Force 75 | 75 N | 3 |
| Force 100 | 100 N | 4 |

#### Dodge
- **Type:** State Card
- **Cost:** 3 energy
- The higher the enemy’s force, the harder the dodge is to succeed.
- If the enemy does not push, nothing happens.
- If dodge succeeds, the enemy may move forward by their own committed action, which may create a positional disadvantage or cause them to lose.

---

### Effect Cards

#### Conservation of Energy
- **Cost:** 0 energy
- **Restriction:** can only be used once per round
- Steal up to **2 energy** from the enemy
- The same amount is returned to the enemy in the next round

#### Smooth Environment
- **Cost:** 1 energy
- Decrease the coefficient of friction by **0.01**

#### Rough Environment
- **Cost:** 1 energy
- Increase the coefficient of friction by **0.01**

---

## What You Need in Advance

Before working on this project, it is helpful to have the following background knowledge and tools.

### 1. Python Basics
You should be familiar with:

- variables
- functions
- classes and objects
- conditionals
- loops
- lists / dictionaries
- importing modules

### 2. Pygame Basics
Helpful concepts include:

- creating a game window
- drawing objects on screen
- handling keyboard and mouse input
- managing a game loop
- updating frames
- displaying text and UI elements

### 3. Basic Physics Knowledge
Since this game is aimed at physics students, you should understand:

- force
- acceleration
- velocity
- displacement
- friction
- gravity
- Newton’s laws of motion

### 4. Turn-Based Game Logic
It is useful to know how to design:

- turn order
- energy consumption
- card drawing systems
- state changes
- win/lose conditions

### 5. Development Environment
Make sure you have:

- **Python 3.x**
- **Pygame**
- a code editor such as **VS Code** or **PyCharm**
- **Git** and **GitHub** for version control

---

## Installation

### Clone the repository

```bash
git clone https://github.com/your-username/void-push.git
cd void-push
