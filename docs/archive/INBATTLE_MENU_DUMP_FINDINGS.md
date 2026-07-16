> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> In-battle menu dump analysis — merged into docs/in_battle_ui/MENU_CHROME.md.
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# In-Battle Menu — Dump Analysis (Game Settings / Command Ring / Option List)

Analysis of the paired VDP2-VRAM / HWRAM / LWRAM dumps (3 menu states). Goal: assess whether
the custom in-battle menus can be translated.

## How the menus are drawn (confirmed)
- The menu text is a **VDP2 tilemap** (pattern-name table found at VRAM `0x0820C`+). Each
  on-screen character is a **16×16 glyph = four 8×8 tiles**, and the glyphs are written into
  **consecutive tile slots** (e.g. char numbers `0x4B8, 0x4BC, 0x4C0, …`, +4 per glyph). So the
  text is **composed glyph-by-glyph at runtime**, not a fixed string of tile indices.
- The glyphs come from a **custom font in VDP2 VRAM at `0x20000`** (8×8, 4bpp). That font
  contains exactly what the Japanese UI needs: the menu kanji (移動/攻撃/設定/戦闘/高速…),
  katakana (ゲーム), digits, the stat labels (LV AT DF MP MV HP), TURN, SCENARIO, and a
  **partial Latin set** (about A T D F M P V H S Z C M D R O + lowercase a, plus ON/OFF).
- The `0x30000` VRAM region is the **separate SCEN/dialogue renderer** (it held stale
  "勝利条件 / クリスが…" conditions text) — that's the system already fully translated.

## The two blockers (both confirmed against the dumps)
1. **The custom font cannot be edited from the disc.** Its bytes do not appear — as 4bpp or
   1bpp, in any bit order tried — in LWRAM, HWRAM, LANG1.BIN, 0.BIN, IMG.DAT, or the full disc
   image. It is **decompressed directly into VRAM by the IMG.DAT codec at load time**, and that
   codec's decoder back-end is still unsolved. So the missing Latin letters (B G K L W Y, most
   lowercase, …) needed for English menu words **cannot be added by a static disc edit**.
2. **The menu source strings are in an unknown custom encoding.** The labels (ゲーム設定,
   移動, セーブ, 勝利条件, …) appear as Shift-JIS **nowhere** — not on disc and not in runtime
   RAM. They are stored/encoded in a custom form that drives the glyph-composition routine, and
   that form/location has not been cracked.

## Realistic paths (all heavy, none a static-patch win)
- **(A) Crack the IMG.DAT codec back-end** → decompress the font, add Latin glyphs, recompress,
  then locate+rewrite the menu strings. The codec is the long-standing blocker.
- **(B) Code-injection in LANG1.BIN** (which *is* editable — loads verbatim to `0x06010000`):
  hook a point after the font DMA to **write ~20 Latin glyph tiles into spare font slots in
  VRAM**, then find the glyph-composition routine and patch the per-label source so it composes
  English. Requires SH-2 disassembly of the menu renderer in the HWRAM image to find the string
  pointer + encoding + an injection site. Multi-stage, uncertain, but does not need the codec.

## Recommendation
Everything story-facing is translated (dialogue, prologues, names, items, scenario titles,
quiz, tutorial, troop types, in-battle save/load + magic + summon + battle messages, victory/
defeat conditions, and the character endings). What remains Japanese is the in-battle menu
**chrome** — ~15 short labels (command ring, option list, settings) plus class names — all on
this one custom system. It is a large reverse-engineering project for a small cosmetic gain.
Path (B) is the only route that avoids the codec; it can be attempted but should be scoped as
its own effort.

## Useful coordinates (for a future attempt)
```
VDP2 custom font (master)  : VRAM 0x20000, 8x8 4bpp tiles; partial Latin + menu kanji
VDP2 menu tilemap          : ~0x0820C; 16x16 glyphs = 4 consecutive 8x8 tiles; slots from char 0x4B8 (+4/glyph)
VDP2 SCEN/dialogue glyphs  : 0x30000 (already-translated path; not the menu font)
Font source                : NOT present uncompressed anywhere -> IMG.DAT codec, decompressed to VRAM
Menu strings               : not SJIS anywhere -> custom encoding, location/format unknown
LANG1.BIN                  : loads verbatim to 0x06000000 region (HWRAM dump) -> editable for code hooks
Dumps on hand              : gamesettingsubmenu/gamesetting/statuscommand × {vdp2,hwram,lwram}
```

