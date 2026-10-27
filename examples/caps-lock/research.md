# Research: "Caps lock" / "Your fix isn't showing up? Check the port" (duo sketch, 2026-10-27)

Checked on 2026-10-27.

| Claim (screen / voice / caption / guide) | Source | Checked |
|---|---|---|
| Vite's default dev-server port is 5173 | https://vite.dev/config/server-options (server.port, "Default: 5173") | 2026-10-27 |
| "Port taken? Vite jumps to the next one." (docs: "if the port is already being used, Vite will automatically try the next available port so this may not be the actual port the server ends up listening on") | same page | 2026-10-27 |
| On-screen log line `Port 5173 is in use, trying another one...` (source: `logger.info(\`Port ${port} is in use, trying another one...\`)`) | https://github.com/vitejs/vite/blob/main/packages/vite/src/node/http.ts | 2026-10-27 |
| On-screen `VITE ready` / `Local:   http://localhost:5174/` (the Local: line format comes from Vite's logger; the screen is a simplified recreation) | https://github.com/vitejs/vite/blob/main/packages/vite/src/node/logger.ts | 2026-10-27 |
| `strictPort: true`: "exit if port is already in use, instead of automatically trying the next available port" | https://vite.dev/config/server-options (server.strictPort) | 2026-10-27 |
| `defineConfig({ server: { strictPort: true } })` in vite.config.js (guide only) | https://vite.dev/config/ | 2026-10-27 |

## Fiction (sketch, not claims)
"Attempt twelve", fixes #12 and #13, the button, "since Tuesday", the old server being the Nerd's own
forgotten one, the caps lock joke and the left monitor's "clicked 40 times" are invented for the scene.
The terminals are simplified recreations, not screenshots.

## Dropped
- Next.js / Create React App port behaviour: different tools, not checked, left out (guide note says to check your framework's docs).
- "Ctrl+C stops the server": true for most terminals but not sourced here, so the guide just says "stop it".
