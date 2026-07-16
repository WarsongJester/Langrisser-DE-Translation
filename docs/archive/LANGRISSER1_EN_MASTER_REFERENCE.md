> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> Newest *text* reference (EN_45). Its content is merged into 00_MASTER_REFERENCE.md; class-name/menu status here is out of date (class names are now solved).
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# Langrisser I (Sega Saturn, *Dramatic Edition*) — English Translation
## Master Technical Reference — "What Was Hacked, and How"

This is the authoritative, self-contained record of the Langrisser I fan-translation: the
disc and file formats, the rendering techniques, the build/patch pipeline, what has been
translated, what remains, and the bugs/gotchas discovered along the way. It is written so the
project can be reviewed or reproduced from scratch later.

*Current shipping patch: `Langrisser1_EN_45.xdelta` (against the clean Japanese `.bin`).*
*Build lineage: clean JP → `Langrisser1_EN_43` → `Langrisser1_EN_44` (conditions) → `Langrisser1_EN_45` (conditions + character endings).*

---

## 0. Project at a glance

- **Target:** *Langrisser – Dramatic Edition* (Sega Saturn, Japanese). We translate the
  **Langrisser I** half. The disc also holds Langrisser II data, which is never touched.
- **Workflow:** the user supplies English scripts (xlsx) and **tests builds in SSF (PCM OFF)**,
  reporting via screenshots. All reverse engineering, encoding, font work, disc rebuilding and
  patch generation is done in the toolchain and verified offline (byte/round-trip/render/
  EDC-ECC); in-game effects are flagged pending the user's test. The game is never run on the
  build side.
- **Delivery:** an **xdelta3 patch** against the clean Japanese `.bin`, plus a `.cue`. Apply →
  rename output to `Langrisser1_EN_test.bin` → load `Langrisser1_EN_test.cue` in **SSF, PCM OFF**.
- **Core text technique:** *Route B half-width packing* (§3). No emulator/CPU patch is
  required for text — only FONT glyphs and SCEN text change.

---

## 1. Disc structure

The image is a raw `.bin` (+`.cue`). Track 1 is the data track; the rest are the MODE2 track
and audio.

| Track | Mode | Start LBA (clean JP) | Notes |
|------:|------|----------------------|-------|
| 1 | MODE1/2352 | 0 | ISO9660 filesystem (all game files) |
| 2 | MODE2/2352 | 167225 | |
| 3 | AUDIO | 235745 | |
| 4 | AUDIO | 240000 | |
| 5 | AUDIO | 247258 | |
| 6 | AUDIO | 278563 | |

- Clean JP image = **279,163** sectors. The current English build is **+42** sectors (a prior
  build grew SCEN and shifted later files), so tracks 2–6 are offset by **+42** in the build's
  `.cue` (MSF = `lba+150` → `MM:SS:FF`, 75 frames/s).
- **Sector framing (MODE1/2352, 2352 bytes):**
  `sync[12] · header[4] · user[2048] · EDC[4] · zero[8] · ECC_P[172] · ECC_Q[104]`.
  Sector *N*'s user data is at file offset `N*2352 + 16`, length 2048.

### 1.1 Track-1 file layout (around the files we edit, from the build's ISO directory)

| File | LBA | Size (bytes) | Sectors | Role |
|------|-----|--------------|---------|------|
| IMG.DAT | 134794 | 514,624 | 252 | compressed graphics (in-battle UI art) |
| FONT.DAT (LI) | 135070 | 220,732 | 108 | **glyph banks — edited** |
| FACE.DAT | 135182 | 3,612,672 | 1764 | portraits |
| **SCEN.DAT (LI)** | 136946 | **745,472 allocated** | **364** | **script/text — edited** |
| SE_BIN.PAC | 137310 | 868,352 | 424 | |
| LANG1.BIN | 202 | 413,460 | — | LI program/overlay; loads verbatim to `0x06010000` |
| 0.BIN | 142 | 121,852 | — | LI data |
| FONT.DAT (LII) | 144527 | 220,732 | — | untouched |
| SCEN.DAT (LII) | 157751 | 4,517,888 | — | untouched |

> **Critical fact (enables in-place splicing):** SCEN.DAT's ISO directory **reserves 364
> sectors (745,472 bytes)** but the live content is far less (333 sectors in EN_43, 354 in
> EN_44). The unused tail (≈31 sectors) is **slack**, so SCEN can grow up to 364 sectors
> **without shifting any later file or editing the ISO9660 directory / PVD**. FONT.DAT sits
> *before* SCEN and never changes size, so it is always spliced in place.

