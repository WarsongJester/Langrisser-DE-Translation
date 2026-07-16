# Langrisser I (Sega Saturn, *Dramatic Edition*) — English Fan-Translation
## Complete Technical Handoff

**Purpose of this document.** A self-contained handoff so a new engineer can take over with
no access to prior chat history. It covers the disc, the file formats, the build pipeline,
what has been translated, and — in the most depth — the **in-game class-name system**, which
is the one unsolved frontier. Read §9 carefully; it is where the open work is.

**Last shipped build:** `Langrisser1_EN_45_classnames_JPrevert.xdelta` (see §4). This is a
full English story build with the in-game class/character-name system **reverted to original
Japanese** (a deliberate decision — see §9.7).

---

## 1. Project Overview & Working Model

- **Target.** *Langrisser – Dramatic Edition* (Sega Saturn, Japanese). The disc contains
  **both** Langrisser I and Langrisser II. We translate **Langrisser I only**; the
  Langrisser II files are never touched.
- **Division of labour.**
  - The **translator/tester** (project owner) supplies English scripts as xlsx spreadsheets
    and tests builds in emulators, reporting results via screenshots and emulator
    save-states.
  - The **engineer** (you) does all reverse engineering, text reinsertion, font work, disc
    rebuilding, and patch generation **offline**. The engineer never runs the game; every
    result is verified offline (byte/round-trip/render/EDC-ECC checks) and in-game effects
    are flagged as "pending test."
- **Iteration loop.** Engineer ships an xdelta patch → owner applies it to the clean JP
  `.bin`, runs it, screenshots/save-states → engineer diagnoses and revises.
- **Emulators in use.** SSF, Mednafen, and **Kronos**. Always run with **PCM audio OFF**.
  - **Kronos is required** for CRAM/palette inspection and for save-states used in deep
    screen traces. **Mednafen cannot read CRAM** (its `0x5F00000` view is a placeholder).

---

## 2. Deliverable Model

- Every build ships as an **xdelta3 delta against the clean Japanese `.bin`** plus a `.cue`.
- **Clean JP `.bin` size: 656,591,376 bytes.** This is the canonical source for every patch.
- **Apply procedure (owner side):**
  1. `xdelta3 -d -s <clean_JP.bin> <patch>.xdelta <output>.bin`
  2. Rename the output `.bin` to match the `FILE "..."` line in the shipped `.cue`.
  3. Load the `.cue` in the emulator with **PCM OFF**.
- Generating a patch (engineer side):
  `xdelta3 -e -9 -f -s <clean_JP.bin> <built>.bin <out>.xdelta`
- Always **round-trip verify**: decode the patch against the clean bin and confirm the
  SHA-256 of the result matches the built bin (use a streamed hash — the files are ~657 MB).

---

## 3. Disc Structure

The data track (track 1) is **MODE1/2352** (2352 raw bytes/sector = sync + header + 2048 user
bytes + EDC/ECC). It is an ISO9660 filesystem. Sector *N*'s 2048 user bytes live at file
offset `N*2352 + 16`.

| File | LBA | Size (bytes) | Role |
|------|-----|--------------|------|
| `LANG1.BIN` | 202 | 413,460 | LI program/overlay (SH-2 code + data + class/char names). Loads to CPU **0x06010000**. **Edited.** |
| `0.BIN` | 142 | 121,852 | LI data |
| `FONT.DAT` (LI) | 135070 | 220,732 | glyph banks — **edited** |
| `SCEN.DAT` (LI) | 136946 | 659,456 (orig) | script/text container — **edited** |
| `FONT.DAT` (LII) | 144527 | 220,732 | untouched |
| `SCEN.DAT` (LII) | 157751 | 4,517,888 | untouched |
| `IMG.DAT` | (various) | — | source of the **runtime-decompressed 8×8 font** (see §9.4) |
| `*.CPK` | various | large | compressed archives (movies, graphics) |

- Track 1 is **167,225 sectors**.
- `FONT.DAT` (LI) sits **before** `SCEN.DAT` (LI), so it never shifts when SCEN grows and can
  be spliced in place.
- The current dialogue build keeps `SCEN.DAT` the **same on-disc size** as the prior working
  build (in-place splice, no ISO resize), so no later files move and `.cue` geometry is
  unchanged.

