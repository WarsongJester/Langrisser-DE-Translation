> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> Alternative class-name approach (katakana-slot repaint) + menu. Superseded by the runtime-hook A–Z solution; menu chrome still pending.
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# Langrisser I (Sega Saturn, *Dramatic Edition*) — Class Names & Menu
## Hacking Handoff & Technical Record

This document records the reverse engineering and build work for two pieces of the
Langrisser I English fan-translation: the **in-game class names** (the unit class shown
on status / class-change screens) and the **UI menu**. It is written to stand on its own
for a handoff, and complements the master references
(`LANGRISSER1_EN_HACKING_REFERENCE.md`, `SCEN_DAT_FORMAT.md`, `FONT_DAT_FORMAT.md`).

Workflow context: the script owner supplies English text and tests builds in **SSF**
(PCM off), reporting via screenshots; all reverse engineering, encoding, disc work, and
patch generation is done offline. Delivery is an **xdelta3 patch** against the clean
Japanese `.bin`. The game is never run on the build side — everything is verified offline
(round-trip, EDC/ECC, glyph-collision, render) and confirmed in-game by the tester.

---

## 1. Result / Status

| Item | Status |
|------|--------|
| **Class names — 16×16 status & class-change screen** | **DONE.** All 132 classes render in English (hybrid single-letter + pair-packed half-width). Confirmed fitting after the dakuten rebuild. |
| **Class names — bottom status bar** | **NOT done / deferred.** Separate renderer using a compressed VDP2 font that was not cracked (see §8). The bottom bar still shows katakana for the class. |
| **UI menu** | **DONE & confirmed in-game.** `SCEN_menu.dat` + `FONT_menu.DAT` folded into the shipping patch. Earlier full-width menu crashed (buffer overflow); the half-width (Route B) menu stays under the buffer limit. |
| Character names on the 16×16 screen | Already English from a separate path (the dialogue/menu text renderer, kanji-slot pairs). Not part of this work. |

Current combined deliverable: **`Langrisser1_EN_classes_menu.xdelta`** = the full English
build (dialogue, prologues, items, quiz, troop types) + UI menu + all 132 class names.

---

## 2. The Two Class-Name Renderers

Class names are drawn by **two independent renderers** that both read the *same* source
string but render through completely different glyph systems. This was the central
finding and the reason a single patch can't fix both at once.

### 2.1 Bottom status bar (half-width) — NOT solved
- Reads the class string, converts each byte to a tile in a **custom half-width font held
  in VDP2 VRAM at 0x20000** (4bpp, 8×8 tiles, 32 bytes/tile).
- Byte→tile mapping confirmed: `tile = byte − 0x70` (katakana bytes 0xB1–0xDD →
  tiles 0x41–0x6D), verified against the VDP2 tilemap (~VRAM 0x8C90, 2-byte BE entries)
  and in-game.
- Out-of-range codes do **not** crash here — they just draw wrong glyphs.
- The font itself is **compressed** and was not located on disc/RAM in any plain bitmap
  form. It is asset 0 of a compressed archive loaded to Low Work RAM at 0x00200000; the
  codec is **not standard LZSS** and resisted an exhaustive brute force (see §8).
- Because the font is missing most Latin letters and the codec is uncracked, the bottom
  bar is a **deferred stretch goal**.

### 2.2 16×16 class-change / character-status screen — SOLVED
- A different renderer that draws class glyphs from **FONT.DAT**, which contains every
  letter and is fully editable.
- It reads the class string one byte at a time and maps each byte through a
  table/arithmetic to a **FONT.DAT S2 (katakana) glyph slot**. The same string drives both
  renderers, so the two are coupled at the source level but diverge at glyph lookup.
- Static trace: per-character renderers at file `0x1B150` (mode 1, byte+2) and `0x1B190`
  (mode 4, byte unchanged); both read the class-string pointer var (`0x0609AB38`) and call
  a shared resolver `0x19F4C(mode, code)`. `0x19F4C` resolves a base via `0x06015040(2)`
  then `table[mode] = base + *(base + mode*4)` and scans `(code−1)` null-terminated
  entries — an indexed resolver. The **mode-4 path renders from the katakana bank**.
- The full code→glyph conversion was not reversed line-by-line, but it did not need to be:
  the editable surface (the katakana glyph slots + the class string itself) was enough.

