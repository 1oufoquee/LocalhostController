# LocalhostController

A phone gamepad for a second player in Fireboy and Watergirl-style games.

- Phone: left analog stick sends A/D; right hold button sends Space.
- Player 1 continues using the PC arrow keys.
- No room codes, QR codes, or manual token entry.
- PC agent automatically opens the PC page and registers the computer.
- On the phone, press **Find PC**, select the computer, then approve the request on the PC screen.

## Deploy on Northflank

1. Create a service from this repository using the Dockerfile.
2. Expose HTTP port 8080 and enable WebSocket upgrades.
3. Health check path: `/health`.
4. Use one running replica because active WebSocket connections are held in memory.
5. No environment variables or manually created secrets are needed for this pairing flow.

## Start the PC

Install Python 3.10+ on Windows. Download this repository, open PowerShell in its folder and run:

```powershell
py -m pip install -r requirements.txt
py pc_agent.py --server https://YOUR-NORTHFLANK-DOMAIN
```

The agent creates a persistent random device ID, opens the PC confirmation page in the browser, and connects to the server. Leave the agent window running while playing.

## Connect the phone

Open the main site URL on the phone, press **Найти ПК**, select your computer, and approve the request on the PC browser page. The controller then appears on the phone.

## Controls

- Phone joystick: A / D.
- Phone jump button: Space.
- PC player: arrow keys as usual.

## Important

The Windows agent is required: browsers cannot synthesize operating-system keyboard input for another game or application. The agent only accepts A, D and Space, and the PC user must approve each phone connection. Keep the agent running while playing.
