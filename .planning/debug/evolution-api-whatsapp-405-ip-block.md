---
status: resolved
trigger: "Evolution API corre pero WhatsApp rechaza la conexión con error 405 — bloqueo temporal de IP por demasiados intentos de conexión"
created: 2026-03-31T23:10:00Z
updated: 2026-03-31T23:20:00Z
---

## Current Focus

hypothesis: CONFIRMED - root cause identified and fix applied
test: Need user to wait for ban expiry then test reconnection with new version
expecting: v2.3.7 with clean session data will generate QR without reconnection loop
next_action: Wait for user verification after ban expires

## Symptoms

expected: Evolution API genera QR, usuario escanea, WhatsApp conecta y mantiene sesión estable
actual: WhatsApp rechaza conexión con HTTP 405 — indica ban temporal de IP por exceso de intentos de handshake WebSocket. Container in tight reconnect loop (every 1-3 seconds).
errors: Error 405 continuo en logs de Evolution API, sigue reintentando y fallando. State stuck at 'connecting' with statusReason 200 but never reaching 'open'.
reproduction: Muchos intentos de conexión previos (QR scanning repetido, reinicios de contenedor, recreación de instancias) agotaron la tolerancia de WhatsApp
started: After multiple QR scan attempts, container restarts, and instance recreation

## Eliminated

## Evidence

- timestamp: 2026-03-31T23:10:00Z
  checked: Evolution API container logs (tail 100)
  found: Container actively in reconnect storm - emitting connection.update with state 'connecting' every 1-3 seconds. 12 attempts in last 100 log lines. No 'open' state ever reached.
  implication: The ban is actively being extended by each reconnection attempt.

- timestamp: 2026-03-31T23:10:30Z
  checked: docker-compose.yml evolution-api environment variables
  found: No reconnect/retry configuration. No QRCODE_LIMIT configured. Using atendai/evolution-api:latest which resolved to v2.2.3.
  implication: Zero protection against connection storms.

- timestamp: 2026-03-31T23:11:00Z
  checked: Container stopped successfully
  found: docker compose stop evolution-api executed - container halted
  implication: No more connection attempts. Ban timer can count down.

- timestamp: 2026-03-31T23:12:00Z
  checked: Evolution API version and known bugs
  found: Running v2.2.3 (image built 2025-02-03). PR #2365 "Bug Fix: QR Code Infinite Reconnection Loop" fixes exact issue. NOT in v2.2.3 - verified in v2.3.7+. Issue #2430 confirms infinite reconnection loop in v2.2.3.
  implication: KNOWN BUG in our version. Baileys connectionUpdate handler triggers immediate reconnect when connection closes during initial QR generation.

- timestamp: 2026-03-31T23:13:00Z
  checked: Database instance and session state
  found: Instance 'clinic-main' had connectionStatus='close', ownerJid=NULL (never authenticated). Session table had stale creds (has_creds=true) from failed QR attempts.
  implication: Stale creds cause Baileys to attempt reconnection using old session instead of fresh QR. Compounds the loop bug.

- timestamp: 2026-03-31T23:13:30Z
  checked: Instance data volume
  found: Volume directory for instance empty (0 files).
  implication: Instance file data lost during recreation. Only DB session data remained (stale).

- timestamp: 2026-03-31T23:14:00Z
  checked: QRCODE_LIMIT env variable
  found: Defaults to 30. Controls max QR generation attempts before instance disconnects.
  implication: Set to 6 for protection against QR regeneration storms.

- timestamp: 2026-03-31T23:15:00Z
  checked: Docker Hub image availability
  found: v2.3.x releases moved from atendai/ to evoapicloud/ org. evoapicloud/evolution-api:v2.3.7 confirmed available and pulled.
  implication: Image reference must use evoapicloud/ not atendai/.

- timestamp: 2026-03-31T23:16:00Z
  checked: Applied fixes
  found: (1) Stale Session and Instance records deleted from DB. (2) Image pinned to evoapicloud/evolution-api:v2.3.7. (3) QRCODE_LIMIT=6 added. (4) Container remains stopped pending ban expiry.
  implication: All three root cause factors addressed. Ready for recovery when ban expires.

## Resolution

root_cause: Three compounding factors caused the WhatsApp IP ban and perpetuated it:
1. **Known bug in v2.2.3:** Infinite reconnection loop bug (GitHub issue #2430, fix PR #2365). Baileys connectionUpdate handler triggers immediate reconnection when connection closes during initial QR generation, with no backoff. Fix included in v2.3.7+.
2. **Stale session credentials:** Database contained session creds from failed QR attempts (ownerJid=NULL = never authenticated), causing Baileys to attempt reconnection using invalid data instead of generating fresh QR.
3. **No protective configuration:** No QRCODE_LIMIT set (default 30), no reconnect throttling. Allowed unlimited rapid-fire retry attempts every 1-3 seconds.

fix: Applied three changes:
1. Stopped container to halt connection storm (done immediately)
2. Cleaned stale Instance and Session data from PostgreSQL evolution_api database
3. Updated docker-compose.yml:
   - Changed image from atendai/evolution-api:latest (v2.2.3) to evoapicloud/evolution-api:v2.3.7 (includes reconnection loop fix)
   - Added QRCODE_LIMIT=6 to prevent future QR generation storms

verification: Pending human verification after ban expires
files_changed:
  - docker-compose.yml
