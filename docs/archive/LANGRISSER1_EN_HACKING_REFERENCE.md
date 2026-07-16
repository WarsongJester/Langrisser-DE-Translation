> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> Intermediate master (all text done, class names still 'deferred'). Superseded by the EN_45 master and the class-name solution.
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# Langrisser I (Sega Saturn, *Dramatic Edition*) — English Translation
## Consolidated Hacking Reference

This is the single authoritative record of the Langrisser I fan-translation: what has been
reverse-engineered, what has been translated, how each piece works, and what remains. It
supersedes scattered notes and chat history.

---

## 1. Project at a Glance

- **Target:** *Langrisser – Dramatic Edition* (Sega Saturn, Japanese). We translate the
  **Langrisser I** half. The disc also holds Langrisser II data, which we do not touch.
- **Division of labour:** You supply English scripts (xlsx) and test builds in the **SSF**
  emulator (PCM OFF), reporting via screenshots. All reverse engineering, text reinsertion,
  font work, disc rebuilding, and patch generation is done in the toolchain. The game is
  never run on this side — every result is verified offline (byte/round-trip/render/EDC-ECC)
  and in-game effects are flagged as pending your test.
- **Delivery:** an **xdelta3 patch** against the clean Japanese `.bin`, plus a `.cue`.
  Apply the patch → name the output `Langrisser1_EN_test.bin` → load
  `Langrisser1_EN_test.cue` in SSF with **PCM OFF**.
- **Core technique:** *Route B half-width packing* (see §4). No emulator or CPU patch is
  required — only font glyphs and SCEN text change.

---

## 2. Disc Layout

The data track (track 1) is **MODE1/2352** (2352 raw bytes/sector = sync + header + 2048
user bytes + EDC/ECC). It is an ISO9660 filesystem. Sector *N*'s user data lives at file
offset `N*2352 + 16`, length 2048.

Files we care about (LBA = logical block address = sector number):

| File | LBA | Size (bytes) | Role |
|------|-----|--------------|------|
| FONT.DAT (LI) | 135070 | 220,732 | glyph banks — **edited** |
| SCEN.DAT (LI) | 136946 | 659,456 (orig) | script/text container — **edited** |
| LANG1.BIN | 202 | 413,460 | LI program/overlay (SH-2 code + data; world-map names) |
| 0.BIN | 142 | 121,852 | LI data |
| FONT.DAT (LII) | 144527 | 220,732 | untouched |
| SCEN.DAT (LII) | 157751 | 4,517,888 | untouched |
| `*.CPK` | various | large | compressed archives (movies, graphics) — see §11 |

Track 1 is 167,225 sectors. FONT.DAT (LI) sits **before** SCEN.DAT, so it never shifts and
is spliced in place. The current build keeps SCEN.DAT the **same on-disc size as the prior
working build** (in-place splice, no ISO resize), so no later files move and the `.cue`
geometry is unchanged.

---

## 3. SCEN.DAT — Script Container (fully cracked)

Big-endian, three-level pointer structure:

```
SCEN.DAT
├─ Top table : 22 block offsets (each block padded to a 0x800 boundary)
└─ Blocks[0..20]
   └─ Block: section pointer list + section data
      └─ Section 2 = string table → exposed as "entries" of {00}-separated strings
```

- **Block *i* = Scenario *i*+1.** Block 0 = Scenario 1 … block 19 = Scenario 20.
  **Block 20 = the extra/global block** (opening quiz, battle tutorial, etc.).
- **Entries** (the logical string groups inside section 2):

  | Entry | Contents | Scope |
  |------:|----------|-------|
  | 0 | UI / menu | global |
  | 1 | names (characters + a few unit types) | global |
  | 2 | items (names 0–36, descriptions 37+) | global |
  | 3 | **debug / sound-test menu** (incl. suffixed class labels) | global |
  | 4 | places | global |
  | 5 | **dialogue** (per scenario); **opening quiz** in block 20 | per-block |
  | 6 | win/lose (per scenario); **battle tutorial** in block 20 | per-block |
  | 7 | title + prologue | per-scenario |
  | 8 | scenario titles | global |
  | 9 | empty | — |

- **Global entries (0,1,2,3,4,8)** are duplicated identically in every block, so any change
  must be written to **all 21 blocks** or it only shows in some scenarios.