### 3.1 The EN_45 +42-sector note (important for merges)

The English **story** build (EN_45) grew `SCEN.DAT`, which shifts every file at LBA ≥ the
threshold by **+42 sectors**. The class-name work, by contrast, was developed against **clean
JP at LBA 202** (LANG1 doesn't move because it's before SCEN). The merged build
`en45_combined.bin` (656,690,160 bytes, +42 sectors) is the EN_45 story build into which
LANG1/FONT edits are spliced at their fixed LBAs (LANG1 @ 202, FONT @ 135070). When producing
a final merged release, **account for the +42-sector shift** on anything past the SCEN
threshold (LANG1 and FONT are both before SCEN, so they are unaffected).

---

## 4. Output Files (what exists today)

All in the outputs directory. The **JPrevert** patch is the current recommended build.

| File | What it is |
|------|------------|
| `Langrisser1_EN_45_classnames_JPrevert.xdelta` / `.cue` | **CURRENT.** EN_45 English story + **original Japanese** class/char names (clean, no garble). |
| `Langrisser1_EN_45_classnames_v3.xdelta` / `.cue` | Attempt to render troop-purchase names in English via a renderer patch. Bottom bar correct; **troop names still garbled in-game** (see §9.6). Superseded. |
| `Langrisser1_EN_45_classnames_panel*.xdelta` | Earlier baselines; 16×16 status panel English class names (the one path that works for English). |
| `Langrisser1_EN_45_classnames_namefix.xdelta` | **Broken** (shifted the whole conversion table +9 and garbled the bottom bar). Do not use. |
| `LANGRISSER1_HANDOFF.md` | This document. |

**Cue geometry** (shared by all class-name builds; copy when making new cues):
```
FILE "<name>.bin" BINARY
  TRACK 01 MODE1/2352   INDEX 01 00:00:00
  TRACK 02 MODE2/2352   INDEX 01 37:10:17
  TRACK 03 AUDIO        INDEX 01 52:23:62
  TRACK 04 AUDIO        INDEX 01 53:20:42
  TRACK 05 AUDIO        INDEX 01 54:57:25
  TRACK 06 AUDIO        INDEX 01 61:54:55
```

---

## 5. SCEN.DAT — Script Container (fully reverse-engineered)

Big-endian, three-level pointer structure; parse/serialize round-trips losslessly.

```
SCEN.DAT
├─ Top table : 22 block offsets (each block padded to a 0x800 boundary)
└─ Blocks[0..20]
   └─ Block: section pointer list + section data
      └─ Section 2 = string table → exposed as "entries" of {00}-separated strings
```

- **Block *i* = Scenario *i*+1.** Block 0 = Scenario 1 … block 19 = Scenario 20.
  **Block 20 = the extra/global block** (opening quiz, battle tutorial).
- Section 2 is the only edited section. On serialize, pointer tables and 0x800 padding are
  regenerated.

**Entries (logical string groups inside section 2):**

| Entry | Contents | Scope |
|------:|----------|-------|
| 0 | UI / menu (incl. **troop types** 歩兵→Soldier, etc.) | global |
| 1 | names (characters + a few unit types) | global |
| 2 | items (names 0–36, descriptions 37+) | global |
| 3 | debug / sound-test menu (incl. a battle-test class roster with Ｔ/Ｇ/Ｎ/Ｃ faction suffixes) | global |
| 4 | places | global |
| 5 | **dialogue** (per scenario); **opening quiz** in block 20 | per-block |
| 6 | win/lose (per scenario); **battle tutorial** in block 20 | per-block |
| 7 | title + prologue | per-scenario |
| 8 | scenario titles | global |
| 9 | empty | — |

- **Global entries (0,1,2,3,4,8)** are duplicated identically in every block. A change to a
  name/item/menu/title must be written to **all 21 blocks** or it shows only in some
  scenarios.

**Control codes** (inside dialogue/quiz/prologue strings):