---

# UPDATE — Exploratory disassembly crack (the in-battle UI text system is now understood)

Disassembling LANG1.BIN (capstone SH-2 BE; HWRAM image confirms the live values) cracked the
encoding and the full render pipeline.

## The encoding: 1-byte custom codes
The menu renderer at **CPU 0x60152E8** (file 0x52E8) iterates a `rows × cols` grid and for each
cell does:
```
mov.b @r10,r6      ; read ONE byte = the character's custom code
extu.b r6,r6
jsr  @r12          ; glyph-draw(col, row, code)
add  #4,r10        ; next cell — grid cells are 4 bytes, the code is byte 0
```
So every on-screen character is a **single 1-byte code** (not SJIS), stored in a 4-byte-stride
grid. `rows` is read from `0x06087210`, `cols` from `0x06093430`.

## The render pipeline (all addresses confirmed)
```
grid  0x060A21F0  (shared UI buffer: rows×cols, 4 bytes/cell, code in byte 0)
   |  written by ~14 builder functions; drawn by ~4 renderers
renderer 0x60152E8  --r12-->  glyph-draw 0x06015274
   glyph-draw: code*18 -> 9 VDP2 pattern words in table 0x060859F0 (a 3x3 tile = 24x24 glyph)
               blits them into staging buffer 0x06087220, later DMA'd to VDP2 VRAM
font  VDP2 VRAM 0x20000  (8x8 4bpp tiles; the pattern words index into it, low 12 bits = char#)
```
- glyph-draw `0x06015274` is shared by the renderers at 0x60186E8, 0x6023CA0, 0x60262 98 (and ours).
- The decode pipeline was reproduced offline: codes 0x00–0x27 render as the real text glyphs
  (DF, digits, HP, MP, SCE…, RN, ZCM, etc.); higher codes share the table with map-terrain tiles.

## Why this still doesn't unlock a clean patch
1. **Font + glyph table are runtime-built.** LANG1's static image ends at 0x06074F14, but the
   glyph table (0x060859F0), staging buffer (0x06087220) and grid (0x060A21F0) all live *above*
   that — they are produced at runtime, almost certainly by the **IMG.DAT decompressor**. So the
   missing Latin letters (B G K L W Y + most lowercase) cannot be added by editing a static table
   on disc; you must either crack the IMG.DAT codec or inject them at runtime.
2. **Too few Latin glyphs to spell the words.** The font only carries the letters the JP UI needs
   (≈ A C D E F H I M N O P R S T U V Z), so SAVE/LOAD/ATTACK/MAGIC/BATTLE/SETTINGS etc. cannot be
   spelled without adding glyphs.
3. **The label code-strings are written by builder code**, not pinned to one static table yet;
   rewriting them to English means tracing the relevant builder(s).

## Scoped path (B) — runtime code-injection in LANG1 (no codec needed)
Now fully defined, but a real multi-part hack:
1. Hook a point after the font DMA into VRAM 0x20000 (font-load refs near file 0xDF58 / 0x2BBF8 /
   0x3FC0C, the streaming-codec loop at ~0x2BB00) and **write ~12 missing Latin 8x8 tiles** into
   spare font tiles in VRAM.
2. **Add code→glyph entries** for the new letters to the glyph table at 0x060859F0 (also runtime —
   either extend it via the same hook, or repoint the table).
3. **Locate and rewrite** each menu's 1-byte-code string (the builders that fill 0x060A21F0).

## Net
The encoding and rendering are no longer a mystery — every address and the exact mechanism are
known. Turning that into shipped English menus is an engineering project (runtime glyph injection
+ string rewrite), not a discovery problem. It remains the one large, optional remainder; all
story-facing text is done.