---

## 2. SCEN.DAT — the script container (fully reverse-engineered)

Big-endian, three-level pointer structure. Round-trip `parse → serialize` is **byte-exact
lossless**, validated on both the clean JP file and the English build.

```
SCEN.DAT
├─ Top table : 512 × u32 (padded). The nonzero entries = 21 block ABSOLUTE offsets + EOF.
│             block i begins Scenario i+1; block 20 = global block (opening quiz, tutorial).
│             blocks are padded to a 0x800 boundary.
└─ Block
   ├─ Section pointer table : M × u32 RELATIVE offsets (M = first_ptr / 4)
   └─ Section data
      └─ Section 2 = string table:
         ├─ count × u32 offsets (relative to section-2 start; count = u32(sec2)/4)
         └─ string data — exposed as "entries", each a {00}-separated SJIS blob
```

Most blocks expose **10 entries**; block 17 has 11, block 20 has 8.

| Entry | Contents | Scope |
|------:|----------|-------|
| 0 | UI / menu (incl. **all magic & summon names, save/load dialogs, battle messages**) | global |
| 1 | names (characters + some unit types) | global |
| 2 | items (names 0–36, descriptions 37+) | global |
| 3 | debug / sound-test menu | global |
| 4 | **places + condition dictionary phrases** | global |
| 5 | dialogue (per scenario); opening quiz in block 20 | per-block |
| 6 | **win/lose conditions** (per scenario); battle tutorial in block 20 | per-block |
| 7 | title + prologue | per-scenario |
| 8 | scenario titles | global |
| 9 | empty in all blocks **except block 17 = the 50 character endings/epilogues** | per-block |

**Global entries (0,1,2,3,4,8)** are duplicated identically in every block — a change must be
written to **all 21 blocks**. Codec edits only section-2 strings; pointer tables and 0x800
block padding are regenerated on serialize.

### 2.1 Control codes (inside strings)

| Code | Meaning |
|------|---------|
| `{06}{07}` | box advance / page break |
| `{08}` | newline within a box |
| `{05}` | format / indent marker |
| `{05}{05}` | line continuation (e.g. 2-line conditions) |
| `{02}` | lord-name insert (the player lord, usually Ledin) — **carries a trailing space** |
| `{09}{XX}` | name insert |
| `{04}{XX}` | **dictionary word** (see below) |

### 2.2 The `{04}{XX}` dictionary (important — discovered during the conditions pass)

`{04}{XX}` expands at render time to a phrase stored as an entry-4 substring; the mapping is
**`{04}{XX} → entry4[XX-1]`** (verified). The renderer expands the code, then draws the
resulting SJIS through the normal FONT path — so **translating the entry-4 substring localizes
the code's output**. Confirmed condition codes:

| Code | entry4 index | Japanese | English (EN_44) |
|------|-------------:|----------|-----------------|
| `{04}{1C}` | 27 | `＊勝利条件` | `＊Victory Conditions` |
| `{04}{1D}` | 28 | `＊敗北条件` | `＊Defeat Conditions` |
| `{04}{0D}` | 12 | `・敵の全滅` | `・Destroy all foes` |
| (also) | 1 | `・ターンオーバー` | `・Time runs out` |

Other known dictionary codes (not condition-related): `{04}{83}` ≈ opening 「,
`{04}{01}`+digit+`{04}{83}` = SCENARIO-NN.

> **Why the conditions panel needed two edits:** each scenario's win/lose panel is assembled
> from **entry 6** (the scenario-specific lines, e.g. "Defeat Lord Zaldaff") **plus** entry-4
> dictionary phrases (the `＊Victory/＊Defeat` headers and "Destroy all foes"). EN_43 had
> translated neither for the panel; EN_44 does both.

---

## 3. FONT.DAT and Route B half-width packing

FONT.DAT = 220,732 bytes: **7 big-endian u32 pointers**, then **6 glyph banks**. Every glyph
is **16×16, 1 bit/pixel = 32 bytes** (16 rows × 2 bytes).

Header pointers: `[0x1C, 0xD9C, 0x21DC, 0x349C, 0x3EBC, 0x266FC, 0x35E3C]`.