| Code | Meaning |
|------|---------|
| `{06}{07}` | box advance / page break (next message box) |
| `{08}` | newline (line break within a box) |
| `{05}` | format/indent marker — also used at the start of quiz continuation boxes |
| `{04}{XX}` | dictionary-compressed word (re-encoded English drops these). Known: `{04}{1C}`=Winning Conditions, `{04}{1D}`=Losing Conditions, `{04}{01}`+digit+`{04}{83}`=SCENARIO-NN, `{04}{83}` ≈ opening 「 |
| `{09}{XX}` / `{02}` | name insert / lord-name insert |
| `{03}` | prologue title setup |

- A dialogue box is physically **3 lines × 14 full-width cells**.
- **Quiz box rendering quirk:** the quiz box is 3 lines tall and its renderer **skips the
  first line of every continuation box**. The Japanese fills that line with `{05}{08}`. So
  encode box 1 with up to 3 lines, and every box after it must **begin with `{05}{08}`** then
  up to 2 lines. Omitting that marker eats the first content line of each continuation box.

---

## 6. FONT.DAT — Glyph Banks (fully reverse-engineered)

220,732 bytes: **7 big-endian uint32 pointers**, then **6 glyph banks** back-to-back. Every
glyph is **16×16, 1 bit/pixel = 32 bytes** (16 rows × 2 bytes/row).

| Ptr index | Value | Bank | Glyphs | Contents |
|-----------|-------|------|-------:|----------|
| 0 | 0x0001C | S0 | 108 | symbols / punctuation |
| 1 | 0x00D9C | S1 | 162 | full-width ASCII (slots 0–78) + hiragana (79–161) |
| 2 | 0x021DC | S2 | 150 | katakana + Greek |
| 3 | 0x0349C | S3 | 81 | Cyrillic |
| 4 | 0x03EBC | S4 | 4418 | kanji — complete 47 ku × 94 ten grid |
| 5 | 0x266FC | S5 | 1978 | kanji level-2 |
| 6 | 0x35E3C | — | — | end of S5 |

- **Glyph at bank-base `B`, slot `n`** starts at `B + n*32`.
- **Row byte-swap quirk:** within a row, `byte[r*2]` = RIGHT 8 px, `byte[r*2+1]` = LEFT 8 px.
  Render `word = (byte[r*2+1] << 8) | byte[r*2]` (bit15 = leftmost column). A symmetric glyph
  looks fine if you forget the swap; asymmetric glyphs come out mirrored-in-halves.
- **S1 ASCII anchors:** slot 0 = `0` (digits 0–9 = slots 0–9), slot 17 = `A` (A–Z = 17–42),
  slot 49 = `a` (a–z = 49–74), slots 79–161 = hiragana.
- **Kanji slot ↔ (ku,ten):** `S4 slot=(ku-16)*94+(ten-1)` for ku 16–62; `S5 slot=(ku-63)*94+(ten-1)`
  for ku 63–83. SJIS↔(ku,ten) conversion is in `FONT_DAT_FORMAT.md` and is round-trip exact.
- **Spare pool:** the game displays only ~825 distinct kanji of 6,396, so **~5,571 kanji
  slots are safe to repurpose**. Kana / Greek / Cyrillic slots are **NOT** safe (still-Japanese
  UI renders them).

> **NOTE:** FONT.DAT is the **16×16** glyph source. The **8×8** font used by the in-game class
> names is a *different* asset (runtime-decompressed from IMG.DAT — see §9.4). Editing FONT.DAT
> does nothing for the 8×8 class-name screens.

---

## 7. Route B — Half-Width Letter-Pair Packing (the dialogue technique)

The native SCEN renderer is **strictly 2 bytes per cell** (one double-byte code = one cell).
Route B composes **two 8-pixel half-width letters into a single 16×16 cell** (left half = char
A, right half = char B, honouring the byte-swap), stores that composed glyph in an unused
kanji slot, and emits that kanji's SJIS code in the text. The engine still draws "one kanji
per cell," but the cell now shows two letters.

- **Doubles capacity** (14 cells/line → 28 half-width letters/line) and **halves byte count**,
  which dissolves the old fixed-buffer crash for names/labels.
