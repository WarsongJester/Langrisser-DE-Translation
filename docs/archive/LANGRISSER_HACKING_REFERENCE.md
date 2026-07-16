> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> Route B breakthrough, Scenario 1 only — predates full-game completion.
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# Langrisser — Dramatic Edition (Sega Saturn) — Langrisser I English Translation
## Technical Hacking Reference & Project State

This document consolidates everything that has been reverse-engineered and built for
the fan-translation of **Langrisser I** (the first half of *Langrisser: Dramatic
Edition*, Sega Saturn). It is the authoritative reference — written to replace
re-reading the chat history.

---

## 1. Project Overview

- **Target:** *Langrisser - Dramatic Edition* (Sega Saturn, Japanese). Translating the
  **Langrisser I** half to English. (The disc also contains Langrisser II data, which we
  do not touch.)
- **Division of labour:** The user supplies English scripts (xlsx) and tests builds in
  the **SSF** emulator, reporting results via screenshots. Claude does all reverse
  engineering, text reinsertion, font work, disc rebuilding, and patch generation.
  Claude cannot run the game.
- **Delivery:** Builds are shipped as **xdelta3 patches** against the clean Japanese
  `.bin`, plus a `.cue`. The user applies the patch, renames the output, loads the cue
  in SSF with **PCM OFF**.

---

## 2. Files & Working Layout

**Source uploads** (`/mnt/user-data/uploads/`):
- `Langrisser_-_Dramatic_Edition__SAT_.7z` — original disc archive.
- `Langirsser_I_My_Script.xlsx` — main dialogue. Sheets `Scenario 1`..`Scenario 20`
  (06/08/09 use leading zeros). Markers: a blank/`<>` ends a message box, `<clsr>` =
  page break, each row = a line.
- `Other_Langrisser_Stuff.xlsx` — sheets: Scenario Quiz, Quiz Battle Explanations,
  Scenario Prologues, Endings, Names, Items, Menu.
- `kronos.bin`, `taylor.bin`, `freeze.bin` — HWRAM dumps (used to locate the crash).
- `LANGRISSER_PCM_ON.bkr` / `LANGRISSER_PCM_OFF.bkr` — PCM save states.
- `MxPlus_ToshibaSat_8x16.ttf` — Toshiba 8×16 bitmap font, used as the half-width glyph
  source for Route B.

**Working directory** (`/home/claude/lang/`, resets between sessions, persists within one):
- `extracted/LANG1/SCEN.DAT` (659,456 B), `extracted/LANG1/FONT.DAT` (220,732 B)
- `track1.iso` (the data track), `new_track1.iso` (rebuilt), the original raw `.bin`
- All Python tooling (see §10).

**Outputs** (`/mnt/user-data/outputs/`):
- `Langrisser1_EN_hw_scn1.xdelta` + `Langrisser1_EN_test.cue` — current half-width build.
- `LANGRISSER_HACKING_REFERENCE.md` — this document.

---

## 3. Disc Structure (Sega Saturn CD-ROM)

- Format: **MODE1/2352** for the data track (track 1), then MODE2 + audio tracks.
  Track 1 original length = **167,225 sectors**. Sector layout: 2352 raw bytes = sync +
  header + 2048 user bytes + EDC/ECC. Framing is handled by `cdecc.py`.
- The data track is an **ISO9660** filesystem. Two important file pairs exist:

  | File              | LBA     | Size (bytes) | Belongs to |
  |-------------------|---------|--------------|------------|
  | FONT.DAT          | 135070  | 220,732      | Langrisser I  ← we edit |
  | SCEN.DAT          | 136946  | 659,456      | Langrisser I  ← we edit |
  | FONT.DAT (2nd)    | 144527  | 220,732      | Langrisser II (untouched) |
  | SCEN.DAT (2nd)    | 157751  | 4,517,888    | Langrisser II (untouched) |

- **Disc rebuild method** (when SCEN grows): SCEN.DAT is enlarged in place; every file
  whose LBA ≥ `THRESH` (137268, the sector after original SCEN) is shifted by `K` sectors;
  all ISO9660 directory records are patched (SCEN size updated, shifted extents bumped);
  the PVD `volume_space_size` (LBA 16, offset 80, both LE and BE copies) is increased by
  `K`. Tracks 2–6 are appended shifted by `K`, and the `.cue` INDEX times are offset by
  `K`. **FONT.DAT is at LBA 135070 < SCEN, so it never shifts** — its modified bytes are
  spliced in place (same size).

---

## 4. SCEN.DAT — Script Container (fully cracked)

> **Full specification: `SCEN_DAT_FORMAT.md`.** Summary below.

Big-endian, three-level pointer structure: a top table of **21 block offsets** (block *i* =
**Scenario *i*+1**; block 0 = Scenario 1), each block holding section pointers + data, with
section 2 exposed as **10 string entries (0–9)** of `{00}`-separated strings. Quick index:

| Entry | Contents | Entry | Contents |
|------:|----------|------:|----------|
| 0 | UI / menu (139) | 5 | **dialogue** (per-scenario) |
| 1 | names (93) | 6 | win/lose (6) |
| 2 | items (142: names 0–36, desc 37+) | 7 | **title + prologue** (per-scenario) |
| 3 | debug menu (503, untouched) | 8 | scenario titles (20) |
| 4 | places (239) | 9 | empty |

Entries **0,1,2,3,4,8 are global** — duplicated identically in every block, so a name/item/
menu/title change must be written to **all 21 blocks**. Entries **5 and 7 are per-scenario**.
Codec `scen_codec.py` (`parse`/`serialize`) is lossless; only section-2 strings are edited,
pointer tables and 0x800 padding are regenerated.

---

## 5. Control Codes (inside dialogue/prologue strings)

| Code | Meaning |
|------|---------|
| `{06}{07}` | box advance / page break (next message box) |
| `{08}` | newline (line break within a box) |
| `{05}` | prologue format / indent marker |
| `{04}{XX}` | dictionary word (compression) — dropped when re-encoding. `{04}{1C}`=Winning Conditions, `{04}{1D}`=Losing Conditions, `{04}{01}`+digit+`{04}{83}`=SCENARIO-NN, `{04}{83}`≈ opening 「 |
| `{09}{XX}` | name insert |
| `{02}` | lord-name insert |
| `{03}` | prologue title setup |

A **dialogue box** is physically **3 lines × 14 full-width cells**. Scenario 1's dialogue
(entry 5) uses only `{06}{07}` and `{08}` — no name-inserts or dictionary codes after the
English pass.

---

## 6. Full-width Text Encoding (Route A renderer)

