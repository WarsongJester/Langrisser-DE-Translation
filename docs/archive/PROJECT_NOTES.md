> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> Route A (full-width) era — predates the Route B half-width breakthrough.
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# Langrisser I — Dramatic Edition (Sega Saturn) — English Translation Project Notes

_Consolidated reference. Supersedes the older BUILD_STATUS.md / RENDER_RE_NOTES.md / TRANSLATION_ASSESSMENT.md notes in the outputs folder._

---

## 1. Goal & approach

Full English fan-translation of the **Langrisser I** half of *Langrisser - Dramatic Edition* (Saturn). The user supplies the English translation (xlsx); the tooling does all reverse-engineering, text reinsertion, and disc rebuilding. The user tests builds in the **SSF emulator** and reports back with screenshots.

**Honest framing / key decisions:**
- The game's dialogue/menu renderer is **strictly 2-byte (fullwidth)**. Single-byte ASCII renders as garbage. All English text is encoded as **fullwidth SJIS** (every letter, digit, and punctuation mark mapped to its 2-byte form).
- A true **half-width font patch was attempted and abandoned** — the cursor X-advance lives in a runtime-dispatched, multi-stage pipeline with transient state that couldn't be safely patched without live-trace tooling we couldn't get working.
- The project ships a **fullwidth build with voices (PCM) OFF**. With PCM off, the extra `{06}{07}` "box advance" beats added by overflow re-segmentation are just silent button-advances — no voice desync, no text lost.
- Dialogue overflow is fixed by **re-segmenting each unit into a chain of ≤3-line boxes** joined by `{06}{07}`, wrapping at width 14.

---

## 2. Current status at a glance

| Content | Status |
|---|---|
| Dialogue (14 scenarios) | ✅ Done & confirmed in-game: 1,2,5,6,7,10,11,12,13,15,16,17,18,19 |
| Dialogue (6 scenarios) | ⏳ Mismatched box/unit counts — need manual alignment: 3,4,8,9,14,20 |
| Prologues (all 20) | ✅ Done & confirmed (title + body + win/lose, wrapped to 14, no indent) |
| Character names | ⏳ Work but crash on long names — **awaiting 18 short forms** (see §11) |
| Item names (37) | ✅ Capped at 8 chars (safe placeholders) — **awaiting 21 short forms** (see §11) |
| Item descriptions | ⏳ Box-growth test in progress (see §7) |
| Menu/UI short labels (≤8) | ✅ Safe pass (spells, Yes/No, commands). Long messages stay Japanese |
| Menu/UI long messages | ❌ Cannot translate — exceed the 8-char buffer (crash). Stay Japanese |
| Scenario titles (entry 8) | ⬜ Not started |
| "シナリオ N" intro card | ⬜ Separate Japanese asset, not yet located |
| Opening quiz | ⬜ Location in data not yet found |
| Endings | ⬜ Location in data not yet found |
| Status-bar names | ❌ Separate untranslated table/font path — not yet located |
| PCM-off-by-default | ⏳ Setting byte known; boot-time default not yet flipped (non-blocking) |

**The current test build** (`Langrisser1_EN_test.xdelta`) contains: 14 dialogue scenarios + all 20 prologues + capped item names + ≤8 menu labels + a 2-item description box-growth test.

---

## 3. File locations

**Source (read-only uploads):**
- Original archive: `/mnt/user-data/uploads/Langrisser_-_Dramatic_Edition__SAT_.7z`
- Main dialogue script: `/mnt/user-data/uploads/Langirsser_I_My_Script.xlsx` — sheets `Scenario 1`..`Scenario 20` (note: 06/08/09 use leading zeros). Markers: `<>` = end message box, `<clsr>` = page break; each row = a line.
- Extras script: `/mnt/user-data/uploads/Other_Langrisser_Stuff.xlsx` — sheets: `Scenario Quiz`, `Quiz Battle Explanations`, `Scenario Prologues`, `Endings`, `Names`, `Items`, `Menu`.
- Memory dumps (1 MB, 0x06000000 region): `kronos.bin`, `taylor.bin`, `freeze.bin`.
- PCM saves: `LANGRISSER_PCM_ON.bkr`, `LANGRISSER_PCM_OFF.bkr` (32 KB Saturn backup RAM).

**Working dir:** `/home/claude/lang/` (persists during a session; filesystem resets between sessions). Contains the extracted `extracted/LANG1/SCEN.DAT`, `FONT.DAT`, the original raw BIN, and all Python tooling.

