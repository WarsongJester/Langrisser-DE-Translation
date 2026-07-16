# In-Battle Menu Chrome — Reference (DEFERRED frontier)

**Status: DEFERRED.** The command ring (移動/攻撃/魔法/治療/指令) and system/settings menus
(セーブ/ロード/勝利条件/ゲーム設定/フェイズ終了, options 高速/通常/ON/OFF) still render in
Japanese. The encoding and full render pipeline are **fully reverse-engineered**; what remains
is an engineering effort (runtime glyph injection + string rewrite), not a discovery problem.

This consolidates `ROUTE1_PROGRESS.md`, `INBATTLE_UI_RESEARCH.md`, `INBATTLE_MENU_DUMP_FINDINGS.md`,
and `BATTLE_MENU_*.md` (all archived). The IMG.DAT codec details are in `IMG_DAT_CODEC.md`.

> **Scope vs class names.** This is a *different* custom system from class names (which are
> **done** — see `CLASS_NAMES.md`). The two share the VRAM `0x20000` font region but use
> different renderers and different source data.

---

## 0. What the menus actually are

- The menu text is a **VDP2 tilemap** composed **glyph-by-glyph at runtime** (not a fixed string
  of tile indices, and not pre-rendered bitmap strips). Each on-screen character is a 16×16 glyph
  = **four consecutive 8×8 tiles** (char numbers like 0x4B8, 0x4BC, 0x4C0, …, +4 per glyph),
  written into a HWRAM tilemap buffer (~0x06076880) then DMA'd to the VRAM tilemap (~0x0820C+).
- The glyphs come from a **custom 8×8 4bpp font in VDP2 VRAM at 0x20000** — the same font region
  as the bottom-bar class names. It carries the Japanese UI vocabulary (移動/攻撃/設定/戦闘…,
  katakana, digits, stat labels, TURN, SCENARIO) plus a **partial Latin set** (≈ A C D E F H I
  K L M N O P R S T U V X Y + a few lowercase + ON/OFF).
- The VRAM `0x30000` region is the **separate SCEN/dialogue renderer** (already fully translated)
  — not the menu font.

There are actually **two in-battle render systems** sharing the UI grid:
1. A **24×24 (3×3-tile)** system (glyph-draw 0x06015274 / grid 0x060A21F0) for always-present
   elements (stat labels etc.).
2. A **16×16 (2×2-tile)** system that draws the **pop-up menus** (command ring, option list,
   settings). This is the translation target.

---

## 1. The encoding & render pipeline (mapped)

**Encoding = 1-byte custom codes.** The menu renderer iterates a `rows × cols` grid and reads
one byte per cell (4-byte stride, code in byte 0):
```
mov.b @r10,r6      ; one byte = the character's custom code (NOT SJIS)
extu.b r6,r6
jsr  @r12          ; glyph-draw(col, row, code)
add  #4,r10        ; next cell (4-byte stride)
```
`rows` from 0x06087210, `cols` from 0x06093430 (24×24 renderer at CPU 0x60152E8).

**Render chain (confirmed addresses):**
```
grid 0x060A21F0  (shared UI buffer: rows×cols, 4 B/cell, code in byte 0)
   | written by ~14 builder functions; drawn by ~4 renderers
renderer 0x60152E8 --r12--> glyph-draw 0x06015274
   glyph-draw: code*18 → 9 VDP2 pattern words in glyph table 0x060859F0 (a 3×3 = 24×24 glyph)
               blits into staging buffer 0x06087220 → DMA to VDP2 VRAM
font VDP2 VRAM 0x20000  (8×8 4bpp tiles; pattern-word low 12 bits = char#)
```
For the **16×16 pop-up** path specifically: font glyph (char 0x13xx+, font band at VRAM
~0x26000) → builder **composes** it into a low display slot (char ~0x4xx–0x8xx) → writes the
slot's char number into the HWRAM tilemap buffer → DMA. Translating means making the builder
compose the **Latin** glyphs (which mostly exist) for a given menu item.

---

## 2. The two blockers

