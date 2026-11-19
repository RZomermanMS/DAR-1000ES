# Controller ESP: implementation specification and agent handoff

## Status and instruction to the implementation agent

Implement this target on the controller ESP, using the existing firmware and
tests as the baseline. This document is a requirements handoff, **not evidence
that the target is implemented, deployed, or electrically safe**. The owner
confirmed on 2026-11-19: **all buttons are confirmed**. Treat the physical
controls as confirmed, not as provisional proposals. This confirmation does
not supply new numeric matrix codes or GPIO connections, establish new firmware
actions, prove a complete inter-ESP exchange, or authorize output drivers.
The [historical keypad observations](14-keypad-mapping.md) and current
`firmware/main/sony_keypad.c` remain evidence of what was actually recorded and
implemented. Use the actual confirmed mapping data, not guessed codes; if a
needed code or switch input is not present in the repository, request the
mapping rather than inventing it or disabling the requested feature.

The [menu program guide](16-internet-radio-menu-program-guide.md) supplies
the detailed screen transitions, directory strategy and invariants; the
[user manual](17-internet-radio-menu-user-manual.md) supplies walkthroughs.
This handoff takes precedence over older conflicting target descriptions.
Current-operating and historical documents retain their version-specific facts.

## Scope and boundaries

- The original Sony physical front panel must be sufficient for day-to-day
  receiver operation, including browsing, preset storage and recall, connection
  checks, and source control. No phone app, web UI, or IR remote may be
  required to operate the receiver. AirPlay is initiated on its sender.
- The target split is controller ESP for keypad, display, directory, presets,
  state and command generation, audio ESP for connection, decoding, playback
  and source arbitration. Do not silently run two independent players.
  Portable controller development without the Sony or audio ESP must remain
  possible, with missing hardware reported honestly.
- The current 0.3.48 controller still decodes locally; UART offers diagnostic
  PING/PONG/MAP/ACK, not the finished audio protocol. Inherited standalone
  AirPlay behavior is **not** proof that the DAR profile starts AirPlay.
  Coordinate an actual audio-side protocol counterpart; controller-side mocks
  alone cannot establish end-to-end playback, disconnect, or policy enforcement.
- Physical network onboarding/recovery, adding an arbitrary station outside
  the directory, and any volume/mute or standby functions not already supplied
  by actual Sony hardware have no agreed physical interaction. Do not present
  existing web setup as a completed physical solution. Ask the owner for a
  design before claiming those paths complete. The headphone LEVEL control is
  a physical control; do not infer other audio controls or electrical behavior.
- No startup-animation redesign, electrical modifications, or changes to
  separate startup/demo specifications are authorized by this handoff.

## Control contract

All target behavior below requires implementation; confirmed physical buttons
do not imply the current firmware dispatches the target actions.

| Control | Required target action |
| --- | --- |
| PROGRAM switch | OFF: power up the tuner without a preset loaded. ON: power up with the programmed station, or NPO Radio 2 if none was programmed. SET: select a radio station and hold CHECK for two seconds to save it for future ON power-up. SET at power-up remains an owner decision. |
| CHECK | Short press: force Wi-Fi reconnect using saved credentials and run a bounded cross-ESP communications check; report separate outcomes. In PROGRAM SET, hold for two seconds to save the selected station as startup station. A recognized hold must not also invoke the short action. Replaces the current CHECK-only stopped-screen Stereo VU start; don't change DISPLAY MODE to compensate implicitly. |
| UNDEFINED | Open country selection with a pending copy of the applied filter; not a category shortcut. |
| FINE −/+ | Move one country, one genre, one Top 10 candidate, or one active prefix letter depending on screen. |
| BLOCK −/+ | Move six country entries or six alphabet positions, depending on screen. No assignment in other screens. |
| MEMORY | Short: commit country/genre, lock a prefix character, select BROWSE ALL, confirm replacement or a contextual Source action. Hold with a valid station candidate: enter preset storage. The hold threshold remains to be agreed; short and hold are mutually exclusive. |
| DIRECT | Request playback of the displayed station candidate, not a country, genre, or BROWSE ALL. |
| MHz/CLEAR | Back/cancel; cancel pending country, preset replacement and Source confirmation without applying changes; in prefix editing remove one character, then return to the originating list when empty. |
| 1–16 | Outside storage, immediately recall the numbered preset; inside storage, choose the destination slot rather than recall. |
| DISPLAY MODE | Retain existing short mode cycle including OFF and hold DIM cycle. A hold fires once and must not also dispatch a short press. Manual display start still requires chapter 13 hardware readiness. |
| Category keys | NEWS, AFFAIRS, INFO, SPORT, EDUCATE, DRAMA, CULTURE, SCIENCE, VARIED, POP M, ROCK M, M.O.R. M, MUSIC, SPEECH, LIGHT M, CLASSICS, OTHER M open that category's Top 10 under the applied country; do not tune. |
| LNC/LINK | Candidate Source-menu entry only if the confirmed physical control has no occupied function. Confirmation of buttons alone does not approve an unallocated function or resolve the label spelling. If this condition is not established, do not claim a command entry exists; use the fallback below and ask the owner. |
| MONO MODE | Reserved for a future real mono/stereo option; do not invent an action. |
| POWER, PHONES, LEVEL | Preserve actual Sony hardware behavior. Do not infer a software standby, mute or volume mapping. |