**Outputs:** `/mnt/user-data/outputs/`
- **Current deliverables:** `Langrisser1_EN_test.xdelta` + `Langrisser1_EN_test.cue`, `langrisser_prologue_fitter.html`, this file.
- Stale/older: `Langrisser1_EN_v2..v5.*`, `Langrisser1_EN_overflow_test.xdelta`, the older `.md` notes. (Kept, not deleted, but not current.)

---

## 4. SCEN.DAT format

3-level big-endian pointer structure. **21 scenario blocks** (block *i* = Scenario *i*+1). **Block 0 is the global data block.** Each block's string-table (section 2) holds these entries:

| Entry | Contents | Count (block 0) | Notes |
|---|---|---|---|
| 0 | UI / menu strings | 139 | global; **Menu sheet, SECT 0** |
| 1 | Character/class names | 93 | global; **Names sheet**; duplicated identically across all blocks |
| 2 | Items (names + descriptions) | 142 | global; **Items sheet**; 37 names then descriptions |
| 3 | Big debug/config menu | 503 | global; not covered by the Menu sheet |
| 4 | Places / proper nouns | 239 | global |
| 5 | **Main dialogue** | per-scenario | the per-block content |
| 6 | Win/lose conditions | 6 | per-scenario |
| 7 | **Title + prologue** | 1 long string | per-scenario (see §7) |
| 8 | 20 scenario titles | 20 | global |
| 9 | (empty) | 0 | |

Strings are `{00}`-separated, Shift-JIS (cp932) + control codes. Names/items/menu/places are **duplicated identically across all 21 blocks** — so they must be patched in every block (the tooling does this).

**Items entry (entry 2) layout:** indices **0–36 = item names** (max 8 Japanese chars; includes 2 menu options "Not Equipped"/"Unchanged" and some duplicates like Langrisser ×2). Indices **37–141 = descriptions**, each item = a few `{00}`-separated strings: *desc line 1, desc line 2 (sometimes empty), stat line*. The sheet mirrors this; **keep empty strings when aligning** (1-line descriptions have an empty 2nd line).

---

## 5. Control codes (confirmed)

| Code | Meaning |
|---|---|
| `{06}{07}` | **Box advance** — new screen / (formerly) a voiced beat. Page break in prologues. |
| `{08}` | **Newline** within a box/page. |
| `{05}` | Prologue page/line format marker — produces a leading **indent** on the line it precedes (now omitted for flush-left body text). |
| `{04}{XX}` | **Dictionary-compressed word** — drop for English. Some are headers (e.g. `{04}{1C}`=Winning Conditions, `{04}{1D}`=Losing Conditions). In prologue setup, `{04}{01}`+digit+`{04}{83}` renders "SCENARIO-NN" and `{04}{83}` ≈ the opening 「. |
| `{09}{XX}` | Name-insert — drop. |
| `{02}` | Lord-name insert — drop. |
| `{03}` | Prologue title-setup code. |

A "box"/display screen for dialogue = text between `{06}{07}`, must fit **3 lines × 14 fullwidth chars**.

---

## 6. ⚠ CRITICAL CONSTRAINT: the ~8-fullwidth-char buffer limit

The single most important hard limit. **Names, item names, and menu labels are copied into a fixed-size buffer (~8 fullwidth chars / ~16 bytes).** A string longer than that **overflows the buffer and crashes the game** — the CPU jumps to garbage at **`PC 0606B4D8`** (executing `0x0000`).

Confirmed instances:
- "Imperial Commander" (17) as a character name → crash when selecting that lord.
- Long menu **messages** (e.g. "Load which save data?" = 21) → crash when loading a save.
- "Jessica" (7), item names capped at 8 → **safe, no crash.**

**Implications / rules:**
- All name-type and label-type strings must be **≤ 8 fullwidth characters.**
- English UI **messages** (sentences) are longer than their Japanese originals and **cannot be translated** in slots governed by this buffer; they must stay Japanese (or be abbreviated ≤8, which is usually not worth it).
- The buffer limit is *separate from* visual slot width — some ≤8 strings still visually overlap in very tight slots (e.g. unit-info "Magician"), which is cosmetic, not a crash.

---

## 7. Rendering findings by surface

**Dialogue boxes:** width **14** fullwidth, **3 lines** per box. Overflow handled by re-segmentation into `{06}{07}`-joined boxes. Punctuation must be fullwidth. Confirmed working.

