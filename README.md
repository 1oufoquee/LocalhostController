# LocalhostController

A two-phone gamepad for Fireboy and Watergirl-style games.

- Each phone chooses **Fire** or **Water** before connecting.
- Fire phone sends Arrow Left / Arrow Right / Arrow Up.
- Water phone sends A / D / W.
- Both phones can connect to the same PC at the same time.
- The PC browser asks for approval separately for each character.
- A small Windows agent sends the approved keys to the game.

## Northflank

Deploy this repository using its Dockerfile, expose HTTP port 8080, enable WebSocket upgrades, and use one replica. Health check: `/health`.

## Windows PC

Install Python 3.10+ and run from the project folder:

```powershell
python -m pip install -r requirements.txt
python pc_agent.py --server https://YOUR-NORTHFLANK-DOMAIN
```

The agent opens the PC approval page. Keep the agent and PC page running while playing.

## Phones

Open the public service URL on each phone:

1. Phone one selects **Огонь**, presses **Найти компьютер**, selects the PC, then the PC user approves.
2. Phone two selects **Вода**, does the same, and the PC user approves.
3. Both phones show their own joystick and jump button.

Install the page to the home screen or use the fullscreen button for a more immersive controller.

## Controls

| Phone | Left / right | Jump |
|---|---|---|
| Fire | Arrow Left / Arrow Right | Arrow Up |
| Water | A / D | W |

The Windows agent is required because a mobile browser cannot send operating-system key presses directly to another app or game.