Debounce, contamination handling and release/cancel behavior must preserve
exactly one short or long action per press. Preserve the existing preset
announcement: `Preset X` for one second, loading until connected, station
identity for about two seconds, then the selected display mode. Unassigned
presets report `Unassigned` and do not change playback.

## Browsing and persistence

1. UNDEFINED opens countries; FINE moves one and BLOCK six. Short MEMORY
   commits the pending country and opens genres. MHz/CLEAR cancels the pending
   choice; ALL COUNTRIES removes only the location restriction.
2. Select a genre or ALL GENRES with FINE and short MEMORY. Category shortcuts
   open up to ten matching supported stations under the applied country;
   FINE navigates candidates and trailing BROWSE ALL opens the full browser
   on short MEMORY. A category shortcut replaces the previous genre criterion
   as recommended in chapter 16, subject to owner approval.
3. Alphabetical browsing uses FINE for the active letter, BLOCK for six
   alphabet positions, short MEMORY to lock the letter, DIRECT to tune the
   displayed candidate, and MHz/CLEAR to edit/back. Never require spelling
   an entire station name. Keep the active character visible in the 22 cells.
4. Browsing, candidate movement, saving a candidate and errors never tune or
   interrupt the current station. A successful explicit DIRECT or preset
   selection may change playback; during AirPlay it selects the radio station
   to resume later. Neither selection authorizes display output.
5. Hold MEMORY on a valid candidate to snapshot station identity/name/URL.
   A numbered key chooses a slot. An occupied slot requires a short MEMORY
   replacement confirmation; MHz/CLEAR cancels before commit. Report `STORED`
   only after a successful durable write; report `SAVE ERROR` and retain the
   previous slot on failure. Do not change playback when saving.
6. Preserve preset identity, name and last-known direct playable URL so recall
   can work without the directory. Preserve/migrate existing custom-URL
   presets without inventing UUIDs. No connection error may silently tune a
   different station. Directory errors must not erase presets or interrupt
   playback.
7. Store last successfully selected station, logical brightness and display
   mode, including OFF, in a failure-safe persistent status file. Record the
   PROGRAM SET startup station separately from the last-used station.
   PROGRAM ON chooses the saved startup station or NPO Radio 2 when none was
   programmed; OFF loads no preset. An unplayable saved startup station reports
   failure, never silently falls back. A failed write preserves the previous
   startup station. Do not rewrite saved settings for overlays, browsing,
   failed tune attempts or periodic metadata.

Use the Radio Browser integration, bounded asynchronous cache, stale-generation
and loading/error rules in chapter 16. Direct HTTP/HTTPS MP3 and AAC/ADTS are
the existing scope, not HLS, playlists, authenticated URLs or station websites.
Do not treat incomplete results as a complete no-match result. Use verified
TLS and bounded timeout/retry behavior; don't invent a retry button.

## Source and connectivity

Display active owner and playing/paused state, and sender-reported device name
when available, scrolling it within the 22-character display. Distinguish
`UNKNOWN DEVICE` from `NO AIRPLAY SESSION`. Pause does not release ownership.
Source menu navigation uses contextual FINE and short MEMORY, with MHz/CLEAR
cancel. Require explicit `DISCONNECT?` confirmation; on confirmation release
the actual AirPlay receiver session, then return to the selected radio station,
reporting failure rather than substituting another station. `RADIO ONLY` is a
separate confirmed policy that prevents immediate retake; `AUTO` / `AIRPLAY
ALLOWED` restores AirPlay permission. Policy changes do not replace the saved
station, erase presets, or start a stopped display.