---

## 3. Class-String Data in LANG1.BIN (the editable surface)

LANG1.BIN is the LI program/overlay (disc LBA 202; loads flat to HWRAM at 0x06010000).
Confirmed by HWRAM dumps that the status bar reads these strings at runtime.

| Structure | File offset | Notes |
|-----------|-------------|-------|
| Class-name string pool | **0x617AC – 0x61C24** | 132 null-terminated half-width katakana (JIS X 0201) strings, in class order. e.g. Lord `ﾛｰﾄﾞ` = `DB B0 C4 DE` @ 0x6181C. |
| classID → string pointer table | **0x61C2C** | 255 entries × 4-byte big-endian pointers, base 0x06010000. Duplicate IDs share strings (e.g. several IDs → Lord). Entry 0 points just before the pool (leave as-is). |
| Character-name pool | ~**0x6202C** | e.g. Ledin `ﾚﾃﾞｨﾝ` @ 0x6202C. Not edited in this work. |

**Critical relocation fact:** at load, LANG1 **relocates pointer literals in its code**, so
in-place edits to code pointer literals revert in RAM — code patches are unreliable. But
the **pointer DATA table at 0x61C2C does NOT relocate** (RAM 0x06071C2C == disc bytes,
confirmed), so **repointing the table is safe**. This is why the whole approach repacks the
string pool and rewrites the pointer table, and never patches renderer code.

**ASCII note:** the original class string at index 90 is `47 b1 dd c4` = ASCII `G` (0x47) +
katakana ｱﾝﾄ = "Giant". The original game mixes a literal ASCII byte into a class string,
so ASCII is not universally fatal to these renderers — but a *string of* ASCII codes
(e.g. "LORD" = 4C 4F 52 44) did crash the 16×16 path in an early test (out-of-range index
→ corrupted indirect call → MasterSH2 "unknown code"). The safe, proven approach stays
inside the katakana code range and never relies on ASCII.

---

## 4. The Glyph Mechanism (how English gets onto the screen)

The renderer maps a katakana **byte → S2 katakana glyph slot** in FONT.DAT. The trick is to
overwrite those katakana glyph slots with English glyphs and then re-encode the class
string to point at them.

### 4.1 FONT.DAT glyph cell
- 16×16, 1 bpp = 32 bytes (16 rows × 2 bytes).
- **Row byte order is swapped:** `byte[r*2]` = RIGHT 8 px, `byte[r*2+1]` = LEFT 8 px;
  render `word = (byte[r*2+1] << 8) | byte[r*2]`.
- **Centered single letter** (8-px glyph centered in the 16-px cell):
  `cell16 = (glyph_row << 4) & 0xFFFF; byte0 = cell16 & 0xFF; byte1 = (cell16 >> 8) & 0xFF`.
- **Pair glyph** (two 8-px letters in one cell, left = A, right = B):
  `byte[r*2] = B_row` (right), `byte[r*2+1] = A_row` (left). (`fontlib.compose_pair`.)

### 4.2 byte → S2 slot
For a half-width katakana byte, take the *full-width* katakana char it represents and:
```
ku, ten = sjis_to_kuten(fullwidth_char)      # JIS row/cell
S2 slot = (ku - 5) * 94 + (ten - 1)
```
Verified against the LORD test (ﾛ→slot 76, ﾄﾞ→slot 40, ﾚ→slot 75).

### 4.3 Proof-of-concept that established the method
- Edited FONT.DAT katakana glyphs ロ/ト/ド → L/T/D; Ledin's class screen showed "L ー D".
- Then pair-packed "LO"+"RD" into two katakana slots and set the class string to the two
  bytes addressing them; the screen showed **"LORD"** cleanly. No codec, no renderer patch,
  no crash (codes stayed in katakana range).

---

## 5. The Slot Budget (why not "fully like the dialogue font")

The dialogue and character names render tight because they go through the **dialogue/menu
text renderer**, which draws from thousands of **kanji-slot** pair-glyphs (the Route B
technique reaches them with 2-byte SJIS kanji codes). The class renderer is a different
path: it reads **single katakana bytes** and can only address the **katakana glyph bank**.
It physically cannot emit the kanji codes that reach those existing pair-glyphs, so the
dialogue's ~994 pairs are unreachable from a class string.

