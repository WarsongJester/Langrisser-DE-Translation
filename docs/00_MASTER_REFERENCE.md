# Langrisser I (Sega Saturn, *Dramatic Edition*) — English Translation
## Master Technical Reference

**This is the single source of truth.** It supersedes every file in `docs/archive/`. It covers
the disc/file formats, the rendering techniques, the build/patch pipeline, what has been
translated, and what remains. The in-battle UI work (class names, menu chrome, the IMG.DAT
codec) has its own detailed docs under `docs/in_battle_ui/`; this file links to them and
summarizes their status.

- **Current story patch:** `patches/Langrisser1_EN_45.xdelta` (apply to the **clean Japanese `.bin`**).
- **Current class-name patch:** `patches/Langrisser1_inject_AZ.xdelta` (built on clean JP, LBA 202 — see the merge note in §7).
- **Build lineage (story):** clean JP → `EN_43` → `EN_44` (in-battle conditions) → `EN_45` (conditions + character endings).

---

## 0. Project at a glance

- **Target.** *Langrisser – Dramatic Edition* (Sega Saturn, Japanese). We translate the
  **Langrisser I** half. The disc also holds Langrisser II data, which is never touched.
- **Division of labour.** Tim supplies English scripts (xlsx) and **tests builds in SSF
  (PCM OFF)**, reporting via screenshots and (for RE) Mednafen/Kronos debugger dumps. All
  reverse engineering, encoding, font work, disc rebuilding, and patch generation happen in
  the offline toolchain. The game is never run on the build side — every result is verified
  offline (byte/round-trip/render/EDC-ECC) and in-game effects are flagged pending Tim's test.
- **Delivery.** An **xdelta3 patch** against the clean Japanese `.bin`, plus a `.cue`. Apply →
  rename output to `Langrisser1_EN_test.bin` → load `Langrisser1_EN_test.cue` in **SSF, PCM OFF**.