If no Source entry is confirmed available, a read-only AirPlay status item
within DISPLAY MODE is a fallback proposal, not a substitute for disconnect
or policy commands. Identify that command entry as a blocker and ask the owner;
do not steal an existing gesture. Do not claim AirPlay or Sony mute/relay/I2S
support based solely on standalone inherited code.

Short CHECK forces a reconnect, then a matched bounded inter-ESP request/reply.
Report Wi-Fi and link results independently, including timeout/offline and
retry. Link success does not prove Internet, stream, or audio health. Do not
use MAP: it is an isolated bench GPIO operation. The implementation must decide
and document how each ESP receives the reconnect request and reports its own
status, including when the link is down. Reconnect may interrupt current audio;
retain credentials, presets and the selected station.

## Implementation and safety

Use the existing TCA8418 event dispatcher, radio/display code and local
persistence where appropriate; keep scanning responsive while directory,
storage, Wi-Fi and UART work occurs asynchronously. Define bounded/versioned
station commands, acknowledgments, connection and playback states, metadata,
source and policy operations, and generation IDs; reject malformed frames and
stale responses. On link loss, clear stale meter information and report link
failure. Chapter 15 contains current UART wiring and diagnostic format; do not
misrepresent that diagnostic protocol as already carrying these messages.

The display is one 22-cell row; overlays restore the chosen mode and brightness.
None of startup restoration, browsing, reconnect, source changes, or remote
status grants physical display authorization or starts stopped output.
Keep chapter 13's power, isolation and AHCT output-enable requirements. Sony
OFF alone is not isolation. Do not energize audio outputs, change GPIO
assignments, or assert mute/relay levels based on names or software-only
authorization. Report capacity/build constraints rather than deploying an
unsafe workaround; the documented controller application slot is almost full.

## Acceptance before reporting completion

- Test every confirmed control and all three PROGRAM positions using the
  actual mapped input data; confirm short/hold exclusivity, bounce and
  contamination cancellation. Do not fabricate missing code/input evidence.
- Exercise Netherlands + genre and ALL GENRES, category Top 10/BROWSE ALL,
  SLAM prefix via FINE/MEMORY/DIRECT, BLOCK six-position jumps, country
  cancellation and ALL COUNTRIES without interrupting playback.
- Test preset recall, unassigned slot, empty store, replacement confirmation,
  cancellation, interrupted writes, stale directory response and offline
  saved-URL recall; preserve other slots and prevent a save from tuning.
- Test PROGRAM ON with and without a saved startup station, OFF without preset,
  SET + two-second CHECK, failed write, failed startup stream, and no short
  CHECK action after a hold. Verify status-file persistence, corrupt/missing
  state handling and no silent fallback.
- Test CHECK success, Wi-Fi failure, inter-ESP timeout and recovery separately;
  no MAP and no fabricated success. Test actual audio-board command/ack,
  metadata generation, stale message rejection and link-loss meter clearing.
- With a real supported sender, test AirPlay playing/paused ownership, known
  and unknown device, no session, explicit disconnect/cancel, RADIO ONLY retake
  prevention and AUTO restoration. A mock proves only controller logic.
- Verify mode/DIM and overlay restoration and that stopped output remains
  stopped through all above actions. Run the existing targeted tests and build
  for the applicable profile; report isolated-bench vs connected physical
  results separately, including failures and untested behavior.

## Owner decisions still needed

The final contract does not invent answers to unspecified product or hardware
choices. Before claiming full completion, resolve missing actual input codes
and switch interface, availability of LNC/LINK for Source entry, physical
onboarding/recovery and custom station entry, behavior on boot in PROGRAM SET,
country/policy persistence, MEMORY hold duration, retry gesture, category-tag
mapping and ranking/tie rules, prefix collation/wrap, cache budgets and status
file recovery. Document chosen values and preserve all invariants above.
If the audio counterpart or safe hardware prerequisites are unavailable,
implement and test the controller boundary where possible, report the block,
and do not claim real two-ESP or AirPlay operation.
