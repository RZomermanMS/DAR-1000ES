# Internet-radio menu: program guide (proposed)

## Status and scope

**Design specification only; not installed or implemented.** This chapter
records the requested navigation and separates recommendations from decisions
still needed. The companion [user manual](17-internet-radio-menu-user-manual.md)
describes the intended experience, not operating instructions for current firmware.

Baseline inspected: main commit `7d45cab`, firmware 0.3.48, on 2026-11-16.
See the [operating guide](13-screen-driver-operating-guide.md),
[keypad evidence](14-keypad-mapping.md) and
[split architecture](15-split-setup-architecture.md).

| Area | Implemented baseline versus this proposal |
| --- | --- |
| Presets 1–16, DISPLAY MODE | Work as documented in chapters 13–15; retain their behavior |
| CHECK | Currently starts Stereo VU as documented in chapters 13–15; proposed short press checks connections and a two-second hold in PROGRAM SET stores the selected startup station; see the [user manual](17-internet-radio-menu-user-manual.md#check-connections-proposed) |
| Categories, MUSIC/SPEECH, MEMORY, BLOCK, MHz/CLEAR, MONO MODE | Mapped raw events only; the menu actions below are new |
| PROGRAM switch, DIRECT, FINE +/− | Switch startup behavior and menu controls are proposed; controller mappings remain unverified and virtual controls disabled. UNDEFINED is proposed as country-menu entry, subject to its intermittent mapping |
| Directory, filters, Top 10, prefix editor, MEMORY storage | Proposed, not a feature of the current front panel |
| Startup status file | Record last-used station, brightness and display mode; restore logical display settings, with station startup governed by PROGRAM; not implemented |
| PROGRAM label | Mapped fixed display element; proposed country-state ownership/blinking not implemented |
| Split audio | Controller still decodes locally; UART is diagnostic, not a station-command transport |

The latest complete shared-column keypad check was clean, but earlier
intermittent failures remain relevant; this is not blanket hardware validation.
No firmware, configuration, deployment or hardware changes accompany this guide.

## Safety and display invariants

- Browsing, directory replies, selection, preset recall and menu overlays must
  **never start stopped physical display output** or change authorization.
- Preserve the selected display mode and brightness under overlays, returning
  to that mode afterward. Do not take over manual/held/pair scans.
- DISPLAY MODE retains its information/VU/equalizer/OFF cycle; holding it
  changes DIM. In current firmware CHECK starts Stereo VU only from stopped
  output, with existing AHCT-profile and hardware-readiness constraints, and
  does not change a running scan. The later CHECK proposal does not implement
  or authorize any change to that current behavior.
- Sony OFF is not isolation. Existing powered-Sony, original-driver isolation,
  buffer-enable and safe connection requirements in chapter 13 remain mandatory.
  Software cannot detect all those conditions. This menu grants no new permission
  to energize display or audio outputs.
- Browsing alone never tunes. The current station continues until an explicit
  DIRECT tune or numbered preset recall; a directory error must not stop it.

## State and data model

Keep browsing separate from playback, persistent preset storage and the startup
status file.
The following are conceptual records, not existing firmware structures or APIs.

| Record | Required concepts |
| --- | --- |
| Applied browse scope | `country_code`: ISO alpha-2 or null for ALL COUNTRIES; selected genre/category ID or ALL GENRES |
| Pending country | Copy of applied country while selector is open; never applied by cursor movement |
| Browse session | Screen, return screen, locked prefix, active character, candidate UUID, result generation and cache snapshot |
| Station | Directory UUID, display name, original name, normalized sort key, country code, raw tags, curated categories, last-known playable direct URL, codec/check information |
| Preset | Slot 1–16, UUID, saved name, last-known playable URL; preserve existing custom-URL presets without inventing UUIDs |
| Storage transaction | Snapshot of selected station, proposed slot, replacement confirmation, write outcome |
| Playback | Selected station and independent selection generation; connecting/playing/failed state, actual metadata |
| Persistent startup status file | Last-used station identity/name and last-known playable URL, user-selected brightness and display mode; distinct from transient overlays and output authorization |
| Directory cache | Scope, mapping version, timestamps, pages loaded, completeness/staleness and error state |

Use distinct concepts for **station location country** and **Country music**.
The latter is a genre label, e.g. COUNTRY MUSIC, never a country code.
The applied country remains selected during browsing and playback. Only
confirming ALL COUNTRIES clears it. Reboot persistence is an open decision.

Recommended non-disruptive invariant: a country change affects future browse
results only; it neither stops an already playing station nor blocks explicit
recall of a saved preset outside that country.

### Required startup status file (proposed)

The user requires a **persistent status file**, not merely generic NVS settings,
containing the last-used station, brightness and display mode. On startup,
read and validate that file and restore the saved logical mode/brightness.
The later PROGRAM switch requirement supersedes automatic resumption of the
last-used station: ON starts the programmed station, or NPO Radio 2 if none
has been programmed; OFF starts the tuner without a preset loaded. With
PROGRAM in SET, a two-second CHECK hold stores the selected radio station as
the startup station; the hold must not also trigger the short connection
check. Failed writes preserve the previous programmed station. Startup while
left in SET remains undecided. A programmed station is not assumed to be the last-used station. Retain station
UUID/name and last-known playable URL where available; custom-URL stations
must remain identifiable without a directory UUID. This is a target design;
current firmware starts NPO Radio 2 and does not restore mode/DIM across reboot.

Save only intentional, successfully applied user state changes: an explicitly
tuned/recalled station once playback succeeds, a chosen display mode (including
OFF), or a brightness change. A failed tune must not replace the last-used
station. Update only the changed field while preserving the other saved values.
Do not rewrite the file on every boot, status poll, metadata update, directory
refresh, candidate movement or animation frame. Saving a browsed station to a
preset without playing it does not change the last-used station.

Loading/search animations, preset announcements, menu screens and error overlays
must not replace the saved display mode or brightness. Restore logical settings
without restarting stopped physical output or persisting hardware authorization;
the existing explicit display-start and isolation requirements still apply.
Retaining an OFF selection must not discard the saved brightness.

If the selected startup station cannot connect, report the failure explicitly
and preserve its saved identity/URL; **never silently fall back to NPO Radio 2
or another station**. A later explicit successful selection may replace it.
Use failure-safe file updates and expose save failures without claiming the
new state was persisted. The filename/location, format/versioning and
missing/corrupt-file first-boot/recovery policy still need decisions; do not
invent a recovery fallback for those cases. The requested NPO Radio 2 choice
for PROGRAM ON is a startup choice, not a fallback after a failure.

This is the menu-side contract for the separately developed startup design,
not an implementation of startup or an authorization to change its files.
Country-filter persistence remains a **separate unresolved decision**; the
recorded station and restored display fields do not decide whether country
survives reboot.

### PROGRAM indicator truth table

This is the earlier proposed country-state behavior for the **PROGRAM label**,
not the separate numeric indices 1/2/3 or the physical PROGRAM switch.
Its suitability alongside the switch's startup role needs confirmation.

| State | Applied filter | PROGRAM label |
| --- | --- | --- |
| Normal browsing/playback | ALL COUNTRIES | OFF |
| Country selector open | Previous committed filter retained; pending choice may differ | BLINKING |
| Confirm specific country | Newly committed country | STEADY ON, including during playback/category browsing |
| Confirm ALL COUNTRIES | No country constraint | OFF |
| Cancel selector | Restore previous committed selection | Previous OFF or STEADY ON state |

The [fixed-element map](08-esp-display-driver-specification.md#slot-24-audio-program-and-tuning)
identifies slot 24 bit 8 (`0x100`) as PROGRAM. It is not MEMORY or the
PROGRAM indices, some of which current VU modes use as level warnings.
Compose only the label bit without disturbing those warnings or other fields.
Existing frame/display code provides a base for composition, not a country
indicator service. Blinking requires a future UI scheduler; no blink cadence
is agreed. Logical indicator state must not restart output when the display is OFF.

## Screens, controls and transitions

Short MEMORY confirms navigation; long MEMORY enters storage **only with a
valid selected station**. There is no station to store in country/genre lists.
In a station browser, a successful DIRECT tune returns to the selected display
mode; a tune failure must be explicit, not disguised as another station.

| Screen/context | FINE +/− | BLOCK +/− | Short MEMORY | DIRECT | MHz/CLEAR |
| --- | --- | --- | --- | --- | --- |
| Country selector | One country entry | Six country entries | Commit pending country; open genres | No tune action | Cancel pending choice; return to prior screen |
| Genre selector, including ALL GENRES | One genre | Not assigned by this design | Open alphabetical station browser | No tune action | Up one level to country selector; retain applied country |
| Category Top 10 | Previous/next station candidate or trailing BROWSE ALL entry | Not assigned by this design | Open BROWSE ALL when selected; no station tune action | Play selected station, not BROWSE ALL | Return to prior browse/playback screen |
| Alphabetical station browser | Change active letter | Six alphabet positions | Lock character; advance edit position | Play displayed candidate at any time | Back one character; at empty prefix go up to originating list |
| STORE PRESET | No assignment | No assignment | No action until a replacement is requested | No tune action | Cancel without a write |
| REPLACE PRESET | No assignment | No assignment | Confirm persistent replacement | No tune action | Cancel without a write |

The physical PROGRAM control is a switch reserved for the startup behavior
above, not the country-menu entry. UNDEFINED is now proposed as the physical
entry, replacing its earlier proposed category role. Its shared-column mapping
has been intermittent and must be validated before relying on it. Once
opened, the country selector has a pending copy of the applied filter. When
backing from genres, opening the country selector must not clear the applied
country. Cancelling there restores the preceding genre screen and applied
indicator state.

Country and genre movement are list operations; genre +/− is explicitly
requested. Letter editing happens only in the station browser. Top 10 +/−
moves station candidates, never letters or genres at the same time.
Do not silently assign undefined controls.

Category controls use firmware binding labels:
NEWS, AFFAIRS, INFO, SPORT, EDUCATE, DRAMA, CULTURE, SCIENCE, VARIED,
POP M, ROCK M, M.O.R. M, MUSIC, SPEECH, LIGHT M, CLASSICS and OTHER M.
UNDEFINED is reserved for the proposed country entry, not a category shortcut.
ROCK M is the binding for the button also recorded as ROCKM in chapter 14.
MONO MODE is not a new category/navigation command.

Proposed category-shortcut rule: open that category's Top 10 under the applied
country, replacing the previous genre criterion rather than invisibly combining
two genres. Country and the resulting category criterion are composable.
Do not change the applied country. Final tag mappings need approval.

### Category Top 10

- List up to ten matching, supported playable candidates; show fewer when
  fewer qualify. No automatic tune, preset assignment or worldwide fallback.
- Recommended ranking: descending Radio Browser `clickcount`, documented as
  clicks in the last 24 hours, not audience ratings or listener counts.
  `clicktrend` is a different metric (difference over the last two days).
  Ranking choice and deterministic tie-breaker remain to be finalized.
- Append BROWSE ALL after the candidates. Short MEMORY on it opens the
  alphabetical browser with the same country/category scope. With zero matches,
  show an explicit empty state and retain a way back; do not imply ten exist.
- Filtered-out unsupported candidates can require additional bounded pages to
  fill ten places. A loading/partial result is not a complete global Top 10.

### Alphabetical station browser

The requested index is A B C … . The display suggests the first station matching
the locked prefix plus active letter. FINE +/− changes that letter. BLOCK +/−
jumps **six alphabet positions**, e.g. B → H for BLOCK+, not six stations.
Short MEMORY locks the current character and starts the next position.
The current editable character blinks; locked letters and the suggested station
suffix must be distinguishable.

Recommended exact empty-prefix handling: FINE skips letters without matches
under the locked prefix. BLOCK first computes the six-letter target, then,
if empty, advances in the requested direction to an available match. This
skipping rule is a recommendation, not an already implemented algorithm.
Wrap/end behavior and a fully empty result need the decisions listed below;
never loop indefinitely searching an empty cache.

Example with SLAM present in the filtered results:

1. Select S; show a first S candidate (not necessarily SLAM).
2. Short MEMORY locks S and moves to position two.
3. Select L; show the first SL candidate.
4. Short MEMORY locks SL and moves to position three; choose A if necessary
   to show SLAM. DIRECT may tune as soon as SLAM is the displayed candidate.

It is **not** necessary to spell the whole name. Do not promise that S or SL
uniquely identifies SLAM. The recommended back key is the mapped MHz/CLEAR,
not the user's earlier possible LNC/LINK suggestion; LINK remains unassigned.

The display is one row of **22 physical 5x7 cells**, not a multiline terminal.
Keep the edit position visible in a bounded window, with a prefix/suffix visual
distinction that survives truncation. A possible compact convention is a colon
after locked text: `SL:AM` means locked SL, active blinking A, suggested suffix M.
This convention still needs UI approval. Never marquee the cursor off-screen.
Blinking is a UI frame update, not a change to multiplex timing, duty or scan slots.

Illustrative single-row messages (each fits 22 cells):

```text
ALL COUNTRIES
NETHERLANDS
ALL GENRES
TOP10 ROCK M
BROWSE ALL
SL:AM
STORE PRESET --
REPLACE PRESET 07?
STORED
SAVE ERROR
```

These are **sequential screen examples**, not simultaneous physical rows.

### Preset storage and recall

1. Hold MEMORY with a valid station candidate selected; snapshot its UUID,
   name and checked playable URL. Show `STORE PRESET --`.
2. A numbered key 1–16 now chooses a storage slot instead of recalling it.
   An empty slot saves; an occupied one shows `REPLACE PRESET 07?` for slot 7.
3. Short MEMORY confirms replacement. MHz/CLEAR cancels before a write,
   leaving both saved presets and playback unchanged.
4. Show `STORED` only after successful persistent storage. On failure show
   `SAVE ERROR`, retain the old slot contents and allow cancellation/retry.
   Recommended completion: return to the originating candidate screen.

Ignore further storage inputs while a committed write is in flight; never
claim a cancellation rolled back a completed save. Use transactional persistence
so failed writes do not destroy occupied slots. Snapshot the station so an
asynchronous refresh cannot change what is saved.

Do not dispatch both short and long MEMORY actions from one press.
Reuse the debounce, contamination/cancellation and single-long-action pattern in
[`sony_keypad.c`](firmware/main/sony_keypad.c); its current long handling is for
DISPLAY MODE, not MEMORY. The MEMORY hold threshold is **not finalized**;
do not inherit a numeric value as a product commitment.

Outside storage, keys 1–16 retain immediate existing recall, independent of
directory availability (and, as recommended above, of the browse-country filter).
An unassigned key leaves playback unchanged and briefly shows `Unassigned`.
Preserve the implemented announcement: `Preset X` for one second, with
`Preset` in physical cells 4–9, blank cell 10, number in cells 11–12;
loading until connection, then station ID/name for about two seconds before
returning to the selected mode. None of these overlays starts stopped output.

## Directory integration proposal

Preferred provider: [Radio Browser API reference](https://docs.radio-browser.info/).
On 2026-11-16 direct retrieval of that documentation hostname was unavailable
in the task environment. Endpoint/field details below were checked against the
maintainer's [API documentation source at e093fd9](https://github.com/segler-alex/radiobrowser-api-rust/blob/e093fd995ec90ecba8cb1e7a9a2f2a9899f83bba/static/docs.hbs);
mirror guidance is also published on the [API landing page](https://api.radio-browser.info/).
These are design references, not an on-device integration test.

Discover mirrors through DNS for `all.api.radio-browser.info`, select a reachable
service host, and retry another on bounded failures. Resolve usable hostnames
and preserve HTTPS hostname/certificate validation; do not pin a permanent
server or bypass TLS checks. Send a descriptive application/version User-Agent.
Set request deadlines, retry/backoff limits and cache budgets before implementation.

| Purpose | Verified API path/parameters relative to chosen mirror |
| --- | --- |
| Country choices | GET `/json/countries`; station filters use standardized `countrycode`, not deprecated `country` |
| Available community tags | GET `/json/tags`; not a ready-made Sony genre taxonomy |
| Scoped station page | GET `/json/stations/search` with optional `countrycode=NL`, `tag=rock`, `tagExact=true`, `hidebroken=true`, `order=name`, `limit=100`, `offset=0` |
| Recommended popularity page | Same search with `order=clickcount&reverse=true` and bounded `limit`/`offset` |
| Refresh saved identity | GET `/json/stations/byuuid?uuids=<stationuuid>` |
| Report explicit station selection | GET `/json/url/<stationuuid>`; API JSON response, not itself an audio stream |

The page size above is illustrative, not a fixed memory-budget decision.
ALL COUNTRIES omits the country constraint; ALL GENRES omits tag constraints.
The API's `tagList` means **all** listed tags must match; it is not an OR list.
Curated category synonyms may require separate bounded queries and deduplication
by station UUID. Country + genre/category is an intersection. MUSIC/SPEECH and
other physical labels need an explicit, versioned mapping from community tags,
not guesses from station names or an assumption of RDS compatibility.
Directory categories also differ from the current stream `icy-genre` indicators.

A directory URL, homepage, search response or click-report endpoint is **not
a playable stream URL**. Candidate `url_resolved` may resolve redirects/playlists,
but is not proof of compatibility. Filter directory codec/check/HLS information
and validate the resulting direct HTTP/HTTPS MP3/AAC stream against current
decoder support. `hidebroken=true` and `lastcheckok` are hints, not guarantees.
No HLS, playlist, webpage, or additional codec support is introduced here.
Report a click only on explicit playback selection, not every candidate change,
and do not make directory reporting a prerequisite for saved-URL playback.

### Bounded cache and asynchronous work

Build a sorted local index over a bounded, paged, country/category-filtered
cache. Prefix matching is local; do not invent an API prefix endpoint or download
the full directory for every keypress. Worldwide/ALL GENRES particularly needs
a deliberate cache budget. Mark partial coverage explicitly; do not report
NO MATCHES as authoritative while relevant pages are still missing.
Full worldwide index coverage, eviction and refresh policies remain open.

Recommended request protocol:

1. Every scope change or refresh increments a browse generation and starts
   bounded loading outside the keypad dispatcher and real-time scan.
2. Tag results with generation, country/category scope, page and cache snapshot.
   Ignore obsolete results after cancellation, changed scope or a newer refresh.
3. Deduplicate UUIDs and maintain deterministic sorting across loaded pages.
   Preserve the selected UUID where possible; if it disappears, make that
   explicit rather than silently tuning/saving a replacement.
4. Freeze the candidate snapshot for DIRECT/storage. Playback has a separate
   selection generation so late stream status cannot replace newer metadata.
   This also matches the future UART generation requirement in chapter 15.

| Condition | Required explicit result |
| --- | --- |
| Lookup/page in progress | Loading or partial-results state; controls remain cancellable |
| Empty completed scope | NO MATCHES; retain scope/back navigation, no worldwide fallback |
| DNS, timeout, mirror, malformed-response failure | DIRECTORY ERROR; bounded retry/refresh path, keep playback and presets |
| Cached data without connectivity | Clearly stale/offline results with age/refresh status; no promise URLs still work |
| Unsupported or failed stream | Explicit playback error, no silent station replacement |
| Saved URL fails | Explicit failure; optional UUID refresh of the same identity, never substitute another station |
| Persistent write fails | SAVE ERROR; old preset retained, no STORED success message |

Persist UUID, name and last-known playable URL so preset playback does not need
a live directory. A missing UUID result does not authorize deleting a preset.
Refresh/check work must not hold scan locks or alter output authorization.

## Integration boundary and decisions still open

Controller target responsibilities: directory/cache, country/genre navigation,
candidate selection, presets and display composition. Audio target responsibilities:
stream connection/decoding and actual playback state/metadata, as in chapter 15.
The current controller-local player is still the actual playback backend.
Do not send station messages through the diagnostic UART protocol as though
that future command layer already exists.

Before implementation, resolve:

- Physical PROGRAM, DIRECT and FINE mappings, UNDEFINED reliability and
  continued matrix reliability; startup while PROGRAM remains in SET and
  startup-station write/confirmation details.
- Country-filter persistence/default after reboot.
- Status-file path/format/versioning and missing/corrupt-file first-boot/recovery
  policy; recording last-used station, brightness and display mode is required,
  not an open decision.
- Curated categories, shortcut replacement rule approval, popularity ranking
  and ties; no audience-rating claim.
- FINE/BLOCK empty-prefix skipping recommendation, alphabet wrap/bounds,
  no-match behavior, end-of-name/duplicate names, digits and non-Latin
  normalization/collation. Preserve original names separately from sort keys.
- Locked-prefix visual convention, blink cadence and return/error/retry gestures.
- MEMORY hold threshold, storage transaction integration and legacy preset migration.
- Cache/page/memory budgets, worldwide coverage, refresh/backoff policy and
  maximum URL/name lengths compatible with existing persistence and player.

Future acceptance checks should cover pending-country cancellation and indicator
restoration; ALL COUNTRIES; genre versus letter semantics; B→H jumps; partial/empty
caches; stale asynchronous replies; offline preset recall; storage
replace/cancel/failure and single short-or-long dispatch; mode/DIM preservation;
status-file recording of station and restoration of brightness/mode, including
OFF; PROGRAM ON and OFF startup choices, SET plus a two-second CHECK hold,
short/hold separation and failed startup-station writes; intentional
changes only, overlay exclusion and failed writes; startup-station failure
without fallback; and stopped output remaining stopped. These are implementation
acceptance goals, not claims of executed firmware tests.