Reachable glyph slots for class names:
- **Single-byte katakana:** 45 base (0xB1–0xDD) + 10 small kana/ヲ (0xA6–0xAF) = **55**.
- **Dakuten / handakuten (2-byte codes):** base + ﾞ/ﾟ combine into the dakuten slot
  (ガギグゲゴ ザジズゼゾ ダヂヅデド バビブベボ パピプペポ) = **25 more**.
- **Total ≈ 80 addressable glyph slots.**

A full pair-pack of all 132 names needs **237 distinct pairs** — far over 80 — so a pure
pair font is impossible through this renderer. The achievable goal is a hybrid that packs
the common words tightly and fits every name in the field width.

**Dakuten safety:** the original class names themselves use dakuten/handakuten
(e.g. ﾊﾞﾝﾊﾟｲｱﾛｰﾄﾞ = Vampire Lord uses ﾊﾞ ﾊﾟ ﾄﾞ), which **proves the renderer combines
base+ﾞ/ﾟ into a single dakuten cell**. That is what makes the 25 extra slots usable. (The
first build avoided them out of caution — only ﾄﾞ had been individually confirmed — and was
limited to 55 slots, which caused the overflow described in §7.)

---

## 6. Encoding (hybrid single + pairs)

- **Token set:** all 48 distinct letters (guaranteed fallback) + the **32 most frequent
  letter-pairs** across the 132 names = **80 tokens**, one per addressable slot.
- **Assignment to minimize string bytes:** 48 letters → single-byte slots; the 7 most
  frequent pairs → the remaining 7 single-byte slots; the next 25 pairs → dakuten 2-byte
  slots. (Single-byte pairs save a byte each; dakuten pairs are byte-neutral vs two
  singles.)
- **Per-name encoding:** a min-cells dynamic program over each name (use a pair token when
  the bigram at the cursor is allocated, else a single), emitting the 1- or 2-byte code for
  each chosen token.
- **Spaces dropped** from multi-word names (the original Japanese had none), which shortens
  names and frees the space slot.
- **Result:** max **9 cells** per name (only Necromancer, Living Armor, Hellhound at 9;
  the rest ≤ 8), pool bytes **1014 / 1152** budget. The field is ~10 cells (inferred from
  where the first build truncated), so everything fits.

### 6.1 Pool repack & repoint (the actual edit)
1. Render the 80 glyphs into their S2 slots in FONT.DAT (centered singles / composed
   pairs).
2. Parse the original 132 strings from the pool (offset → index).
3. Pack the 132 new encoded strings back into the pool region (≤ 1152 bytes; pad the
   remainder with zeros up to the pointer table).
4. Rewrite the 255-entry pointer table: for each entry that pointed into the old pool,
   repoint it to the new offset of the same class index (preserving duplicates). Entries
   pointing outside the pool are left untouched.

---

## 7. Build History (this session)

1. **First class-name build:** 48 letters + 7 pairs, single-byte slots only (55 total).
   Most letters fell back to single (wide, centered) cells. In-game: class names rendered
   as **spaced single letters and overflowed/truncated** — "Sword Master" → "SwordMaste",
   "Silver Knight" → "SilverKnig", "Vampire Lord" → "VampireLo".
2. **Dakuten rebuild:** added the 25 dakuten/handakuten slots (proven safe by original
   usage) → 80 slots → 48 letters + 32 pairs. Names re-encoded to ≤ 9 cells; the common
   classes pack two letters per cell. This is the shipped version.
3. **Menu fold-in:** the menu work existed separately (`SCEN_menu.dat`, `FONT_menu.DAT`,
   built earlier) but had never been merged into the shipping build (the shipping SCEN was
   the pre-menu `SCEN_en.dat`, byte-identical to disc). Spliced both into the build and
   verified the menu's added glyphs (16 changed cells, all in **kanji** slots) are disjoint
   from the **katakana** slots the class names use (0 collisions).

---

## 8. Bottom-Bar Font Codec (deferred — research notes)

For completeness, the bottom-bar half-width font was investigated and **not** cracked:
- It is **asset 0** of a compressed archive loaded to Low Work RAM 0x00200000
  (= uncached 0x20200000): an offset table of ~207 BE uint32 entries, then blobs. Font
  asset 0 compressed = LowWorkRAM bytes **0x33C–0xCF2** (2486 B), first bytes
  `C0 01 C0 51 A2 7C 08 FC 61 0F D6 …`. The decompressed output is known (VDP2 VRAM
  0x20000).