The native renderer is **strictly 2 bytes per cell**. The `sj()` encoder maps:
- ASCII letters/digits → full-width (Unicode `U+FEE0 + c`, i.e. SJIS 0x8260='A', 0x8281='a', 0x824F='0').
- space → `0x8140`.
- specials: `'`→U+2019, `"`→U+201D, `-`→U+2015, `` ` ``→U+2018.

---

## 7. FONT.DAT — Glyph Banks (cracked this session)

> **Full specification: `FONT_DAT_FORMAT.md`** (header pointers, exact bank offsets, the
> full SJIS↔kanji-slot math both directions, pair-glyph composition recipe). Summary below.

220,732 bytes. **7 big-endian pointers** then **6 glyph banks**; every glyph is
**16×16, 1bpp = 32 bytes**.

| Bank | Glyphs | Contents | JIS ku |
|------|-------:|----------|--------|
| S0 | 108  | symbols / punctuation | 1–2 |
| S1 | 162  | full-width ASCII (slots 0–78) + hiragana (79–161) | 3–4 |
| S2 | 150  | katakana + Greek | 5–6 |
| S3 | 81   | Cyrillic | 7 |
| S4 | 4418 | kanji — complete **47 ku × 94 ten** grid | 16–62 |
| S5 | 1978 | kanji level-2 (+ a few) | 63–83 |

Key facts: kanji banks are a **complete JIS grid**, so slot and SJIS code are computable
(`S4 slot=(ku-16)*94+(ten-1)`, `S5 slot=(ku-63)*94+(ten-1)`). **Pixel byte-swap:** per row,
byte0 = RIGHT 8px, byte1 = LEFT 8px; render `word=(byte1<<8)|byte0`. **Anchors:** S1 slot
0=`0`, 17=`A`, 49=`a`. **Spare pool:** only 92 blank slots exist, but the game displays just
825 of 6,396 kanji → **~5,571 kanji slots are safe to repurpose** (kana/Greek/Cyrillic are
NOT — still-Japanese UI renders them).

---

## 8. The Buffer Crash (dominant constraint for Route A)

Names, item names, and menu labels are copied into a **fixed ~8-full-width-char (~16-byte)
buffer**. A longer string overflows it and crashes: the CPU ends up executing `0x0000`,
observed at **PC 0606B4D8**.

- Confirmed crashers: "Imperial Commander" (17) at lord-select; long save/load menu
  messages; a multi-line item description (~50 bytes via `{08}`) on an *equipped* item
  processed in battle.
- Confirmed safe: ≤ 8 full-width chars.
- **Rules for Route A:** every name/label ≤ 8 full-width chars; English UI messages
  longer than the Japanese cannot go in those slots; item descriptions are a hard
  2 lines × 16 full-width chars with **no `{08}`** (it does not grow the box and inflates
  bytes). Status-bar names come from a *separate, not-yet-located* table/font path.

---

## 9. Two Rendering Approaches

### 9A. Route A — Full-width (shipped, in-game confirmed)
Each English letter occupies one full-width cell. Simple and proven, but: only 14 letters
per line, and the buffer crash caps every name/label at 8 chars. This is what the current
dialogue and prologues ship as.

### 9B. Route B — Half-width letter-pair packing (the breakthrough; no renderer patch)
Compose **two 8-pixel half-width letters into a single 16×16 glyph** (left half = char 1,
right half = char 2, honouring the byte-swap), store each composed glyph in an **unused
kanji slot**, and re-encode text to emit that kanji's SJIS code. The engine still draws
"one kanji per cell" — but the cell now shows two letters.

Why this is the path forward:
- **Doubles capacity:** 14 cells → 28 letters per line.
- **Halves byte count:** ~1 byte/letter instead of 2 → the 8-char name buffer now holds
  ~16 letters, so **the buffer crash dissolves** (names, item names, menu messages,
  multi-line descriptions all become feasible).
- **No SH-2/renderer patch** — only FONT.DAT glyphs and SCEN text change. (An earlier
  attempt to patch the renderer's X-advance — "Route A half-width" — was abandoned as
  untraceable; Route B sidesteps it entirely.)

Implementation details (as built for Scenario 1):
- Half-width glyphs are rendered from `MxPlus_ToshibaSat_8x16.ttf` via **freetype-py**
  (PIL/FreeType refuses to open this sfnt; freetype-py reads its embedded 8×16 bitmap
  strike directly). Glyph = 16 bytes (one per row, MSB = leftmost column).
- Pair glyph row: `FONT[base + r*2] = right_char_row`, `FONT[base + r*2+1] = left_char_row`.
- Encoding per dialogue string: split on authorial `{06}{07}`; per segment join the
  `{08}` lines, decode full-width → ASCII (NFKC + a small map for ' ' " — …), re-wrap to
  **28 chars**, paginate into boxes of ≤3 lines, **center each line** (character
  granularity, leading spaces), then pack two chars per cell. A `"  "` cell is emitted as
  the existing full-width space `0x8140` (saves a slot); any cell containing a letter gets
  a composed pair glyph.
- Slot assignment: distinct pairs are assigned unused kanji codes drawn from the high-ku
  (level-2) end first, skipping all 825 SCEN-used kanji.

**Scenario 1 result:** **359 distinct pairs**, SCEN unchanged in size (745,472 B = 364
sectors), FONT unchanged in size. End-to-end render verified correct from the real glyph
bytes (centered half-width).

---

## 10. Build Pipeline & Tooling (`/home/claude/lang/`)

Active scripts:
- **`scen_codec.py`** — `parse` / `serialize` for SCEN.DAT.
- **`parse_xlsx.py`** — `parse_sheet(ws)` → boxes; `is_speaker()` detects Title-Case
  speaker labels (validated, 0 false positives).
- **`reinsert_overflow.py`** — `sj()` encoder; `encode_box(box, width=14, maxlines=3)`
  re-segments dialogue into ≤3-line `{06}{07}` boxes; `patch(...)`. (Route A.)
- **`build_prologue.py`** — parse/wrap/paginate prologues; localizes the title (preserves
  setup + `{05}` wrappers, swaps the `{04}{83}` title text); body/conditions wrap to 14,
  ~5 lines/page, flush-left.
- **`build_all.py`** — MASTER Route A build → writes **`LANG1_SCEN_overflow.dat`**
  (English dialogue + all 20 prologues + item names capped at 8; menu currently disabled).
- **`rebuild_disc.py`** — grows SCEN in the ISO, shifts later files by `K`, patches
  directory records + PVD → `new_track1.iso`. Constants: `SCEN_LBA=136946`,
  `SCEN_OLD_SECT=322`, `THRESH=137268`, `TRACK1_SECT=167225`.
- **`final_assemble.py`** — frames `new_track1.iso` to MODE1/2352 via `cdecc.py`
  (fast-path reuses unchanged original sectors), appends tracks 2–6 shifted by `K`, writes
  the `.cue` with offset INDEX times.
- **`cdecc.py`** — EDC/ECC sector framing (validated).
- **`hw_build.py`** *(Route B, this session)* — renders the Toshiba font, re-encodes
  Scenario 1 entry 5 to centered half-width, composes pair glyphs into unused kanji slots,
  writes **`FONT_hw.DAT`** + **`SCEN_hw.dat`**.
- **`rebuild_disc_hw.py`** *(Route B, this session)* — same as `rebuild_disc.py` but reads
  `SCEN_hw.dat` and **splices `FONT_hw.DAT` in place at LBA 135070**.

Superseded/older: `reinsert*.py`, `reinsert_full.py`, `build_extras.py`, `build_scen.py`,
`build_template.py`, `rebuild_generic.py`, `extract_script.py`, `sjis_scan.py`.

**Build commands**

Route A (full-width, current shipping base):
```
python3 build_all.py            # → LANG1_SCEN_overflow.dat
python3 rebuild_disc.py         # → new_track1.iso
python3 final_assemble.py       # → Langrisser1_EN_test.bin + .cue
xdelta3 -e -9 -f -s "<ORIG_BIN>" Langrisser1_EN_test.bin <OUT>.xdelta
```

Route B (half-width Scenario 1, current test):
```
python3 build_all.py            # base English SCEN
python3 hw_build.py             # → FONT_hw.DAT + SCEN_hw.dat (359 pairs)
python3 rebuild_disc_hw.py      # → new_track1.iso (SCEN grown + FONT spliced)
python3 final_assemble.py       # → Langrisser1_EN_test.bin + .cue
xdelta3 -e -9 -f -s "<ORIG_BIN>" Langrisser1_EN_test.bin \
        /mnt/user-data/outputs/Langrisser1_EN_hw_scn1.xdelta