- **No CPU/renderer patch** — only FONT glyphs and SCEN text change.
- Half-width glyphs are rendered from `MxPlus_ToshibaSat_8x16.ttf` via **freetype-py** (PIL
  can't open this sfnt). Pair glyph row: `FONT[base+r*2] = right_row`, `FONT[base+r*2+1] =
  left_row`. A `"  "` cell reuses the existing full-width space `0x8140` to save a slot.
- **Glyph-allocation safety:** before placing pair glyphs, the build reserves (1) all S4/S5
  kanji used by kept SCEN content, (2) **all S4/S5 kanji referenced by LANG1.BIN and 0.BIN**
  (world-map place names live there), and (3) prior-build-changed slots. Pair glyphs are
  drawn only from the remaining free pool; every build re-verifies `changed-slots ∩
  externally-referenced-slots = 0`.

**Historical buffer crash:** names/labels were copied into a fixed ~16-byte buffer; >8
full-width chars overflowed it and crashed (CPU executes `0x0000`, PC `0606B4D8`). Route B's
half-byte-per-letter packing removes this for dialogue/names/item-names. Item **descriptions**
keep a hard limit of **2 lines × 16 cells (32 bytes), no `{08}`**.

---

## 8. Build Pipeline & Tooling

Working directory `/home/claude/lang/` **resets between sessions**; rebuild infrastructure
from the owner's uploads and the persistent outputs directory each session. Disk is tight
(~3.7 GB free) — a second full disc copy is generally not viable; **extract files from an
already-built disc** rather than applying xdelta to make a second full copy.

Key modules / helpers:

| Module | Role |
|--------|------|
| `scen_codec.py` | SCEN.DAT parse/serialize (lossless) |
| `fontlib.py` / `glyphlib.py` | glyph read/write; render 8-px half-width glyphs from the Toshiba TTF |
| `encoder.py` | `GlyphAlloc`; `encode_message` (28-wide dialogue boxes); `encode_quiz_message`; `encode_name` |
| `prologue.py`, `itemdesc.py`, `quizbattle.py` | per-content encoders |
| `cdecc.py` | **EDC/ECC Mode-1 sector framing.** Has `reframe(sector2352, lba)` (validated). |
| `splice.py` | in-place splice of a file's bytes into the working `.bin`, re-framing each touched sector |
| `build_hw.py` | master build → `SCEN_hw.dat` + `FONT_hw.DAT` |

**Splice rule (critical):** when overwriting a file's sectors in the `.bin`, write
`sector[16:16+len(chunk)] = chunk` (the chunk is the *remaining* file bytes for the last
sector, **not** a fixed 2048), then `cdecc.reframe(sector, lba)` to fix EDC/ECC.

**Disassembly:** Capstone, SH-2 big-endian:
`Cs(CS_ARCH_SH, CS_MODE_BIG_ENDIAN | CS_MODE_SH2)`.

**Every build is validated offline:** changes localized to expected LBA ranges; EDC/ECC valid
on sampled changed sectors; xdelta reproduces the built bin byte-for-byte; all emitted glyph
codes resolve; glyph-collision overlap with external assets = 0.

---

## 9. THE IN-GAME CLASS-NAME SYSTEM (the open frontier)

This is the hard part and the reason for the current Japanese revert. Read this whole section
before attempting anything.

### 9.1 High-level summary

In-game **class names** (e.g. Lord, Fighter, Knight) and **character/unit names** (Ledin,
Volkoff…) shown in menus and HUD are **text**, but they belong to a **separate text system**
from SCEN dialogue: null-terminated strings in **LANG1.BIN**, fed through **custom renderers**
with **custom code pages**, **not** standard SJIS→FONT.DAT.

There are **three renderers** that consume the **same shared strings via one shared pointer
table**. That sharing is the core constraint: you cannot make one screen show English and
another show Japanese from the same string (see §9.7).

### 9.2 The shared string pool (LANG1.BIN, loaded at CPU 0x06010000)

> File offsets below are LANG1.BIN file offsets; CPU address = `0x06010000 + file_offset`.

| Region (file) | Contents |
|---------------|----------|
| `0x617A0–0x61C27` | **Main class list** (null-terminated). In the English builds: FIGHTER, GLADIATOR, VAMPIRE, KNIGHT, PIRATE, HAWK KNIGHT, …, LORD, …, BISHOP, GRAND KNIGHT, BASILISK, EFREET (~136 entries). **Originally Japanese katakana.** |
| `0x61C2C–0x6202C` | **Pointer table.** ~255/256 entries, 4-byte big-endian, classID → string address (base `0x06010000`), with duplicate entries. |
| `0x6202C–0x622E0` | **Second list:** character/boss names (LEDIN, NARM, CHRIS, TAYLOR, JESSICA, …, VOLKOFF, …) **plus** generic unit labels (SOLDIER, COMMANDER, PRIEST, VILLAGER, PIRATE, …). |
| `0x62314+`, `0x62866`, `0x6291A` | additional index/pointer tables for the second list. |

In the original Japanese game **all of these are katakana strings**; the project rewrote them
to English ASCII in-place and rebuilt the pointer tables. (The original conversion table at
`0x64DB0` is **all zeros for ASCII** — the original game never indexes ASCII, because the
strings were Japanese. The ASCII→glyph table is a project creation; see §9.5.)

### 9.3 The three renderers

**(A) Bottom status bar — the "C000 renderer."**
- Code at CPU **0x0601C000** (file `0xC000`); pixel drawer at **0x0601BED8**.
- Renders the persistent HUD: "SCENARIO/TURN", selected-unit stats, and unit class/char
  names in the bar. Glyphs are **8×8 half-width**.
- Uses a **256-byte ASCII→glyph conversion table** at CPU **0x06074DB0** (file `0x64DB0`):
  `glyph = table[char]`. The table is **referenced only at file `0xC040`**, so editing it only
  affects this renderer.
- Its tile plane **charbase = 4105**. The table is calibrated for this charbase.
- Drawer writes `word = (palette<<12) | glyph` into a **38-cell-wide work-RAM tilemap at
  0x060989D0**, later DMA'd to VDP2 VRAM.

**(B) Troop-purchase / battle-forecast middle names — the "0x288D8 renderer."**
- Code at CPU **0x060388D8** (file `0x288D8`).
- Renders the class/character names in the troop-purchase middle box (and, it is believed,
  the battle-forecast unit info). Glyphs are **8×8 half-width**.
- Original char→glyph dispatch (file `0x288F0`–`0x2893E`): four special-char cases
  (chars `0xDE`,`0xDF`,`0xB0`,`0xA5` → glyphs 112,113,110/±,32) then a **general case
  `add #-53,r7`** at file **`0x2893E`** for everything else.
- Tile plane **charbase = 4096** (9 less than the bottom bar) — determined empirically (the
  `+9` relationship below).
- Blitter pointer `r12 = 0x0603C7AC` (literal at file `0x28968`, loaded at file `0x288F0`).
- Because the font's A–Z is **scattered** (see §9.4/§9.5), the `add #-53` general case maps
  English ASCII to wrong cells → garbage.

**(C) 16×16 class-change / character-status panel.**
- A **different** renderer that draws from **FONT.DAT** (which has every Latin letter).
- Char loop near file `0x1B150`; project renderer edits are at files `0x1B276–0x1B2C8` and
  `0x1B316`.
- **This is the only path that renders English class names cleanly** (verified in-game:
  the status screen showed "Ledin / LORD / Soldier" correctly).

### 9.4 The 8×8 font (renderers A and B)

- The 8×8 half-width font is **runtime-decompressed from IMG.DAT** into **VDP2 VRAM at cell
  4096 (VRAM offset 0x20000)**. It is **NOT in FONT.DAT** and **cannot be statically edited**
  in FONT.DAT.
- It contains a **complete but scattered A–Z** — there is **no contiguous alphabet block**.
  (So no font injection is ever required for English; only a correct char→cell conversion.)
- **Cell math:** VRAM byte offset = `cell * 32`, base `0x25E00000`; cell 4096 = `0x20000`.
  (This was a repeated source of off-by errors — double-check it.)

### 9.5 The project's ASCII→glyph conversion table (file 0x64DB0)

Calibrated for **charbase 4105** (renderer A). Letters are scattered; digits are contiguous.

```
A=1   B=205 C=155 D=3   E=156 F=4   G=143 H=8   I=204 J=202 K=200 L=10  M=5
N=141 O=160 P=6   Q=42  R=140 S=154 T=138 U=139 V=7   W=201 X=56  Y=203 Z=44
0..9 = 18..27        space(0x20) = 64
```
- At charbase 4105: `cell = 4105 + table[char]`.
- **One genuine bug:** `table['O'] = 160` points at a blank/block cell (4265). The real `O`
  glyph is at cell **4264**, i.e. `table['O']` should be **159**. Fixing this single byte
  corrects O in renderer A; it does **not** affect any other character.

### 9.6 What was tried, and the central unsolved discrepancy

1. **Shifting the whole table `+9`** (to serve charbase 4096): **broke the bottom bar** (which
   legitimately needs the unshifted table at 4105) and did **not** fix the troop names.
   Reverted. *(This is the `namefix` patch — do not use it.)*

2. **Patching renderer B (0x288D8) to `glyph = table[char] + 9`** (the `+9` accounts for its
   4096 charbase vs the table's 4105), plus fixing `table['O']=159`:
   - **Offline render: perfect.** Reading the *actual VRAM* from a Kronos save-state of the
     troop-purchase screen and applying `cell = 4096 + table[char] + 9`, every name rendered
     pixel-correct: SOLDIER, SPEARMAN, FIGHTER, LEDIN, LORD, HAWK KNIGHT, VOLKOFF, BISHOP
     (including O and spaces).
   - **In-game: still garbled.** The middle-box text changed from the byte-53 garble to a
     *different* garble — i.e. the patch took effect but did not produce the names.
   - The exact surgery used (for reference) replaced the dispatch at file `0x288FA`:
     `mov r7,r0; mov.l @(24,PC),r1; mov.b @(r0,r1),r7; extu.b r7,r7; add #9,r7; mov r9,r6;
     bra 0x6038942; nop`, with `table_ptr = 0x06074DB0` written at file `0x28960`, and the old
     dispatch nop-filled. *(This is the `v3` patch.)*

> **THE KEY UNSOLVED QUESTION.** The offline model (`cell = 4096 + table[char] + 9`) reproduces
> the names exactly from the *captured VRAM*, but the live screen does not match. That
> discrepancy means one of the following is true for the troop-purchase **middle-box** text,
> and the next person must determine which **with a live debugger**:
>   - the plane's actual charbase for that text is **not 4096** (the 4096 figure was inferred
>     from a different element — a troop-type label — that may sit on a different plane), **or**
>   - the bytes being rendered there are **not the class-name string** we patched (could be a
>     number/stat field, or a different string entirely), **or**
>   - the middle box uses a **different renderer/codepath** than `0x288D8`.
>
> Until that is pinned down live, any static patch is guesswork.

### 9.7 Why English is blocked, and the shared-string constraint

A clean English result on **all** screens needs both:
1. The exact code→VRAM-cell mapping for renderers A and B confirmed **live** (the offline/
   in-game discrepancy in §9.6 must be resolved), and
2. No regressions on the bottom bar (renderer A is correct as-is for 25 of 26 letters).

**The shared-string, all-or-nothing reality:** class names and character names come from one
string pool indexed by one pointer table, and the renderers are shared:
- **Japanese strings require the original renderers** (which expect the original code page).
- **English ASCII strings require modified renderers** (table-based).
- On the **status panel** (renderer C), both class names *and* character names go through the
  **same** 16×16 renderer — so you cannot show English character names and Japanese class
  names on that screen simultaneously.

Therefore you cannot mix "English on screen X, Japanese on screen Y" from the same strings.
It is all-English (with the 8×8 rendering still unsolved) **or** all-Japanese (clean).

### 9.8 Current decision: revert to Japanese (the shipped JPrevert build)

Because the 8×8 English rendering is unsolved and the system is all-or-nothing, the current
build **reverts the entire LANG1 class/character-name machinery to original Japanese**:
- `Langrisser1_EN_45_classnames_JPrevert.xdelta` splices the **original clean-JP LANG1.BIN**
  (LBA 202) into the EN_45 combined build, leaving FONT/SCEN (all the English story work)
  untouched.
- Result: troop-purchase, battle-forecast, bottom bar, and status/class-change screens all
  show **clean original Japanese**; everything else (dialogue, prologues, items, titles, quiz,
  tutorial, troop **types**) stays English.
- Tradeoff: menu **character** names are Japanese while the **story** uses English names — an
  unavoidable consequence of the shared system.

### 9.9 Recommended path forward (for whoever picks this up)

1. **Get Kronos save-states** on (a) the troop-purchase screen with the middle box visible and
   (b) the battle-forecast screen. (Kronos save format: VDP2 section tag `VDP2`; VRAM is the
   first `0x80000` of its payload. The other-state tag is `OTHR`.)
2. **Live-trace renderer B (0x060388D8)** and the bottom-bar renderer (0x0601C000) in a
   debugger:
   - Breakpoint at each renderer's entry; capture **the string pointer passed in** (which
     string is it actually rendering?).
   - Read the **VDP2 plane registers** for the target plane to get its **real charbase** for
     that specific screen (do not assume 4096/4105).
   - Watch the **work-RAM tilemap target** and the glyph word written per character.
   - This resolves the §9.6 discrepancy directly.