- Loader chain (LANG1 file offsets; runtime = +0x06010000): font setup at 0xDEEA calls a
  load-queue manager 0x11850 → multi-state dispatcher 0x1F55C → handlers
  (0x06033F40, 0x0602C3A4, 0x0602C3BC, 0x0602C32C, 0x0602F13C, 0x0602FED8, 0x0602C4D4).
  The inner codec was not reached statically.
- The codec is **not** standard LZSS: an exhaustive brute force over bit polarity/order,
  ring-buffer init/start positions, common 12-bit-offset/4-bit-length encodings, header
  offsets, and thresholds produced no valid glyph run (watch for blank-tile false
  positives). Runtime literal-patching also fails because LANG1 relocates pointer literals
  at load.
- **Deterministic future unlock:** set an emulator write-breakpoint on the VDP2 VRAM
  destination (≈ 0x25E20000) during boot to land directly on the decompressor, then read
  it off. Until then the bottom bar stays katakana. (Full notes:
  `BOTTOM_BAR_FONT_NOTES.md`, `bottom_bar_font_map.png`.)

---

## 9. Name Alignment Finding (source-of-truth caveat)

The supplied `Classes_and_Troops.xlsx` (133 rows) is **not** in the ROM pool order past
index ~69 and contains entries that aren't in this game's class table. The **ROM pool order
is authoritative** for which string is which class. Observed divergences:
- **0–69:** xlsx matches the ROM 1:1 (use xlsx spellings directly).
- **70 / 71:** ROM = **Chaos / Lushiris** (xlsx had Monk/Barbarian, which are actually
  ROM 106 / 109).
- **87 / 88:** order **swapped** — ROM is **Crawler, High Elf**.
- **90+:** ROM has **Giant** (the ASCII-`G` string) and **Wraith** (ﾚｲｽ, *reisu*) that the
  xlsx lacks; the xlsx then drifts and includes names not present in this pool.

The shipped list was built from the ROM order (romanized), using xlsx spellings where the
content aligned and translator judgment for the divergent monster/boss entries. A few
spelling picks worth a second look: **Wraith** (ﾚｲｽ could be "Lace"), **Berserker**,
**Pikeman**, **Merman**, **Freya**, **Ifrit**, and **Aniki** (a literal carry-over of a
joke/boss label). The 132 list is in §11.

Unrelated spelling nit spotted in testing: a troop-type string renders "Undease" (likely
intended "Undead"); that lives in SCEN entry 0 and is a quick separate fix.

---

## 10. Build Pipeline & Key Constants

Working dir `/home/claude/lang/` (resets between sessions). Tools used:
`cdecc.py` (MODE1/2352 sector framing), `fontlib.py` (FONT bank offsets, `compose_pair`,
`sjis_to_kuten`, S2 base), `glyphlib.py` (8-px half-width glyph rows from the Toshiba TTF),
`scen_codec.py` (SCEN parse/serialize), `build_menu.py` / `splice_menu.py` (menu),
`xdelta3`, `openpyxl`, Capstone (SH-2 big-endian) for the static traces.

**Combined build (menu + class names):**
1. Base = `Langrisser1_EN_current.bin` (FONT_en + SCEN_en + original LANG1).
2. Splice `SCEN_menu.dat` and `FONT_menu.DAT` in place (same LBAs/sizes; reframe sectors).
3. Render the 80 class glyphs into their S2 slots (on top of FONT_menu).
4. Repack the LANG1 class-string pool + rewrite the 255-entry pointer table.
5. Verify: SCEN region == `SCEN_menu.dat`; class S2 slots ∩ menu kanji slots = 0;
   pool ≤ 1152; round-trip the xdelta byte-for-byte.
6. `xdelta3 -e -9 -S none -f -s orig.bin out.bin Langrisser1_EN_classes_menu.xdelta`.