- **Core text technique.** *Route B half-width packing* (§3.1). No CPU/renderer patch is
  required for text — only FONT glyphs and SCEN text change. (Class-name work *does* patch
  LANG1 code; that's a separate subsystem — see `docs/in_battle_ui/CLASS_NAMES.md`.)

---

## 1. Disc structure

The image is a raw `.bin` (+`.cue`). Track 1 is the data track (an ISO9660 filesystem); the
rest are the MODE2 track and audio.

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

### 1.1 Track-1 file layout (files we touch)

| File | LBA | Size (bytes) | Sectors | Role |
|------|-----|--------------|---------|------|
| IMG.DAT | 134794 | 514,624 | 252 | compressed graphics + the custom in-battle UI font (see `docs/in_battle_ui/IMG_DAT_CODEC.md`) |
| FONT.DAT (LI) | 135070 | 220,732 | 108 | **glyph banks — edited** (Route B) |
| FACE.DAT | 135182 | 3,612,672 | 1764 | portraits |
| **SCEN.DAT (LI)** | 136946 | **745,472 allocated** | **364** | **script/text — edited** |
| SE_BIN.PAC | 137310 | 868,352 | 424 | |
| LANG1.BIN | 202 | 413,460 | — | LI program/overlay; **loads verbatim** to CPU `0x06010000` |
| 0.BIN | 142 | 121,852 | — | LI data |
| FONT.DAT (LII) | 144527 | 220,732 | — | untouched |
| SCEN.DAT (LII) | 157751 | 4,517,888 | — | untouched |

> **Splice-in-place enabler:** SCEN.DAT's ISO directory **reserves 364 sectors (745,472 B)**
> but the live content is smaller (EN_43 = 333, EN_44 = 354, EN_45 = 355 sectors). The unused
> tail is **slack**, so SCEN can grow up to 364 sectors **without shifting any later file or
> editing the ISO9660 directory / PVD**. FONT.DAT sits *before* SCEN and never changes size, so
> it is always spliced in place. This is why current builds keep disc geometry identical and the
> `.cue` unchanged — the old "grow + shift + patch PVD" path (in `docs/archive/HACKING_HANDOFF.md`)
> is no longer needed.

> **LANG1.BIN loads verbatim.** Confirmed across the whole code region in both title-load and
> in-battle HWRAM dumps: the RAM image is byte-identical to the disc file (`file_off = CPU −
> 0x06010000`). **Code *and* data patches to LANG1 are reliable** — there is **no relocation**.
> (Earlier notes feared pointer-literal relocation; that was disproven. This is the key enabler
> for the class-name code-hook solution.)

---

## 2. SCEN.DAT — the script container (fully reverse-engineered)

Big-endian, three-level pointer structure. Round-trip `parse → serialize` is **byte-exact
lossless**, validated on the clean JP file and every English build. Full spec:
`docs/format_specs/SCEN_DAT_FORMAT.md`. Codec: `tools/scen_codec.py`.

```
SCEN.DAT
├─ Top table : 512 × u32 (padded). Nonzero entries = 21 block ABSOLUTE offsets + EOF.
│             block i begins Scenario i+1; block 20 = global block (opening quiz, tutorial).
│             blocks are padded to a 0x800 boundary.
└─ Block
   ├─ Section pointer table : M × u32 RELATIVE offsets (M = first_ptr / 4)
   └─ Section data
      └─ Section 2 = string table:
         ├─ count × u32 offsets (relative to section-2 start; count = u32(sec2)/4)
         └─ string data — exposed as "entries", each a {00}-separated SJIS blob
```

Most blocks expose **10 entries**; block 17 has **11**, block 20 has **8**.

| Entry | Contents | Scope |
|------:|----------|-------|
| 0 | UI / menu — incl. **all magic & summon names, save/load dialogs, battle messages** | global |
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
written to **all 21 blocks**. The codec edits only section-2 strings; pointer tables and 0x800
block padding are regenerated on serialize.

### 2.1 Control codes (inside strings)

| Code | Meaning |
|------|---------|
| `{06}{07}` | box advance / page break |
| `{08}` | newline within a box |
| `{05}` | format / indent marker |
| `{05}{05}` | line continuation (e.g. 2-line conditions) |
| `{02}` | lord-name insert (player lord, usually Ledin) — **carries a trailing space** |
| `{09}{XX}` | name insert |
| `{04}{XX}` | **dictionary word** (see §2.2) |
| `{03}` | prologue title setup |

### 2.2 The `{04}{XX}` dictionary

`{04}{XX}` expands at render time to a phrase stored as an **entry-4 substring**:
**`{04}{XX} → entry4[XX-1]`** (verified). The renderer expands the code, then draws the result
through the normal FONT path — so **translating the entry-4 substring localizes the code's
output**. Confirmed condition codes:

| Code | entry4 idx | Japanese | English (EN_44) |
|------|-----------:|----------|-----------------|
| `{04}{1C}` | 27 | `＊勝利条件` | `＊Victory Conditions` |
| `{04}{1D}` | 28 | `＊敗北条件` | `＊Defeat Conditions` |
| `{04}{0D}` | 12 | `・敵の全滅` | `・Destroy all foes` |
| (turn-limit) | 1 | `・ターンオーバー` | `・Time runs out` |

Other known codes: `{04}{83}` ≈ opening 「; `{04}{01}`+digit+`{04}{83}` = "SCENARIO-NN".

> Each scenario's win/lose panel is assembled from **entry 6** (scenario-specific lines) **plus**
> entry-4 dictionary phrases (the `＊Victory/＊Defeat` headers and "Destroy all foes"). Both must
> be translated for the panel to be fully English (this is what EN_44 fixed).

---

## 3. FONT.DAT and Route B half-width packing

FONT.DAT = 220,732 bytes: **7 big-endian u32 pointers**, then **6 glyph banks**. Every glyph is
**16×16, 1 bit/pixel = 32 bytes** (16 rows × 2 bytes). Full spec:
`docs/format_specs/FONT_DAT_FORMAT.md`. Helpers: `tools/routeb.py`.

Header pointers: `[0x1C, 0xD9C, 0x21DC, 0x349C, 0x3EBC, 0x266FC, 0x35E3C]`.

| Bank | Offset | Glyphs | Contents | JIS ku |
|------|--------|-------:|----------|--------|
| S0 | 0x001C | 108 | symbols / punctuation | 1–2 |
| S1 | 0x0D9C | 162 | full-width ASCII (slots 0–78) + hiragana (79–161) | 3–4 |
| S2 | 0x21DC | 150 | katakana + Greek | 5–6 |
| S3 | 0x349C | 81 | Cyrillic | 7 |
| S4 | 0x3EBC | 4418 | kanji level-1 (complete 47 ku × 94 ten grid) | 16–62 |
| S5 | 0x266FC | 1978 | kanji level-2 | 63–83 |

- **Row byte-swap (essential):** `byte[r*2]` = **RIGHT** 8 px, `byte[r*2+1]` = **LEFT** 8 px.
  Render `word = (byte[r*2+1] << 8) | byte[r*2]`.
- **S1 anchors:** slot 0 = `0`, 17 = `A`, 49 = `a`.
- **Kanji slot ↔ SJIS:** `S4 slot = (ku-16)*94 + (ten-1)` (ku 16–62);
  `S5 slot = (ku-63)*94 + (ten-1)` (ku 63–83). SJIS ↔ (ku,ten) round-trips exactly.

### 3.1 Route B — two half-width letters per cell

The native renderer always draws **one double-byte code = one 16×16 cell**. Route B composes
**two 8-pixel half-width letters into one cell** and stores that glyph in an otherwise-unused
kanji slot; the text emits that kanji's SJIS code. Effects: doubles letters-per-line
(14 cells → ~28 chars) and halves bytes per letter (which dissolved the old ~8-char buffer
crash). **No CPU/renderer patch** — only FONT glyphs + SCEN text change.

Compose (honouring the byte-swap; `gA`/`gB` = left/right char row bytes, MSB = leftmost):
```
for r in 0..15:
    FONT[base + r*2]     = gB[r]   # right half
    FONT[base + r*2 + 1] = gA[r]   # left half
```
A `"  "` (two-space) cell reuses the existing full-width space `0x8140` to save a slot.

### 3.2 Glyph source & exactness

Half-width glyphs are rendered from **`MxPlus_ToshibaSat_8x16.ttf`** via **freetype-py**
(`FT_LOAD_TARGET_MONO`) at **ascent = 13**. This reproduces the build's stored pair-glyphs
**byte-for-byte** (validated by OCR — e.g. the "Yes" cell = left `Y` + right `e`). PIL cannot
open this sfnt; freetype-py reads its embedded 8×16 bitmap strike. **This TTF must be
re-uploaded after a sandbox reset** to rebuild FONT.

### 3.3 Slot allocation & safety

- The font is a full JIS kanji set; only **43 slots are truly blank** (all-zero). The English
  build repurposes **~1,376 real kanji slots** — i.e. it relies on the game never *displaying*
  those particular kanji.
- The build reconstructs its allocation by diffing `FONT_en` vs JP FONT.DAT → changed slots,
  then OCR-ing each changed slot to recover **~996 distinct letter-pair → code** mappings.
- **Adding new glyphs safely:** reuse an existing pair's code if the pair already exists;
  otherwise allocate from the **43 blank slots**. (The conditions pass needed only 4 new glyphs;
  endings needed 6 more — all placed in blank slots.)
- Every build verifies **changed FONT slots ∩ kanji codes referenced by remaining Japanese
  (SCEN, LANG1.BIN, 0.BIN) = 0**, so the world map and other Japanese assets are never disturbed.

---

## 4. CD-ROM Mode-1 EDC/ECC (`tools/cdecc.py`)

When SCEN/FONT/LANG1 sectors are rewritten, each touched sector is re-framed: correct sync,
header (MSF from LBA), **EDC**, and **ECC P/Q**.

- **EDC:** CRC-32 over bytes `0x000–0x80F`, reflected polynomial `0xD8018001`, stored
  little-endian at `0x810`.
- **ECC (ECMA-130):** GF(2⁸), primitive `0x11D`.
  - P: `block(src=sector+0x0C, major=86, minor=24, major_mult=2, minor_inc=86) → 0x81C` (172 B)
  - Q: `block(src=sector+0x0C, major=52, minor=43, major_mult=86, minor_inc=88) → 0x8C8` (104 B)
- **Header MSF:** `total = lba + 150`; min/sec/frame in BCD; mode byte `0x01`.

> **Bug found & fixed (keep in mind if reimplementing):** ECC-Q must be computed **after** P is
> written, because Q's input range includes the P parity bytes. A first version snapshotted
> `sector+0x0C` once and computed both from it, so Q used stale P. It passed validation on
> already-correct/unchanged sectors but produced wrong Q on *rewritten* SCEN sectors. The
> validation method — re-frame a stored sector and require it to equal itself — caught it.
> Fix: re-slice `sector+0x0C` for Q after writing P. Reframes original sectors byte-identical.

---

## 5. Build / patch pipeline (story text)

Tools live in `tools/`; the working dir `/home/claude/lang/` is ephemeral (resets between
sessions) and mirrored to `/mnt/user-data/outputs/`. Key modules:

| Module | Role |
|--------|------|
| `scen_codec.py` | SCEN.DAT parse/serialize (lossless). `parse`, `parse_section2`, `build_section2`, `build_block`, `serialize(pad=0x800)`. |
| `routeb.py` | Route B: `glyph8` (Toshiba 8-px, ascent 13), `compose_pair`, `ocr_cell`, `kuten_to_sjis`, `slot_to_sjis`, `sjis_to_slot`, `slot_base`. |
| `cdecc.py` | Mode-1 `reframe(sector2352, lba)` → correct sync/header/EDC/ECC. |
| `build_conditions.py` | Rebuilds the build's pair allocation; `TR` (entry-6 per-scenario conditions) + `E4TR` (entry-4 dictionary phrases); Route B encoder reusing existing pairs / allocating blank slots. |
| `build_endings.py` | Block-17 entry-9 epilogues; re-wrap 28×3 + paginate. |
| `translate_battle.py` | Content-keyed entry-0 translator (UI/menu, magic/summon names, battle messages). |
| `assemble.py` | Applies translations to all blocks, serializes SCEN, writes new glyphs to FONT, **splices both in place** (reframing each sector), checks no regression to other entries, asserts SCEN ≤ 364 sectors and output size unchanged. |
| `sh2dis.py`, `findref.py`, `sh2emu.py` | SH-2 RE helpers (used for the LANG1 class-name/menu work). |

**Reproduce the current story patch (`EN_45`) from the previous build:**
```
# inputs: clean JP .bin, the previous build's patch, MxPlus_ToshibaSat_8x16.ttf
xdelta3 -d -s <CLEAN_JP.bin> patches/Langrisser1_EN_44.xdelta EN_44.bin   # or EN_43 base
# extract FONT_en.DAT (LBA 135070, 108 sect) and SCEN_en.DAT (LBA 136946) from the base build
python3 tools/assemble.py            # → EN_45.bin (FONT+SCEN spliced, reframed)
xdelta3 -e -9 -f -s <CLEAN_JP.bin> EN_45.bin patches/Langrisser1_EN_45.xdelta
# verify:
xdelta3 -d -s <CLEAN_JP.bin> patches/Langrisser1_EN_45.xdelta /tmp/v.bin && cmp EN_45.bin /tmp/v.bin
```

**Every build is validated offline:** SCEN round-trips byte-exact except the intended entries;
no regression in untouched entries (all blocks); EDC/ECC valid on every spliced sector; the
xdelta reproduces the build byte-for-byte; all emitted glyph codes resolve; new-glyph slots
were blank; changes confined to the FONT and SCEN ranges only.

---

## 6. Translation status

| Content | Where | Status |
|---------|-------|--------|
| Dialogue (all 20 scenarios) | entry 5 | **Done** (Route B, 28-wide, ≤3-line boxes) |
| Prologues (all 20) | entry 7 | **Done** |
| Names | entry 1 | **Done** |
| Item names + descriptions | entry 2 | **Done** (desc buffer-safe; 6 condensed; "enchanted" wording) |
| Scenario titles | entry 8 | **Done** (repeated map banner disabled — see note below) |
| Troop types (Soldier, etc.) | entry 0 | **Done — confirmed in-game** |
| In-battle save/load dialogs, **magic & summon names**, battle messages | entry 0 | **Done** |
| Opening quiz / battle tutorial | block 20 entries 5/6 | **Done** |
| **In-battle Victory/Defeat conditions** | entry 6 + entry-4 dictionary | **Done — EN_44, in-game tested** |
| **Character endings / epilogues** (50) | **block 17, entry 9** | **Done — EN_45** (28×3, paginated) |
| **In-game class names** (status bar + 16×16 panel) | LANG1.BIN custom code-page | **DONE — see `docs/in_battle_ui/CLASS_NAMES.md`** (was "deferred" in older docs) |
| **Entry-4 place names** (Twin Castle, Raigard Empire, Holy Rod, Dark Rod, Velzeria, Langrisser…) | entry 4 | **NOT done — next story task** |
| In-battle **command/system menu chrome** (Move/Attack/Magic/Cure, Save/Load/Settings…) | custom VDP2 tilemap + IMG.DAT font | **Deferred — see `docs/in_battle_ui/MENU_CHROME.md`** |
| "シナリオ N" intro card | hardcoded/graphic asset | Not located |
| Entry-3 debug/sound-test menu | entry 3 | Skipped (normally inaccessible) |
| Quiz comedic alt-intro (block 20 entry 5, strings 5–9) | entry 5 | Left Japanese (not in source file) |

**Scenario-title map banner:** the deployment-map title banner always reads title slot 0
regardless of scenario (the selection lives in LANG1 SH-2 code). Slot 0 is blanked so the
banner draws nothing on every scenario; slots 1–19 are kept intact (trade-off: Scenario 1's
own banner is also blank).

**Conditions detail (EN_44):** 49 entry-6 lines across 21 scenarios + the entry-4 dictionary
phrases. Universal defeat = "・<lord> dies" (the `{02}` insert supplies the name + its trailing
space). Note S13 `全指揮官石化` is a *lose* condition → "All allies petrified".

---

## 7. In-battle UI subsystems — pointer to the detailed docs

These are **separate from SCEN/FONT** and have their own references in `docs/in_battle_ui/`:

- **Class names — `docs/in_battle_ui/CLASS_NAMES.md` — DONE.** Both renderers (bottom status
  bar + 16×16 status/class-change panel) display English A–Z, confirmed in-game
  (`patches/Langrisser1_inject_AZ.xdelta`, test strings "HAWK"/"JOY"). Solved with a runtime
  CPU hook in LANG1 (table-driven byte→glyph conversion + injection of the 4 missing bottom-bar
  glyphs J/K/W/Y + white recolor). **Remaining:** insert the real English class names into the
  LANG1 pool, and merge into the full EN build honouring the **+42-sector LANG1 shift** (the
  class work is built at LBA 202 vs clean JP; EN_45 puts LANG1 elsewhere).

- **Menu chrome — `docs/in_battle_ui/MENU_CHROME.md` — DEFERRED.** Command ring
  (移動/攻撃/魔法/治療/指令) and system/settings menus. Drawn as a VDP2 tilemap composed glyph-
  by-glyph from a **custom 8×8 font in VRAM 0x20000** (the bottom-bar font), with the source
  strings in a 1-byte custom code page. The encoding + render pipeline are fully mapped; the
  blockers are (a) most Latin letters are missing from that font and (b) the font is runtime-
  decompressed from IMG.DAT. Path forward = "Route 1" runtime glyph injection into VRAM + string
  rewrite (no codec needed), since LANG1 loads verbatim.

- **IMG.DAT codec — `docs/in_battle_ui/IMG_DAT_CODEC.md` — research notes.** The compressed
  archive that decompresses the custom UI font to VRAM. It's a stateful streaming Huffman-LZ
  (LZH-family), not LZSS; decoder back-end located but not transcribed. Cracking it would unlock
  static font editing, but the runtime-injection route sidesteps it.

---

## 8. Quick-reference constants

```
Disc      : MODE1/2352 track1 LBA 0–167224; T2 MODE2@167225; audio @235745/240000/247258/278563
            JP=279163 sect; current EN build +42 sect. user data = sector*2352+16 (2048 B).
SCEN.DAT  : LBA 136946; ISO allocation 745,472 B = 364 sect (content uses fewer → splice slack).
            top table 512×u32 (21 block offsets + EOF); block i = Scenario i+1; block 20 global.
            section 2 = string table; entries 0–9 (block17 +ending entry). {04}{XX} → entry4[XX-1].
FONT.DAT  : LBA 135070; 220,732 B; ptrs [0x1C,0xD9C,0x21DC,0x349C,0x3EBC,0x266FC,0x35E3C].
            glyph 16×16 1bpp = 32 B; row word=(byte1<<8)|byte0 (byte1=LEFT, byte0=RIGHT).
            S1 anchors slot0='0',17='A',49='a'. kanji S4 (ku-16)*94+(ten-1) [16-62],
            S5 (ku-63)*94+(ten-1) [63-83]. 43 blank slots; build repurposed ~1376.
RouteB    : 2 half-width letters/cell; FONT[base+r*2]=right, [+r*2+1]=left; emit kanji SJIS.
            Toshiba TTF via freetype-py, ascent=13 (byte-exact to build).
Mode1 ECC : EDC CRC32 poly(refl) 0xD8018001 over 0x000-0x80F @0x810 LE.
            ECC GF(2^8) prim 0x11D; P(86,24,2,86)@0x81C; Q(52,43,86,88)@0x8C8 — Q AFTER P.
LANG1.BIN : LBA 202; loads VERBATIM to 0x06010000 (file off = CPU-0x06010000). No relocation.
            class string pool @file 0x617AC; classID→ptr table @0x61C2C; Lord(ﾛｰﾄﾞ)@0x6181C.
IMG.DAT   : LBA 134794; custom UI font = asset 0 → VRAM 0x20000 (8×8 4bpp). Codec = streaming LZH.
Apply     : xdelta3 -d -s <cleanJP.bin> <patch>.xdelta out.bin; rename Langrisser1_EN_test.bin;
            load .cue in SSF, PCM OFF.
```

---

## 9. Open items / next steps

1. **Entry-4 place names** (Twin Castle, Raigard Empire, Holy Rod, Dark Rod, Velzeria,
   Langrisser, …) — the last remaining SCEN-backed Japanese text. Straightforward Route B pass.
2. **Insert real English class names** into the LANG1 pool and **merge the class-name patch into
   the full EN build** (mind the +42-sector LANG1 shift). See `docs/in_battle_ui/CLASS_NAMES.md` §7.
3. **In-battle menu chrome** (optional, cosmetic) — Route 1 runtime glyph injection +
   string rewrite. See `docs/in_battle_ui/MENU_CHROME.md`.
4. **"シナリオ N" intro card** — separate graphic asset, not located.
5. Quiz comedic alt-intro (block 20 entry 5, strings 5–9) — Japanese unless a translation is supplied.