3. Once the real `(string, charbase, cell-mapping)` for the troop-purchase/battle text is
   known, either patch that renderer's conversion to hit the correct cells, or confirm the
   text isn't the class string (and chase the real source).
4. Remember: **the 8×8 font already has a complete A–Z** (scattered). **No font injection is
   needed** — only the conversion. (An earlier "inject an A–Z block" approach was a dead end
   because the game's own glyphs overwrote the injected cells, and because injection was never
   necessary.)
5. **Lowest-risk hybrid** if full English proves intractable: keep the **16×16 status/
   class-change panel in English** (renderer C handles English cleanly and is independent of
   the 8×8 planes) while leaving troop-purchase and battle in Japanese. This split is feasible
   because renderer C is the one path that works; it would require keeping the English class
   strings + renderer-C edits but reverting only what the 8×8 screens need — which again hinges
   on resolving §9.6 (whether the 8×8 screens read the same strings).

### 9.10 Things that look like leads but are NOT

- **SCEN.DAT entry 3** is the debug/sound-test **battle-test roster** (class names with
  Ｔ/Ｇ/Ｎ/Ｃ faction suffixes). Editing it has **zero** in-game effect on real class names
  (verified). Useful only as a class-list cross-reference.
- **FONT.DAT** is irrelevant to the 8×8 class names (those use the IMG.DAT runtime font).
- The class names are **not** pre-rendered graphics and are **not** in SCEN.DAT (both were
  early wrong guesses).