```

**Apply (user):** apply the xdelta to the clean JP `.bin` → name the output
`Langrisser1_EN_test.bin` → load `Langrisser1_EN_test.cue` in SSF → **PCM OFF**.

---

## 11. Status by Content

| Content | Status |
|---------|--------|
| **Dialogue (full-width)** | 14 scenarios DONE & confirmed in-game: 1,2,5,6,7,10,11,12,13,15,16,17,18,19. 6 need manual line-alignment (auto-align unreliable): 3,4,8,9,14,20. |
| **Prologues (all 20)** | DONE & confirmed (title localized, body/conditions wrapped to 14, indent removed). 13 titles wider than 14 wrap to 2 lines (optional shortening list given). |
| **Names (entry 1)** | Work for dialogue/unit-info but CRASH if > 8 chars (18 over-8 names listed for shortening). Status-bar names use a separate, un-located table. |
| **Item names (37)** | Translated, capped at 8 (safe). 21 over-8 listed for shortening. |
| **Item descriptions** | NOT done. Hard box = 2 lines × 16 full-width, no `{08}`. |
| **Menu** | ≤8-char labels translate cleanly but were REVERTED (a build crashed); long messages blocked by the buffer. Big entry-3 debug menu untouched. |
| **Scenario titles (entry 8), quiz, endings** | Not started; locations not yet fully mapped. |
| **"シナリオ N" intro card** | Separate asset, not located. |
| **PCM-off-by-default** | Save byte 0x24D (01/00), checksum 0x9D; boot default not flipped (non-blocking). |
| **Route B half-width (Scenario 1)** | **BUILT** — 359 pairs into unused kanji slots, Scenario 1 dialogue centered half-width; render verified; PENDING in-game test. This approach also fixes the buffer crash and is the candidate to scale to the whole game. |

---

## 12. Open Items / Next Steps

1. **Test the Route B Scenario 1 build in-game** (`Langrisser1_EN_hw_scn1.xdelta`):
   check readability/spacing of centered half-width, and watch for any garbled kanji
   elsewhere in Langrisser I (would indicate a repurposed slot that some non-dialogue
   asset actually uses).
2. If Route B looks good, **scale it to all 20 scenarios** (same `hw_build.py` re-encode
   loop) and **fold in names, item names, item descriptions, and menu messages** — half-
   width removes the 8-char buffer limit on all of them.
3. Manually align the 6 mismatched full-width scenarios (3,4,8,9,14,20) if Route A is kept
   for any of them.
4. Locate the **status-bar name table**, the **"シナリオ N" intro card**, scenario titles,
   quiz, and endings assets.

---

## 13. Quick Reference — Key Constants

```
FONT.DAT  : 220,732 B; header ptrs [0x1C,0xD9C,0x21DC,0x349C,0x3EBC,0x266FC,0x35E3C]
            glyph = 16×16 1bpp = 32 B; row word=(byte1<<8)|byte0 (byte1=LEFT, byte0=RIGHT)
            S1 anchors: slot0='0', 17='A', 49='a'
SCEN.DAT  : original 659,456 B = 322 sectors; LI LBA 136946
Disc LBAs : FONT(LI)=135070  SCEN(LI)=136946  FONT(LII)=144527  SCEN(LII)=157751
            track1=167225 sectors; THRESH=137268
Crash     : >8 full-width-char name/label buffer overflow → exec 0x0000 @ PC 0606B4D8
Kanji map : S4 slot=(ku-16)*94+(ten-1) [ku16-62]; S5 slot=(ku-63)*94+(ten-1) [ku63-83]
Spare pool: ~5,571 unused kanji slots (game uses only 825 of 6,396)
Route B   : 2 half-width letters per 16×16 cell in unused kanji slots; no renderer patch;
            doubles line capacity AND dissolves the buffer crash
```
