# LocalhostController

A tiny phone gamepad for a second player in Fireboy and Watergirl-style games.

- Phone: left virtual analog stick sends A/D; right hold button sends Space.
- Player 1 continues using the PC keyboard arrow keys.
- No rooms, pairing codes, QR codes, or room creation.
- One Windows PC agent keeps an outbound WebSocket connection to the hosted service. The phone connects to the same service.

## Northflank deployment

1. Create a service from this repository and select Dockerfile.
2. Expose HTTP port 8080 and enable WebSocket upgrade support.
3. Set health check path to `/health`.
4. Configure two long random environment variables:
   - `PC_AGENT_TOKEN` — secret used only by the Windows agent.
   - `PHONE_TOKEN` — secret used in the private phone controller link.
5. Deploy one replica. Connections are held in memory by the single server instance.

## Windows PC setup

Install Python 3.10+ and download this repository. In PowerShell, from the project folder:

```powershell
py -m pip install -r requirements.txt
py pc_agent.py --server https://YOUR-NORTHFLANK-DOMAIN --token YOUR_PC_AGENT_TOKEN
```

Leave this window running while playing. The agent reconnects automatically after temporary network interruptions.

## Phone setup

Open this private URL on the phone:

```
https://YOUR-NORTHFLANK-DOMAIN/#YOUR_PHONE_TOKEN
```

The page opens directly as a full-screen controller. Add it to the home screen for an app-like experience. Do not share the URL: its fragment is the phone access key.

## Safety

The service accepts only left/right/jump actions from the phone. The PC agent maps them to A, D and Space and releases all held keys when the phone disconnects. Keep the phone URL and PC token private. Use HTTPS on the hosted service.