- The codec (`scen_codec.py`) `parse`/`serialize` is byte-exact lossless; only section-2
  strings are edited, and pointer tables + 0x800 padding are regenerated.

### Control codes (inside dialogue/quiz/prologue strings)

| Code | Meaning |
|------|---------|
| `{06}{07}` | box advance / page break (next message box) |
| `{08}` | newline (line break within a box) |
| `{05}` | format/indent marker — used at the start of **quiz continuation boxes** (see §6) |
| `{04}{XX}` | dictionary-compressed word (re-encoded English simply drops these) |
| `{09}{XX}` / `{02}` | name insert / lord-name insert |
| `{03}` | prologue title setup |

---

## 4. FONT.DAT and Route B (the half-width breakthrough)

FONT.DAT is 220,732 bytes: 7 big-endian pointers, then 6 glyph banks back-to-back. Every
glyph is **16×16, 1 bit/pixel = 32 bytes** (16 rows × 2 bytes).

| Bank | Offset | Glyphs | Contents |
|------|--------|-------:|----------|
| S0 | 0x001C | 108 | symbols / punctuation |
| S1 | 0x0D9C | 162 | full-width ASCII (0–78) + hiragana (79–161) |
| S2 | 0x21DC | 150 | katakana + Greek |
| S3 | 0x349C | 81 | Cyrillic |
| S4 | 0x3EBC | 4418 | kanji (complete 47 ku × 94 ten grid) |
| S5 | 0x266FC | 1978 | kanji level-2 |

- **Row byte-swap:** within a row, `byte[r*2]` = RIGHT 8 px, `byte[r*2+1]` = LEFT 8 px;
  render `word = (byte[r*2+1] << 8) | byte[r*2]`.
- **Kanji slot math:** `S4 slot = (ku-16)*94 + (ten-1)`; `S5 slot = (ku-63)*94 + (ten-1)`.
- **Spare pool:** the game displays only ~825 of 6,396 kanji, so ~5,571 kanji slots are
  free to repurpose. Kana/Greek/Cyrillic slots are **NOT** safe (Japanese UI still uses them).

### Route B — half-width letter-pair packing
Compose **two 8-pixel letters into one 16×16 cell** (left half = char A, right half = char B,
honouring the byte-swap), store that composed glyph in an unused kanji slot, and emit that
kanji's code in the text. The engine still draws "one kanji per cell" — but the cell now shows
two letters. Effects:
- **Doubles capacity:** 14 cells/line → 28 half-width letters/line.
- **Halves byte count**, which dissolves the buffer crash (below) for names/labels.
- **No CPU/renderer patch** — only FONT glyphs and SCEN text change.