| Bank | Offset | Glyphs | Contents | JIS ku |
|------|--------|-------:|----------|--------|
| S0 | 0x001C | 108 | symbols / punctuation | 1–2 |
| S1 | 0x0D9C | 162 | full-width ASCII (slots 0–78) + hiragana (79–161) | 3–4 |
| S2 | 0x21DC | 150 | katakana + Greek | 5–6 |
| S3 | 0x349C | 81 | Cyrillic | 7 |
| S4 | 0x3EBC | 4418 | kanji level-1 (complete 47 ku × 94 ten grid) | 16–62 |
| S5 | 0x266FC | 1978 | kanji level-2 | 63–83 |

- **Row byte-swap (essential):** within a row, `byte[r*2]` = **RIGHT** 8 px, `byte[r*2+1]` =
  **LEFT** 8 px. Render `word = (byte[r*2+1] << 8) | byte[r*2]`.
- **S1 anchors:** slot 0 = `0`, 17 = `A`, 49 = `a`.
- **Kanji slot ↔ SJIS:** `S4 slot = (ku-16)*94 + (ten-1)` (ku 16–62);
  `S5 slot = (ku-63)*94 + (ten-1)` (ku 63–83). SJIS↔(ku,ten) round-trips exactly.

### 3.1 Route B — two half-width letters per cell

The native renderer always draws **one double-byte code = one 16×16 cell**. Route B composes
**two 8-pixel half-width letters into one cell** and stores that glyph in an otherwise-unused
kanji slot; the text then emits that kanji's SJIS code. Effects: doubles letters-per-line
(14 cells → ~28 chars) and halves bytes per letter (which dissolved an older 8-char buffer
crash). **No CPU/renderer patch** — only FONT glyphs + SCEN text change.

Compose (honouring the byte-swap), with `gA`/`gB` = left/right char row bytes (MSB = leftmost):

```
for r in 0..15:
    FONT[base + r*2]     = gB[r]   # right half
    FONT[base + r*2 + 1] = gA[r]   # left half
```

A `"  "` (two-space) cell reuses the existing full-width space `0x8140` to save a slot.

### 3.2 Glyph source & exactness

Half-width glyphs are rendered from **`MxPlus_ToshibaSat_8x16.ttf`** via **freetype-py**
(`FT_LOAD_TARGET_MONO`) at **ascent = 13**. This reproduces the build's stored pair-glyphs
**byte-for-byte** (validated by OCR: e.g. the "Yes" cell = left `Y` + right `e` matches). PIL
cannot open this sfnt; freetype-py reads its embedded 8×16 bitmap strike.

### 3.3 Slot allocation & safety (re-derived this session)

- The font is a **full JIS kanji set**; only **43 slots are truly blank** (all-zero). The
  existing English build repurposed **1,376 real kanji slots** — i.e. it relies on the game
  never *displaying* those particular kanji.