```
LANG1.BIN     : disc LBA 202; loads to HWRAM 0x06010000; code pointer literals RELOCATE
Class pool    : file 0x617AC – 0x61C24 (132 null-terminated half-width katakana strings)
Pointer table : file 0x61C2C, 255 × 4-byte BE, base 0x06010000; does NOT relocate (safe)
16×16 render  : char loops 0x1B150 / 0x1B190; resolver 0x19F4C(mode,code); mode-4 → S2
byte→S2 slot  : slot = (ku-5)*94 + (ten-1)  from the full-width katakana char
FONT cell     : 16×16 1bpp = 32 B; byte0 = RIGHT 8px, byte1 = LEFT 8px
centered glyph: cell16 = glyph_row << 4
Slots reachable: 55 single-byte katakana + 25 dakuten/handakuten (2-byte) = 80
Encoding      : 48 letters + 32 pairs, DP min-cells, ≤9 cells, pool 1014/1152 B
Bottom bar    : VDP2 VRAM 0x20000; byte→tile = byte−0x70; compressed font NOT cracked
Disc (LI)     : FONT 135070 (220,732 B); SCEN 136946 (745,472 B grown English)
```

---

## 11. The 132 Class Names (ROM pool order)

```
  0 Fighter        33 Priest         66 Dark Master     99 Leviathan
  1 Gladiator      34 Summoner       67 Wizard         100 Harpy
  2 Vampire        35 Mage           68 Princess       101 Fairy
  3 Knight         36 Saint          69 High Master    102 Bat
  4 Pirate         37 Unicorn Knight 70 Chaos          103 Griffin
  5 Hawk Knight    38 Minotaur       71 Lushiris       104 Angel
  6 Sister         39 Living Armor   72 Soldier        105 Gargoyle
  7 Shaman         40 Succubus       73 Berserker      106 Monk
  8 Warlock        41 Kraken         74 Grenadier      107 Crusader
  9 Werewolf       42 Phoenix        75 Dark Guard     108 Queen Ant
 10 Gelgazer       43 General        76 Lancer         109 Barbarian
 11 Ghost          44 Sword Master   77 Trooper        110 Bandit
 12 Scylla         45 Knight Master  78 Hellhound      111 Zombie
 13 Roc            46 Serpent Lord   79 Royal Lancer   112 Skeleton
 14 Lord           47 Dragon Lord    80 Dragoon        113 Wolfman
 15 Assassin       48 High Priest    81 Bone Dino      114 Ogre
 16 Silver Knight  49 Zauberer       82 Pikeman        115 Gel
 17 Captain        50 Arch Mage      83 Phalanx        116 Elemental
 18 Hawk Lord      51 Sage           84 Golem          117 Civilian
 19 Cleric         52 Ranger         85 Elf            118 Valkyrie
 20 Necromancer    53 Master Dino    86 Dark Elf       119 Freya
 21 Sorcerer       54 Stone Golem    87 Crawler        120 White Dragon
 22 Paladin        55 Vampire Lord   88 High Elf       121 Salamander
 23 Kerberos       56 Jormungand     89 Witch          122 Iron Golem
 24 Dullahan       57 Great Dragon   90 Giant          123 Demon Lord
 25 Lich           58 King           91 Ballista       124 Sleipnir
 26 Serpent        59 Emperor        92 Wraith         125 Fenrir
 27 Wyvern         60 Hero           93 Spectre        126 Aniki
 28 High Lord      61 Queen          94 Demon          127 Builder
 29 Swordsman      62 Royal Guard    95 Arch Demon     128 Bishop
 30 Highlander     63 Serpent Master 96 Merman         129 Grand Knight
 31 Serpent Knight 64 Dragon Master  97 Lizardman      130 Basilisk
 32 Dragon Knight  65 Agent          98 Nixie          131 Ifrit
```

---

## 12. Open Items / Next Steps

1. **In-game confirmation of the dakuten class-name build** across player, enemy, and NPC
   status screens, including a 9-cell edge case (Necromancer / Living Armor / Hellhound).
2. **Spelling review** of the translator-judgment names in §9.
3. **"Undead" troop-type fix** (SCEN entry 0 "Undease").
4. **Bottom status bar** class names — deferred; requires cracking the compressed VDP2
   font codec (see §8). Best lever: emulator write-breakpoint on the VDP2 VRAM font
   destination during boot.
5. **Optional full parity** with the dialogue font (every class name fully pair-packed):
   would require rerouting the 16×16 status screen to pull the class through the dialogue
   renderer (kanji-slot pairs) instead of the katakana class renderer — a deep, relocation-
   sensitive LANG1 code patch. Only worth attempting if the current hybrid reads as too
   sparse on the rare names.