**Prologues (entry 7):** one string = `setup header` + bracketed `title` + body pages + win/lose conditions, separated by `{06}{07}`. Key lessons:
- **Must preserve the original setup header** (`{05}{08}{04}{01}<digit>{03}{08}{04}{83}…`). It renders the "SCENARIO-NN" line and initializes the crawl. Dropping it caused garbled glyphs + overlap.
- **Body/conditions wrap to width 14, ~5 lines per page**, pages joined by `{06}{07}` — same overflow approach as dialogue.
- **`{05}` indent removed** — body lines now start flush-left (per request).
- **Titles render centered with `「 」`**, but the title line only fits ~12–14 chars; long titles are force-wrapped with `{08}` to stack cleanly instead of auto-wrapping into garbage. (Title list & widths: see the fitter tool / §11-adjacent.)
- Tool: **`langrisser_prologue_fitter.html`** — live previewer with all 20 prologues, exact wrap rules, overflow flags, and JSON export for round-tripping edits.

**Item description box:** **CONFIRMED** — exactly **2 text lines × 16 fullwidth chars (~32 chars total)** + 1 stat line. The box does **not** grow vertically; `{08}` inside a desc string is dropped (only the first segment shows). Reliable structure: desc-string-1 = line 1 (≤16), desc-string-2 = line 2 (≤16), stat-string = stat line. English descriptions (~50 chars) must be **trimmed to ~32** to fit. Stat lines (e.g. "AT+8 DF-3") are short and translate fine.

**Status-bar names (bottom of screen):** come from a **different table and font path** than entry 1. Patching entry 1 translates dialogue speaker labels and the unit-info name, but **not** the status bar. That source has not been located yet.

**"シナリオ N" intro card** (flashes before each prologue): a **separate Japanese asset** (likely a small graphic/tilemap), not in this SCEN data. Not yet located; would need its own pass to become "Scenario N".

---

## 8. Build pipeline & commands

Build order (run from `/home/claude/lang/`):

```
python3 build_all.py        # assembles dialogue + prologues + names/items/menu into LANG1_SCEN_overflow.dat
python3 rebuild_disc.py     # grows SCEN in place, shifts directory records, patches PVD -> new_track1.iso
python3 final_assemble.py   # frames to MODE1/2352 (EDC/ECC via cdecc.py), appends tracks 2-6, writes the .cue
xdelta3 -e -9 -f -s "<ORIGINAL_RAW_BIN>" Langrisser1_EN_test.bin /mnt/user-data/outputs/Langrisser1_EN_test.xdelta
```

Where `<ORIGINAL_RAW_BIN>` = `Langrisser - Dramatic Edition (ja-JP)/LANGRISSER_DRAMATIC_EDITION.bin`.

**Disc geometry constants** (in `rebuild_disc.py` / `rebuild_generic.py`): `SCEN_LBA=136946`, `SCEN_OLD=322` sectors, directory-shift `THRESH=137268`, `T1_OLD=167225`. SCEN grows dynamically; everything ≥ THRESH shifts by `K = new_sectors - 322`.

**Apply (for the user):** apply the xdelta to the **original** BIN → name the output `Langrisser1_EN_test.bin` → load the `.cue` in SSF → set **PCM OFF** in Game Settings.

---

## 9. Python tooling (current / authoritative)

- **`scen_codec.py`** — `parse(d)` → `{'top','blocks':[{'strings':[...],...}]}`; `serialize(m)`. Lossless round-trip.
- **`parse_xlsx.py`** — dialogue sheet parser; `is_speaker()` detects Title-Case speaker labels & stage directions (validated 170 labels, 0 false positives).
- **`reinsert_overflow.py`** — dialogue reinserter. `sj(s)` = fullwidth-SJIS encoder (all ASCII incl. punctuation → 2-byte; `'`→0x8166, `"`→”, `-`→— U+2015). `encode_box(box,width=14,maxlines=3)` re-segments into ≤3-line `{06}{07}` boxes. `patch(d,wb,scenarios,width=14)`.
- **`build_prologue.py`** — `parse_prologues(wb)` → `{scn:[pages]}`; `wrap`, `paginate`, `localize_title` (preserves per-scenario setup + `{05}` wrappers, wraps long titles), `build_prologue(orig_e7,pages,width=14,maxlines=5)`.
- **`build_all.py`** — the master build: dialogue (aligned scenarios) + all 20 prologues + menu (`patch_menu`, ≤8 guard) + item names (`patch_item_names`, cap 8) + current description test. **This is the script to edit/run for new builds.**
- **`rebuild_disc.py`** + **`final_assemble.py`** + **`cdecc.py`** — disc rebuild & MODE1/2352 framing.
- Superseded/experimental (ignore): `reinsert.py`, `reinsert2/3/4.py`, `reinsert_full.py`, `build_extras.py`, `build_scen.py`, `build_template.py`, `rebuild_generic.py`, `extract_script.py`, `sjis_scan.py`.