1. **Most needed Latin letters are missing from the font**, and **the font can't be edited
   statically** — it's runtime-decompressed into VRAM by the IMG.DAT codec, whose decoder
   back-end is unsolved (`IMG_DAT_CODEC.md`). The font's bytes don't appear (in any bit order)
   in LWRAM, HWRAM, LANG1.BIN, 0.BIN, IMG.DAT, or the raw disc. So letters like G J Q W Z + most
   lowercase can't be added by a disc edit.
2. **The menu source strings aren't a simple static table.** The 1-byte-code label strings are
   written by **builder code** filling 0x060A21F0; byte-searches for the computed glyph-index
   runs (e.g. ゲーム設定 → a 0x6E 0x6F 0x70 0x71 0x72 run) only hit coincidental matches in
   math/ramp tables. Pinning the exact bytes to rewrite needs a focused disassembly of the
   specific 16×16 builder. (Also: the labels appear as **Shift-JIS nowhere** on disc or in RAM —
   confirming the custom encoding.)

---

## 3. The path forward — "Route 1" runtime glyph injection (no codec needed)

Because **LANG1.BIN loads verbatim** (no relocation — confirmed by HWRAM dumps), code injection
is reliable. This sidesteps the IMG.DAT codec entirely:

1. **Hook a point after the font DMA** into VRAM 0x20000 (font-load refs near LANG1 file 0xDF58 /
   0x2BBF8 / 0x3FC0C; streaming-codec loop ~0x2BB00) and **write the ~12 missing Latin 8×8 tiles**
   into spare font tiles in VRAM. Capacity is ample: **585 free VRAM tiles** and **147 unused
   1-byte code slots** in the glyph table.
2. **Add code→glyph entries** for the new letters to the glyph table at 0x060859F0 (also runtime —
   extend via the same hook or repoint the table).
3. **Locate and rewrite** each menu's 1-byte-code string (the builders that fill 0x060A21F0) to
   English, using existing Latin glyph codes where possible and the injected ones otherwise.

**Glyph generator already built:** `tools/menuglyph.py` renders any letter into the font's exact
format (4bpp, ink index 0x0E), sliced to the tile grid, emitting the matching glyph-table entry.
Preview: `reference_images/menuglyph_preview.png`.

**Editable lever confirmed:** a half-width text renderer at 0x60354A0 translates 1-byte codes
through a **conversion table at LANG1 file 0x63A98 (CPU 0x06073A98)**, masked to 7 bits, which is
**inside LANG1's static range → editable on disc**. It belongs to the status/class-name path but
confirms the kind of lever Route 1 needs.

**Remaining unknown:** the exact 16×16 **menu-definition** bytes (which glyphs per item, and
where the builder reads them). That's the focused trace still to do.

---

## 4. Alternative path — crack the IMG.DAT codec

Crack the streaming Huffman-LZ decoder (and write a matching encoder), decompress the font, add
Latin glyphs, recompress, then rewrite the menu strings. This is the heavier route and also
unlocks any other compressed graphics. See `IMG_DAT_CODEC.md`. Not recommended as the first move —
Route 1 is lighter.

---

## 5. Recommendation & coordinates

Everything story-facing is translated; the menu chrome is ~15 short labels + (already-done) class
names on this one custom system — a large RE effort for a small cosmetic gain. If pursued, **Route
1 (runtime injection)** is the path; scope it as its own effort and verify in SSF/Mednafen.

```
24×24 renderer    : CPU 0x60152E8; glyph-draw 0x06015274; grid 0x060A21F0; glyph table 0x060859F0
16×16 pop-up      : font band VRAM ~0x26000 (char 0x13xx+); composes into display slots char ~0x4xx
VDP2 menu tilemap : ~VRAM 0x0820C; 16×16 glyph = 4 consecutive 8×8 tiles; +4/glyph
custom font       : VRAM 0x20000, 8×8 4bpp; partial Latin + menu kanji; runtime-decompressed (IMG.DAT)
capacity          : 147 free 1-byte codes; 585 free VRAM tiles
editable table    : conversion table @ LANG1 file 0x63A98 (CPU 0x06073A98), 7-bit masked (static)
LANG1.BIN         : loads verbatim @0x06010000 → code hooks reliable (Route 1 enabler)
generator         : tools/menuglyph.py  (preview reference_images/menuglyph_preview.png)
dumps on hand     : {gamesetting, gamesettingsubmenu, statuscommand} × {vdp2, hwram, lwram}
```
