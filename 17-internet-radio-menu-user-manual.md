# Internet-radio menu: user instruction manual (planned)

> **Not available in current firmware.** This manual describes the proposed
> menu, not controls you can use on the installed 0.3.48 front panel.
> PROGRAM, DIRECT and FINE +/− still need verified physical mappings.
> Directory browsing, country selection, Top 10 and holding MEMORY to save
> are not implemented. Restoring station, brightness and display mode from a
> status file is also a target requirement, not an installed feature.
> See the [program guide](16-internet-radio-menu-program-guide.md)
> for recommendations and unresolved decisions.

For controls that work now, use the
[screen-driver operating guide](13-screen-driver-operating-guide.md) and
[current front-panel status](15-split-setup-architecture.md#portable-controller--travel-demo).
The controller still plays radio locally; split-audio station control is a target.

## Before using the planned menu

These walkthroughs assume a future implementation and an already safely
authorized, running display. **The menu must not start a stopped display.**
Selecting a station or preset does not authorize physical output.
Follow chapter 13's connection/isolation precautions; Sony OFF alone is not
electrical isolation. No hardware work is requested by this manual.

Browsing does not interrupt the current station. Only DIRECT on a station
candidate or an explicit numbered preset recall requests a new station.
Menu screens temporarily cover, then return to, your chosen display mode
without changing DIM brightness or safety authorization.

## What startup must remember (planned)

The proposed system must keep a **persistent status file** with your last-used
station, chosen brightness and display mode, then restore those three at startup.
It must resume that station, **not hardcode NPO Radio 2**. If the saved station
fails, show the error without silently choosing NPO Radio 2 or another station.
You can explicitly select a different station.

Only intentional successful changes are saved: a station you explicitly select
and successfully play, a display-mode choice (including OFF), or a brightness
change. Browsing, saving a candidate as a preset, loading animations, menu
screens and announcements must not replace those saved settings.
Restoring settings does not start stopped physical display output or restore
hardware authorization. OFF retains your brightness for later use.

The policy for a missing/corrupt file or first boot is still undecided; no
fallback station is specified. Country-filter persistence is separately
**undecided**, unlike the three required saved settings above.

## Choose Netherlands, then a genre

Planned sequence:

1. Press **PROGRAM** to open countries. Its light blinks while you choose;
   the previous applied country remains in force until confirmation.
2. Use **FINE +/−** to move one country, or **BLOCK +/−** to move six entries.
   Find `NETHERLANDS`.
3. Briefly press **MEMORY** to apply it and open genres. PROGRAM stays lit.
4. Use **FINE +/−** to choose a genre. Choose `ALL GENRES` for no genre limit.
   Briefly press **MEMORY** to open alphabetical station browsing.
5. Press **MHz/CLEAR** to go back one level. Returning from genres or stations
   does not clear Netherlands.

“Country” here means station location, not the Country music genre.
The selected country applies to browsing and category shortcuts even while
a station plays. Whether it survives reboot is **not decided**.

## Use a category's Top 10

With Netherlands applied, press **ROCK M** (also called ROCKM), **NEWS**,
**MUSIC**, **SPEECH**, **SCIENCE** or another category button.
The proposed shortcut opens that category under the selected country, replacing
the previous genre criterion; this replacement rule still needs approval.

- Use **FINE +/−** to move through up to ten station candidates.
  Here +/− changes stations, not genres or letters.
- Press **DIRECT** to play the displayed station. Opening the list does not
  play it or assign presets automatically.
- To search beyond the shortlist, move to **BROWSE ALL** after the candidates
  and briefly press **MEMORY**. It keeps the same country/category.
- Fewer than ten may be available. No matches must be reported explicitly;
  there is no silent switch to worldwide results.

Recommended ranking is directory-recorded clicks in the last 24 hours,
**not audience ratings**. Final ranking is not yet decided.

## Find SLAM without spelling the entire name

This example assumes SLAM is available in the chosen country/genre.
You may use ALL GENRES first if the current category excludes it.

1. In alphabetical station browsing, use **FINE +/−** to choose **S**.
   The active letter blinks and the first matching station is suggested.
2. Briefly press **MEMORY** to lock S and move to the second character.
3. Use **FINE +/−** to choose **L**, then briefly press MEMORY to lock SL
   and move to the third position. Choose A if needed to display SLAM.
4. Press **DIRECT** whenever SLAM is the displayed candidate.
   You do not have to finish spelling it; S or SL may also match other stations.

In this screen **BLOCK +/− jumps six alphabet positions**, for example B → H
with BLOCK+, not six stations. Recommended behavior skips empty prefixes
with FINE; BLOCK first jumps six letters, then searches onward in that
direction if the target has no matches. Wrap, digits and non-Latin names
still need design decisions.

Recommended back/edit control: **MHz/CLEAR**, not LINK/LNC. It goes back one
character; at an empty prefix it returns to the originating genre or Top 10 list.

The physical display has just one row of 22 characters. A proposed display
convention is `SL:AM`: SL is locked, A is the blinking editable character and
M is the suggested suffix. The exact visual convention is not finalized.
The cursor must remain visible rather than scrolling away.

## Save, replace or cancel a preset

Planned storage sequence, with a station candidate selected:

1. **Hold MEMORY** until `STORE PRESET --` appears. The required hold duration
   is not decided. Releasing must not also perform the short-press action.
2. Press **1–16** to choose a slot. An empty slot saves the selected station.
3. For an occupied slot, e.g. 7, read `REPLACE PRESET 07?`.
   Briefly press **MEMORY** to confirm replacement.
4. Before committing a save, press **MHz/CLEAR** to cancel without changing
   any presets. Once a write has been committed, cancellation cannot undo it.
5. Wait for `STORED`, which must mean the persistent save succeeded.
   `SAVE ERROR` means it did not succeed; the previous preset must remain intact.

Storing must not tune the candidate or overwrite other slots.
While choosing a storage slot, numbered keys choose the destination; they
do not recall stations. Outside storage, they retain immediate preset recall.

## Recall a preset

Numbered preset recall already exists; the planned menu must preserve it:

- Press **1–16** outside storage to recall that saved station.
- An unassigned slot briefly shows `Unassigned` and leaves playback unchanged.
- Assigned slots show `Preset X`, then loading until connection, then the
  station identifier for about two seconds before returning to your display mode.
  In the existing layout, `Preset` is in cells 4–9, cell 10 is blank and the
  number is in cells 11–12.
- Recall never starts stopped physical display output.

The proposal stores a directory station's UUID, name and last-known playable
URL so a saved preset can play without a working directory service. The stream
itself still needs network access. The recommended rule lets you recall a
preset from another country without changing or being blocked by your browse
filter. A failed station must show an error, never silently play a replacement.

## Clear or cancel the country filter

To browse worldwide, press **PROGRAM**, select **ALL COUNTRIES** and briefly
press **MEMORY**. PROGRAM turns off and genre selection opens.
ALL COUNTRIES removes only the location restriction; ALL GENRES separately
removes the genre restriction.

To abandon a pending country change, press **MHz/CLEAR** instead of MEMORY.
The previous applied country and its light state return. Merely highlighting
ALL COUNTRIES does not clear a filter.

Recommended non-disruptive rule: changing or clearing the browse-country filter
does not stop the station already playing.

## Quick reference

All menu meanings below are planned unless explicitly marked existing.

| Control or indicator | Meaning |
| --- | --- |
| PROGRAM | Open country choices; OFF = worldwide, BLINKING = choosing, STEADY ON = applied specific country |
| FINE +/− | Country list: one entry; genre list: one genre; Top 10: candidate; station editor: active letter |
| BLOCK +/− | Countries: six entries; station editor: six alphabet positions |
| Short MEMORY | Confirm country/genre, lock a letter, open BROWSE ALL, or confirm preset replacement |
| Hold MEMORY | Enter storage for the selected station; not assigned in country/genre lists |
| DIRECT | Play the currently displayed station candidate, without spelling its full name |
| MHz/CLEAR | Cancel/back; does not implicitly clear the applied country |
| 1–16 | Existing immediate recall, except planned slot selection while storing |
| DISPLAY MODE | Existing mode cycle including OFF; hold changes DIM |
| CHECK | Existing start of Stereo VU only when stopped and hardware ready; no change to a running scan |

The PROGRAM country light is the **label**, not the separate PROGRAM 1/2/3
digits; current VU modes may use digits for level warnings.
The logical country reminder must not turn a stopped display on.

## Loading and problems

The planned browser must distinguish loading, incomplete/stale cached results,
no matches and a directory error. Allow loading to finish or use the eventual
retry/refresh control (its exact gesture remains undecided); you can back out
with MHz/CLEAR. A partially loaded list is not proof there are no other matches.
Directory problems must not erase presets or interrupt the current station.

Only supported direct **HTTP/HTTPS MP3/AAC** streams are in scope.
A directory page/API address or station website is not a playable stream.
This design adds no HLS or playlist support. A directory listing is not a
guarantee that a station can connect or decode.