---

## 10. Detailed status & next steps

1. **6 mismatched dialogue scenarios (3,4,8,9,14,20):** box count ≠ non-empty unit count. Auto-alignment (length-correlation / Needleman-Wunsch) proved unreliable (skips real dialogue, not just combat barks). Plan: align collaboratively with the user, side-by-side, or leave those scenarios Japanese.
2. **Character names:** translate cleanly for dialogue labels & unit-info, but need the **18 short forms** (§11) for the over-length ones, and the **status-bar source** still needs locating.
3. **Item names:** capped at 8 (safe placeholders in build). Need the **21 short forms** (§11) to finalize.
4. **Item descriptions:** decide approach from the box-growth test, then wrap (or trim) all and align sheet↔entry2 keeping empties.
5. **Menu:** short labels done. Long messages blocked by the buffer. Big entry-3 menu (503 strings) not started.
6. **Scenario titles (entry 8), quiz, endings, scenario card:** not started; quiz/endings/card locations in data not yet found.
7. **PCM off by default:** save byte = offset `0x24d` (01=on/00=off), checksum at `0x9d`. Setting persists once saved (so non-blocking). Boot-time default not yet flipped in code.

---

## 11. Pending — short forms needed from the user (≤8 chars each)

**Character names (entry 1) — 18 over the limit:**
idx 12 Sir Galius · 15 Doh Motov · 21 Bernoulli · 32 Commander · 36 Vigilante · 41 Imperial Commander · 45 Stone Golem · 47 Living Armor · 48 Vampire Lord · 51 Master Dino · 53 Great Dragon · 57 Demon Lord · 61 Imperial Soldier · 64 Necromancer · 72 Jormungand · 77 Matsunith · 78 Ramisrose · 92 Shika Tribesman

**Item names (entry 2) — 21 over the limit:**
idx 1 War Hammer · 2 Great Sword · 4 Flame Lance · 5 Devil Axe · 6 Dragon Slayer · 7,8 Langrisser · 9 Iron Dumbell · 10 Masayan Sword · 19 Odin's Buckler · 20 Small Shield · 21 Large Shield · 22 Chain Mail · 23 Plate Armor · 24 Assault Suit · 26 Dragon Scale · 27 Mirage Robe · 31 Speed Boots · 34 Rune Stone · 35 Not Equipped · 36 Unchanged

(The ~16 character names and ~16 item names not listed already fit within 8 chars.)

---

## 12. Emulator & reverse-engineering notes

- **SSF** = user's main emulator (no debugger; play-testing only).
- **Mednafen** = read/write memory breakpoints work (Shift+R/W, range `060A0000-060BFFFF`); PC breakpoints did NOT fire. Debugger: Alt+D toggle, Tab focus, Return jump, Space PC-bp, R resume, S step, Alt+3 memory view.
- **Memory map:** `0.BIN` loads at `0x060A8000`. Dialogue/battle engine overlay `0x06010000–0x06026000`. Text-render engine `~0x0604B000–0x0604E000`. Script (SCEN block) loads `~0x060A0000`. Command dispatcher `0x0604B970` (runtime-populated jump table). Box-frame drawer `0x0604CD18`. Word-copy primitive `0x0604D000`. Text drawn as **VDP1 sprites**.
- **Crash buffer** at `PC 0606B4D8` (see §6).
- Render-state vars (`0x060A6E00`, `0x060A7C88/90/94`, `0x060A7478`) are **transient** (zero when idle) — static dumps can't capture the cursor; needs a mid-render breakpoint with live state (never reliably captured → reason the half-width patch was abandoned).
- `FONT.DAT` lives in VDP VRAM (not in HWRAM dumps).
- Tools: capstone 5.0.7 disassembles SH-2 (`CS_ARCH_SH`, `CS_MODE_SH2|CS_MODE_BIG_ENDIAN`); `xdelta3` at `/usr/bin/xdelta3`.

---

_Last updated this session: prologues completed (all 20); names/menu buffer crash diagnosed (§6); item structure mapped; description box-growth test queued; prologue fitter tool delivered._