Half-width glyphs are rendered from `MxPlus_ToshibaSat_8x16.ttf` via **freetype-py** (PIL
can't open this sfnt). Pair glyph row: `FONT[base+r*2] = right_row`, `FONT[base+r*2+1] =
left_row`. A `"  "` cell reuses the existing full-width space `0x8140` to save a slot.

### The buffer crash (historical constraint)
Names/labels were copied into a fixed ~16-byte buffer; >8 full-width chars overflowed it and
crashed (CPU executes `0x0000`, PC 0606B4D8). Route B halves bytes per letter, so names hold
~16 letters and the crash is gone for dialogue, names, and item names. **Item descriptions**
keep a hard limit of **2 lines × 16 cells (32 bytes), no `{08}`** — wider lines re-introduce
the same overflow (see §5).

---

## 5. What Has Been Translated — and How

### Dialogue — all 20 scenarios (DONE)
- Re-encoded entry 5 of blocks 0–19. English is decoded from the source xlsx, re-wrapped to
  **28 half-width chars/line, ≤3 lines/box**, paginated into `{06}{07}` boxes, and packed two
  letters per cell.
- Six scenarios (3, 4, 8, 9, 14, 20) had mismatched line counts; they were inserted from a
  slot-aligned xlsx (`//BOX//` = page break) by slot number — 423 English slots. One
  intentional Japanese bark (Scenario 3, slot 19, "Ya!") is preserved.

### Prologues — all 20 (DONE)
- Entry 7 per scenario: title localized (including the half-width "SCENARIO-NN" header) and
  body/conditions wrapped to width.

### Names — entry 1 (DONE)
- Character names + unit types, half-width. The half-width packing removes the old 8-char crash.

### Item names — entry 2 slots 0–36 (DONE)
- Translated half-width via the name encoder.

### Item descriptions — entry 2 slots 37–141 (DONE)
- Structure: exactly **3 string-slots per item** for items 0–34 (Knife … Rune Stone); the
  stat line is always the 3rd slot, the middle slot is blank when there's only one description
  line. Items 35–36 are status labels with empty descriptions.
- Each description line is re-wrapped to **≤32 half-width chars (≤16 cells)** to stay inside
  the description buffer — a 33+ char line overran it and crashed (same overflow as names).
  Six over-long items were condensed to fit 2 lines × 32 + a stat line.
- Wording: the three "summoner" items (#9 Iron Dumbell, #19 Odin's Buckler, #33 Gleipnir)
  read "Is it enchanted...?".

### Scenario titles — entry 8 (DONE) + map banner (disabled)
- Titles localized half-width.
- The deployment-map title banner always reads **title slot 0** regardless of scenario (the
  selection lives in LANG1.BIN SH-2 code, which we don't blind-patch). Slot 0 is blanked so
  the banner draws nothing on every scenario (trade-off: Scenario 1's own banner is also
  blank). Slots 1–19 are kept intact.

### Opening quiz — block 20, entry 5 (DONE)
- 75 strings: serious intro (0–4), comedic alternate intro (5–9, **left Japanese** — not in
  the source file), questions + answers (10–73), trailing empties.
- The source xlsx's `<>` markers did **not** line up 1:1 with the game's string slots (66
  message-pieces vs 69 target slots; questions split, answers merged, one answer missing at
  the `<>` level). Solution: a **row-level Japanese-anchored aligner** — each xlsx row's
  Japanese line maps cleanly to one game string, matched as a subsequence of the (decompressed)
  Japanese in the slot. This recovered every slot: 69/69, including Q6's split question,
  "Charisma", the "What is a man" question + its answers, and the "glory and honor" answer.
- **Box rendering (important):** the quiz box is **3 lines** tall, and its renderer **skips
  the first line of every continuation box** — the Japanese fills that slot with a `{05}{08}`
  marker (format + newline). Encoding: box 1 holds up to 3 lines; every box after it begins
  with `{05}{08}` then up to 2 lines. Without that marker the first content line of each
  continuation box is eaten (the original cause of the "skipping" bug).

### Battle tutorial — block 20, entry 6 (DONE)
- 17 messages → strings 0–16 (clean 1:1); string 17 stays empty. Split each `<>`-message into
  pages on `<clsr>`, encode via the normal dialogue path. Unlike the quiz, the tutorial uses
  **plain box breaks** (content immediately after `{06}{07}`, no `{05}` skipped line), matching
  the Japanese — so no continuation marker is needed.

---

## 6. Glyph-Allocation Safety (no world-map regression)

As the pair-glyph count grew (now ~994 cells), it could overwrite real kanji slots used by
other assets. The build's reserved set, computed before any pair glyph is placed, includes:
1. all S4/S5 kanji codes used by SCEN content we keep,
2. **all S4/S5 kanji codes referenced inside LANG1.BIN and 0.BIN** (world-map place names live
   there — collisions here garble the map), and
3. all slots changed by the prior build.

Pair glyphs are assigned only from the remaining free pool. Every build re-verifies
**changed-FONT-slots ∩ externally-referenced-slots = 0**, so the world map and other Japanese
assets are never disturbed.

---

## 7. Build & Validation Pipeline

Active modules (in `/home/claude/lang/`):

| Module | Role |
|--------|------|
| `scen_codec.py` | SCEN.DAT parse/serialize (lossless) |
| `fontlib.py` | glyph read/write, code↔bank-slot, ku-ten↔SJIS |
| `glyphlib.py` | renders 8-px half-width glyphs from the Toshiba TTF (pixel-exact) |
| `encoder.py` | `GlyphAlloc`; `encode_message` (28-wide, 3-line dialogue boxes); `encode_quiz_message` (3/2-line boxes + `{05}{08}` continuation); `encode_name` (single-line names) |
| `prologue.py` | converts entry-7 titles + bodies |
| `itemdesc.py` | parses the item-description xlsx, fits/condenses to 2×32 + stat |
| `quizbattle.py` | row-level quiz aligner + battle-message encoder |
| `classes_en.py` | (disabled) JP→EN class map; see §11 |
| `cdecc.py` | Mode-1 EDC/ECC sector framing |
| `splice.py` | in-place splice of FONT + SCEN into the working `.bin`, re-framing each touched sector |
| `build_hw.py` | master build → writes `SCEN_hw.dat` + `FONT_hw.DAT` |

**Build → ship:**
```
python3 build_hw.py        # SCEN_hw.dat (English) + FONT_hw.DAT (pair glyphs)
python3 splice.py          # overwrite FONT + SCEN sectors in out.bin, recompute EDC/ECC
xdelta3 -e -9 -f -s orig.bin out.bin Langrisser1_EN_dialogue.xdelta
```

**Every build is validated offline:**
- changes are localized to the FONT (LBA 135070, 108 sectors) and SCEN (LBA 136946, 364
  sectors) ranges only;
- EDC/ECC is valid on sampled changed sectors;
- the xdelta reproduces `out.bin` byte-for-byte from `orig.bin`;
- all emitted glyph codes resolve (0 unknowns); the charset covers every source character;
- glyph-collision overlap with external assets = 0;
- `SCEN_hw` ≤ the on-disc SCEN budget; `FONT_hw` = exactly 220,732.

---

## 8. Current Status

| Content | Status |
|---------|--------|
| Dialogue (all 20 scenarios) | **DONE** |
| Prologues (all 20) | **DONE** |
| Names (entry 1) | **DONE** |
| Item names (entry 2, 0–36) | **DONE** |
| Item descriptions (entry 2, 37+) | **DONE** (buffer-safe; 6 condensed; "enchanted" wording) |
| Scenario titles (entry 8) | **DONE**; repeated map banner disabled |
| Opening quiz (block 20 entry 5) | **DONE** (69/69; 3/2-line `{05}{08}` box fix applied) |
| Battle tutorial (block 20 entry 6) | **DONE** (17/18; slot 17 empty) |
| Troop types (entry 0: 歩兵→Soldier, etc.) | **DONE — confirmed in-game** |
| Glyph-collision safety | **enforced every build (overlap = 0)** |
| **In-game class names** | **NOT done — separate custom text system, not graphics (see §9)** |
| "シナリオ N" intro card | not done (separate graphic asset) |
| Quiz comedic intro (5–9) | left Japanese (not in source file) |

---

## 9. The Class-Name Finding (custom text system — not graphics, not SCEN)

The in-game class names (bottom status bar, and the 16×16 class-change / character-status
screens) ARE text, but they belong to a **separate text system** from the dialogue: a custom,
non-SJIS code page feeding custom fonts, each with its own renderer. (An earlier guess that
they were pre-rendered graphics was wrong; so was the idea that they live in SCEN.DAT.)

**Where they live.** Null-terminated strings in **LANG1.BIN** (loaded to HWRAM at
0x06010000): a main pool at file 0x617AC–0x61C2A (basic classes: Fighter, Knight, …, Lord)
continuing into a second region ~0x621A0+ (advanced/boss: Vampire Lord, Demon Lord,
Necromancer, Phoenix, Lushiris…), followed by a **255-entry, 4-byte-BE pointer table at
0x61C2C** (classID → name address, base 0x06010000, with duplicate entries). Confirmed by
HWRAM dumps: these strings load to 0x060717AC and the status bar reads them.

**Two renderers, two custom encodings — the same string drives both:**
- **Bottom status bar (half-width):** byte → (conversion) → tile in a custom half-width font
  in **VDP2 VRAM at 0x20000**. Out-of-range codes don't crash — they just draw wrong glyphs.
  That font has digits, full katakana, a few hiragana, and only a *partial* Latin set
  (a A C D E G I M N O P Q R S T U X Z). It is **missing B F H J K L V W Y and most
  lowercase** — exactly the letters Lord/Fighter/Knight/Hawk/Vampire/Warlock/Bishop need.
  Its disc source is compressed/unidentified (not present as plain bitmap data anywhere).
- **16×16 class-change / status screen:** a different renderer drawing from **FONT.DAT**
  (which has every letter). It maps the class byte through a table/arithmetic and **crashes**
  on out-of-range codes (e.g. ASCII) — observed as a corrupted indirect call (`jsr` to
  ~0x00000002) → MasterSH2 "unknown code" crash. The path was traced statically (char loop
  near LANG1 file 0x1B150; crash trampoline at 0x1B080), but the exact code→FONT.DAT-glyph
  conversion was not fully reversed.

**In-game test that proved it (in-place, same-length "ﾛｰﾄﾞ"→"LORD" patch, no relocation):**
bottom bar changed but rendered wrong glyphs (no crash); the 16×16 screen **crashed**. So
ASCII is meaningless to this system, and the two paths are coupled (same bytes).

**Why English is blocked.** A clean result needs *both*: (1) crack the 16×16 conversion and
patch that renderer to accept letter codes without crashing, and (2) add the missing letters
to the VDP2 half-width font (compressed source must be located first). That is a multi-stage
reverse-engineering + graphics effort and is **deferred** as a known limitation.

**Not the lever:** SCEN.DAT entry 3 is the debug/sound-test **battle-test roster** (class
names with Ｔ/Ｇ/Ｎ/Ｃ faction suffixes). Changing "ファイター" there has zero in-game effect
(verified). It's a useful cross-reference for the class list only.

**Troop types, by contrast, ARE done.** The unit *troop* type (歩兵, 長槍, 騎馬, …) lives in
SCEN entry 0 (standard SJIS → FONT.DAT) and was translated (歩兵→Soldier, etc.) and
**confirmed rendering in-game** ("…のSoldier ユニットで" and the unit box). Different system,
fully editable.

---

## 10. Quick Reference — Key Constants

```
FONT.DAT  : 220,732 B; pointers [0x1C,0xD9C,0x21DC,0x349C,0x3EBC,0x266FC,0x35E3C]
            glyph = 16×16 1bpp = 32 B; row word = (byte1<<8)|byte0  (byte1=LEFT, byte0=RIGHT)
            S1 anchors: slot 0='0', 17='A', 49='a'
SCEN.DAT  : original 659,456 B; 22-entry top table; block i = Scenario i+1; block 20 = global
Disc LBAs : FONT(LI)=135070  SCEN(LI)=136946  LANG1.BIN=202  0.BIN=142
            FONT(LII)=144527  SCEN(LII)=157751 ; track 1 = 167,225 sectors
Kanji map : S4 slot=(ku-16)*94+(ten-1) [ku 16-62]; S5 slot=(ku-63)*94+(ten-1) [ku 63-83]
Spare pool: ~5,571 unused kanji slots safe to repurpose (kana/Greek/Cyrillic are NOT)
Widths    : dialogue 28 half-width/line, ≤3 lines/box
            quiz box 3 lines; continuation boxes start with {05}{08} (blank skipped line)
            item description ≤32 half-width chars/line, ≤2 lines + stat, no {08}
Crash     : >16-byte name/label or >32-byte desc line → exec 0x0000 @ PC 0606B4D8
```

---

## 11. Open Items / Next Steps

The translation of all in-game **text** is complete. Remaining items are optional/deferred:

1. **In-game class names** (deferred — see §9). To pursue: trace the 16×16 renderer live in
   an emulator debugger (breakpoint where it reads the class string at 0x060717AC+) to get
   the code→glyph conversion directly; patch it to accept letter codes without crashing; and
   locate + edit the compressed VDP2 half-width font to add the missing letters
   (B F H J K L V W Y). Multi-stage RE + graphics effort.
2. **"シナリオ N" intro card** — separate hardcoded/graphic asset; not located.
3. Quiz comedic alternate intro (entry-5 strings 5–9) remains Japanese unless a translation
   is supplied (not in the source file).
4. Optionally shorten any quiz answer that wraps to two lines if it looks cramped
   (longest ~33 chars, e.g. "The power to obliterate the enemy").

---

## 12. Apply Instructions (you)

1. Apply `Langrisser1_EN_dialogue.xdelta` to the **clean Japanese `.bin`**.
2. Rename the output to `Langrisser1_EN_test.bin`.
3. Load `Langrisser1_EN_test.cue` in **SSF**, with **PCM OFF**.