- Reconstructing the build's allocation: diff `FONT_en` vs the JP `FONT.DAT` → changed slots;
  **OCR each changed slot** (match its two 8-px halves to rendered Toshiba glyphs) → recovered
  **996 distinct letter-pairs → code** mappings (a handful are non-letter/dakuten rebuild
  glyphs and don't OCR).
- **Adding new glyphs safely:** reuse an existing pair's code when the pair already exists;
  otherwise allocate from the **43 blank slots** (repurposing a blank glyph can harm nothing).
  The conditions pass needed only **4 new glyphs** (`16`, `md`, `Cs`, `oz`), placed in blank
  slots 2965–2968.
- Builds also verify that changed FONT slots don't intersect kanji codes referenced by
  remaining Japanese (SCEN entries, LANG1.BIN, 0.BIN), so the world map and other Japanese
  assets are never disturbed.

---

## 4. CD-ROM Mode 1 EDC/ECC (`cdecc.py`) — and a real bug found

When SCEN/FONT sectors are rewritten, each touched sector must be re-framed: correct sync,
header (MSF from LBA), **EDC**, and **ECC P/Q**.

- **EDC:** CRC-32 over bytes `0x000–0x80F` (sync+header+user), reflected polynomial
  `0xD8018001`, stored little-endian at `0x810`.
- **ECC (ECMA-130):** GF(2⁸), primitive `0x11D`.
  - P: `block(src=sector+0x0C, major=86, minor=24, major_mult=2, minor_inc=86) → 0x81C` (172 B)
  - Q: `block(src=sector+0x0C, major=52, minor=43, major_mult=86, minor_inc=88) → 0x8C8` (104 B)
- **Header MSF:** `total = lba + 150`; `min/sec/frame` in BCD; mode byte `0x01`.

> **Bug discovered & fixed:** ECC-Q must be computed over the sector **after** P has been
> written, because Q's input range includes the P parity bytes. A first implementation took a
> *snapshot* of `sector+0x0C` once and computed both P and Q from it, so Q used stale P. This
> passed validation against already-correct sectors (idempotent) and against FONT sectors whose
> data was unchanged, but produced wrong Q on rewritten SCEN sectors. The validation method —
> *re-frame a stored sector and require it to equal itself* — caught it. Fix: re-slice
> `sector+0x0C` for Q after writing P. Now reframes original disc sectors **byte-identical**.

---

## 5. The build / patch pipeline

Modules (in `/home/claude/lang/`, the ephemeral sandbox; mirrored to `/mnt/user-data/outputs/`):

| Module | Role |
|--------|------|
| `scen_codec.py` | SCEN.DAT parse/serialize (lossless). `parse`, `parse_section2`, `build_section2`, `build_block`, `serialize(pad=0x800)`. |
| `routeb.py` | Route B: `glyph8` (Toshiba 8-px, ascent 13), `compose_pair`, `ocr_cell`, `kuten_to_sjis`, `slot_to_sjis`, `sjis_to_slot`, `slot_base`. |
| `cdecc.py` | Mode-1 `reframe(sector2352, lba)` → correct sync/header/EDC/ECC. |
| `build_conditions.py` | Reconstructs the build's pair allocation; `TR` (entry-6 per-scenario conditions) + `E4TR` (entry-4 dictionary phrases); Route B encoder reusing existing pairs / allocating blank slots. |
| `assemble.py` | Applies translations to all blocks, serializes SCEN, writes new glyphs to FONT, **splices both in place** (reframing each sector), checks no regression to other entries, asserts SCEN ≤ 364 sectors and output size unchanged. |

**Reproduce the current patch (`EN_44`):**
```
# inputs: clean JP .bin, the previous build patch, the Toshiba TTF
xdelta3 -d -s <CLEAN_JP.bin> Langrisser1_EN_43.xdelta Langrisser1_EN_43.bin   # base build
# extract FONT_en.DAT (LBA 135070,108 sect) and SCEN_en.DAT (LBA 136946) from the base build
python3 assemble.py            # → Langrisser1_EN_44.bin (FONT+SCEN spliced, reframed)
xdelta3 -e -9 -f -s <CLEAN_JP.bin> Langrisser1_EN_44.bin Langrisser1_EN_44.xdelta
# verify:
xdelta3 -d -s <CLEAN_JP.bin> Langrisser1_EN_44.xdelta /tmp/v.bin && cmp Langrisser1_EN_44.bin /tmp/v.bin
```

**Every build is validated:** SCEN round-trips byte-exact except the intended entries; no
regression in untouched entries (all blocks); EDC/ECC valid on every spliced sector; the
xdelta reproduces the build byte-for-byte; all emitted glyph codes resolve; new-glyph slots are
blank; changes are confined to the FONT (LBA 135070–135177) and SCEN (136946–…) ranges only.

---

## 6. Translation status

| Content | Where | Status |
|---------|-------|--------|
| Dialogue (all 20 scenarios) | entry 5 | **Done** (Route B, 28-wide, ≤3-line boxes) |
| Prologues (all 20) | entry 7 | **Done** |
| Names | entry 1 | **Done** |
| Item names + descriptions | entry 2 | **Done** (desc buffer-safe) |
| Scenario titles | entry 8 | **Done** (repeated map banner disabled) |
| Troop types (Soldier, etc.) | entry 0 | **Done — confirmed in-game** |
| In-battle UI: save/load dialogs, **all magic & summon names**, battle messages | entry 0 | **Done** (was already in EN_43) |
| Opening quiz / battle tutorial | block 20 entries 5/6 | **Done** |
| **In-battle Victory/Defeat conditions** | entry 6 (+ entry-4 dictionary phrases) | **Done — EN_44, in-game tested** |
| **Character endings / epilogues** (50 epilogues) | **block 17, entry 9** | **Done — EN_45** (re-wrapped 28×3, paginated) |
| **Entry-4 place names** (Twin Castle, Raigard Empire, Holy Rod, Dark Rod, Velzeria, Langrisser, …) | entry 4 | **NOT done — next task** |
| In-battle **command menu** (Move/Attack/Magic/Cure/Command) | custom VDP1/renderer | **Deferred** (not SJIS; custom render) |
| In-battle **class names** | LANG1.BIN custom code-page + custom fonts | **Deferred** (multi-stage RE + missing-glyph problem) |
| "シナリオ N" intro card | hardcoded/graphic asset | Not located |
| Entry-3 debug/sound-test menu | entry 3 | Skipped (normally inaccessible) |

### 6.1 Conditions detail (EN_44)
49 entry-6 lines across 21 scenarios + the entry-4 dictionary phrases. Universal defeat is
"・<lord> dies" (the `{02}` insert provides the name + its trailing space → single space).
Scenario objectives match entry-1 name spellings. Note: **S13 `全指揮官石化` is a *lose*
condition** → "All allies petrified".

---

## 7. Deferred work — pointers for later

- **Command menu** (Move/Attack/Magic/Cure/Command): not SJIS, not a VDP2 pre-rendered strip.
  The VDP1 command list at battle holds unit sprites/portraits, not the menu text — the words
  come from the custom in-battle renderer (likely a VDP2 tilemap of the kanji font or the
  same custom code-page/font path as class names). See `INBATTLE_UI_RESEARCH.md` (IMG.DAT
  streaming-Huffman/LZ codec, load path, VDP analysis).
- **Class names** (status bar + class-change/status screens): null-terminated strings in
  LANG1.BIN (pool ~`0x617AC`+, 255-entry BE pointer table at `0x61C2C`), driven through a
  *custom non-SJIS code page* into two separate renderers — a half-width VDP2 font at VRAM
  `0x20000` (missing B F H J K L V W Y + most lowercase; compressed source unidentified) and a
  16×16 renderer off FONT.DAT that **crashes** on out-of-range codes. Needs live-debugger RE
  of the 16×16 conversion plus adding the missing half-width glyphs.
- **In-battle menu chrome — command ring, option-menu list items, and the Game Settings
  submenu** (`ゲーム設定/表示設定/戦闘シーン/PCM/高速戦闘`, options `高速/通常/ON/OFF`):
  same custom-render family. **None of these strings exist as Shift-JIS anywhere on the disc**
  (verified by exhaustive search of every file and the raw image; only an incidental `セーブ`
  appears in LANG1). They are drawn as a **VDP2 tilemap** using the custom bottom-bar font
  (IMG.DAT asset 0, which has only a partial Latin set — `A T D F M P V H` + digits + katakana)
  plus a kanji font. The "ON/OFF" in the settings screen are tiles from that same partial-Latin
  font. Translating requires (a) locating the custom tile-index source for each label, (b)
  extending the custom font with the missing Latin letters, and likely (c) the IMG.DAT codec —
  whose async Huffman-LZ **back-end decoder is still unlocated** (see `INBATTLE_UI_RESEARCH.md`),
  so the font asset can't yet be decompressed/re-encoded from the static disc. **Blocked from a
  static-patch approach;** the practical next step is a Mednafen VDP2-VRAM (+HWRAM) dump captured
  with the Game Settings menu open, to inspect the live tilemap/font and assess a font-extension
  or runtime-VRAM-patch path.

---

## 8. Quick-reference constants

```
Disc      : MODE1/2352 track1 LBA 0–167224; T2 MODE2@167225; audio @235745/240000/247258/278563
            JP=279163 sect; current build +42 sect. user data = sector*2352+16 (2048 B).
SCEN.DAT  : LBA 136946; ISO allocation 745,472 B = 364 sect (content uses fewer → splice slack).
            top table 512×u32 (21 block offsets + EOF); block i = Scenario i+1; block 20 global.
            section 2 = string table; entries 0–9 (see §2). dictionary {04}{XX} → entry4[XX-1].
FONT.DAT  : LBA 135070; 220,732 B; ptrs [0x1C,0xD9C,0x21DC,0x349C,0x3EBC,0x266FC,0x35E3C].
            glyph 16×16 1bpp = 32 B; row word=(byte1<<8)|byte0 (byte1=LEFT, byte0=RIGHT).
            S1 anchors slot0='0',17='A',49='a'. kanji: S4 slot=(ku-16)*94+(ten-1) [16-62],
            S5 slot=(ku-63)*94+(ten-1) [63-83]. Only 43 blank slots; build repurposed 1376.
RouteB    : 2 half-width letters/cell; FONT[base+r*2]=right, [+r*2+1]=left; emit kanji SJIS.
            Toshiba TTF via freetype-py, ascent=13 (byte-exact to build).
Mode1 ECC : EDC CRC32 poly(refl) 0xD8018001 over 0x000-0x80F @0x810 LE.
            ECC GF(2^8) prim 0x11D; P(86,24,2,86)@0x81C; Q(52,43,86,88)@0x8C8 — Q AFTER P.
LANG1.BIN : LBA 202; loads verbatim to 0x06010000 (file off = addr-0x06010000).
```