- **Troop *types*** (歩兵→Soldier, 長槍→Spearman, etc.) are a **different** system — SCEN entry
  0, standard SJIS→FONT.DAT — and are **fully translated and confirmed in-game**. Do not
  conflate the troop *type* (working English) with the unit *class* name (the 8×8 problem).

---

## 10. Translation Status

| Content | Status |
|---------|--------|
| Dialogue (all 20 scenarios) | **DONE** (Route B half-width, 28 chars/line) |
| Prologues (all 20) | **DONE** (titles localized, bodies/conditions wrapped) |
| Names — SCEN entry 1 | **DONE** |
| Item names (entry 2, 0–36) | **DONE** |
| Item descriptions (entry 2, 37+) | **DONE** (buffer-safe: ≤2 lines × 16 cells, no `{08}`) |
| Scenario titles (entry 8) | **DONE**; repeated deployment-map banner reads title slot 0 and is blanked (trade-off: Scenario 1's own banner is also blank) |
| Opening quiz (block 20, entry 5) | **DONE** (69/69; `{05}{08}` continuation fix applied; comedic alt-intro strings 5–9 left Japanese — not in the source file) |
| Battle tutorial (block 20, entry 6) | **DONE** (17/18; slot 17 empty) |
| Troop **types** (entry 0) | **DONE — confirmed in-game** |
| Glyph-collision safety | enforced every build (overlap = 0) |
| **In-game class/character names** | **REVERTED TO JAPANESE** (see §9) — English on 8×8 screens unsolved |
| "シナリオ N" intro card | not done (separate hardcoded/graphic asset) |

**Outstanding SCEN text tasks (small):**
- **Entry-4 place names** — untranslated place names (notably SCEN entry 4) still pending.
- **"Undease" → "Undead"** — a troop-type/SCEN-line typo (entry 0) to correct.

---

## 11. Quick Reference — Key Constants

```
Clean JP .bin : 656,591,376 bytes  (canonical xdelta source)
EN_45 combined: 656,690,160 bytes  (+42 sectors vs clean)

Disc LBAs : LANG1.BIN=202  0.BIN=142  FONT(LI)=135070  SCEN(LI)=136946
            FONT(LII)=144527  SCEN(LII)=157751 ; track 1 = 167,225 sectors
            data track = MODE1/2352 ; user bytes at sector*2352 + 16 (len 2048)

LANG1.BIN : loads to CPU 0x06010000 ; size 413,460 (0x64F14)
  Class strings (main)   file 0x617A0–0x61C27
  Pointer table          file 0x61C2C  (4-byte BE, classID→addr, base 0x06010000)
  Char/2nd-list strings  file 0x6202C–0x622E0  (+ index tables 0x62314, 0x62866, 0x6291A)
  Bottom-bar renderer    CPU 0x0601C000 (file 0xC000) ; drawer 0x0601BED8
  Conversion table       CPU 0x06074DB0 (file 0x64DB0) ; ref'd only at file 0xC040
                         charbase 4105 ; table['O']=160 BUG (should be 159 = cell 4264)
  Bottom-bar work tilemap 0x060989D0 (38 cells wide)
  Troop/battle renderer  CPU 0x060388D8 (file 0x288D8) ; charbase 4096 ; blitter r12=0x0603C7AC
                         general char case `add #-53,r7` at file 0x2893E
  16×16 panel renderer   char loop ~file 0x1B150 (English-capable; status screen works)

8×8 font  : runtime-decompressed from IMG.DAT to VDP2 VRAM cell 4096 (0x20000)
            complete but SCATTERED A–Z ; NOT in FONT.DAT ; cell→VRAM = cell*32 (base 0x25E00000)
            renderer B needs glyph = table[char] + 9  (charbase 4096 vs table's 4105)

FONT.DAT  : 220,732 B; pointers [0x1C,0xD9C,0x21DC,0x349C,0x3EBC,0x266FC,0x35E3C]
            glyph = 16×16 1bpp = 32 B; row word = (byte1<<8)|byte0 (byte1=LEFT, byte0=RIGHT)
            S1 anchors: slot 0='0', 17='A', 49='a'
            Kanji: S4 slot=(ku-16)*94+(ten-1) [ku16-62]; S5 slot=(ku-63)*94+(ten-1) [ku63-83]
            Spare pool ~5,571 unused kanji slots (kana/Greek/Cyrillic NOT safe)

SCEN.DAT  : original 659,456 B; 22-entry top table; block i = Scenario i+1; block 20 = global
            entries 0,1,2,3,4,8 global (write to all 21 blocks); 5,6,7 per-block
Widths    : dialogue 28 half-width/line ≤3 lines/box ; item desc ≤32 hw/line ≤2 lines + stat, no {08}
            quiz continuation boxes start with {05}{08}
Crash     : >16-byte name buffer or >32-byte desc line → exec 0x0000 @ PC 0606B4D8

Tooling   : Capstone Cs(CS_ARCH_SH, CS_MODE_BIG_ENDIAN|CS_MODE_SH2)
            cdecc.reframe(sector2352, lba) for EDC/ECC ; splice = sector[16:16+len(chunk)]=chunk
            8×8 font source for English would be the IMG.DAT runtime font (already complete A–Z)
            Emulators: SSF / Mednafen / Kronos, PCM OFF ; Kronos required for CRAM + save-states
```

---

## 12. Open Items / Backlog

1. **In-game class names (the frontier).** Resolve the §9.6 offline/in-game discrepancy with a
   live debugger (§9.9). The current build ships these as Japanese.
2. **Entry-4 place names** — last SCEN text translation task.
3. **"Undease" → "Undead"** — small SCEN entry-0 correction.
4. **"シナリオ N" intro card** — separate hardcoded/graphic asset; not located.
5. **Final merged release** — fold the chosen class-name decision into the EN_45 full release,
   accounting for the **+42-sector** SCEN shift (LANG1 and FONT are before SCEN and unaffected).
6. **Japanese graphic labels** that are image assets, not text (e.g. the 兵士配属 troop-purchase
   title, the 種類 battle-forecast header) — would require graphics work, separate from the
   text systems above.

---

*End of handoff. The most valuable next step is a Kronos save-state on the troop-purchase and
battle-forecast screens plus a live breakpoint on the 0x060388D8 and 0x0601C000 renderers —
that single trace resolves the central open question in §9.6.*
