> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> In-battle menu (Route 1) research — merged into docs/in_battle_ui/MENU_CHROME.md.
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# Route 1 (runtime glyph injection) — progress from the disassembly trace

## Solidly established this pass
- **Encoding = 1-byte custom codes** (confirmed by disassembling the renderer at CPU 0x60152E8).
- **Asset pipeline:** an init function at **0x60151F0** decompresses IMG.DAT **asset 4 → the glyph
  table at 0x060859F0** and **asset 5 → 0x060C8000 (font, then DMA'd to VRAM 0x20000)**. Both are
  runtime data (above LANG1's static range), which is exactly why they can't be edited as static
  disc bytes — confirming Route 1 (runtime injection) is the right approach. The **end of this
  init function is the natural hook point** (after both assets are present).
- **Free capacity is ample:** the glyph table has **147 unused 1-byte code slots** (0x64+), and the
  VRAM font has **585 free tiles** safe to write into. An English alphabet needs ≤9 tiles/letter.
- **Glyph generator built & verified** (`menuglyph.py`): renders any letter into the font's exact
  format (4bpp, ink index 0x0E), sliced into the tile grid, and emits the matching glyph-table
  entry. Preview of the full alphabet: `menuglyph_preview.png`.

## Course-correction (important)
There are **two separate in-battle render systems**, not one:
1. A **24×24 (3×3-tile)** system via glyph-draw 0x6015274 / grid 0x060A21F0 — the one first traced;
   it renders some always-present element (its grid was identical across all three captures).
2. A **16×16 (2×2-tile)** system that draws the actual **pop-up menus** (command ring, option list,
   settings). Confirmed by decoding the command ring's on-screen tilemap: e.g. 移 = tiles
   0x5CC/0x5CD/0x5CE/0x5CF (2×2). Its glyphs are composed into VRAM display slots (~char
   0x428–0x5F3) that the tilemap then references.

16×16 is the **same size as the dialogue font (FONT.DAT)**, which raises the key open question.

## The key open question (decides how easy Route 1 is)
Are the 16×16 pop-up-menu glyphs **sourced from FONT.DAT** (which we already edit freely) or from a
separate custom font? A direct compare was inconclusive because the menu layer's tile numbers are
relative to a **VDP2 character-base offset** not yet resolved (the test glyph rendered blank at the
naive address). Resolving the char-base (from the VDP2 registers / by searching VRAM for a known
FONT.DAT glyph expanded to 4bpp) answers this:
- **If FONT.DAT-sourced:** no glyph injection needed — translate by finding the code→glyph mapping
  and pointing the menu strings at English; the buffer/codec problems disappear.
- **If separate font:** proceed with injection (generator + 147 codes + 585 tiles already in hand),
  but target the 16×16 system's font/table rather than the 24×24 one.

## Next sub-steps
1. Resolve the VDP2 character-base for the menu layer → confirm the 16×16 menu glyph source font.
2. Find the 16×16 pop-up renderer + its code-string (the menu label data) — the thing to rewrite.
3. Build a minimal **one-letter test patch** (inject/point one glyph + swap one menu character) for
   in-game verification. (Untestable offline — needs an SSF screenshot to confirm.)

---

# UPDATE 2 — probe answered: separate font, but most Latin is already there

Resolved the question from Update 1 by locating the composed glyphs directly in VRAM.

## The menus use their OWN 16×16 font, not FONT.DAT
- Rendering VRAM as 16×16 glyphs surfaced the menu font as a readable band at ~VRAM 0x26000–
  0x2A000 (inside the 0x20000 custom-font region): it contains the exact menu vocabulary —
  アイテム装備 指揮官 配置 勝利条件 ゲーム設定 フェイズ終了 移動攻撃魔法召喚治療 0123456789
  TURN SCENARIO, etc.
- A correlation search for FONT.DAT's 移 found **no match anywhere in VRAM** (best IoU < 0.5), and
  the menu 移 is visibly a different style. So the menu font is independent of FONT.DAT. (FONT.DAT
  slot math was separately verified correct, so the negative result is real, not a bug.)

## Good news: the menu font already carries most of the Latin alphabet
Visible in the font band: roughly **A C D E F H I K L M N O P R S T U V X Y** (plus digits). This is
a *much* fuller set than the tiny 8×8 status-bar font from earlier sessions (those are different
fonts). Practical consequence — many menu words are spellable with glyphs that ALREADY exist, so
those need only a code-string rewrite, no glyph injection at all:
- SAVE, LOAD, MOVE, ATTACK, HEAL, COMMAND, END, PHASE → all letters present
- Only a few letters look absent (G, J, Q, W, Z + lowercase) → injection needed just for words like
  GAME / MAGIC / etc.

## Refined Route 1 plan
1. Determine the **code → glyph mapping** (the 1-byte code's index into this font sheet) and locate
   the **menu code-strings** (the data the 16×16 menu builder reads). This is the remaining unknown.
2. Rewrite those strings to English using the **existing** Latin glyph codes wherever possible.
3. Inject the **few** genuinely-missing letters (generator already built) into spare font tiles via
   the runtime hook, and add their code→glyph entries — only as needed.

## Net
The hard "can we even get letters" worry is largely answered: the alphabet is mostly present in the
menu's own font. The crux now is purely the **code→glyph mapping + where the menu strings live**, then
rewriting them (with minimal injection). Still needs in-game testing on your side, but the path is
clearer and lighter than feared.

---

# UPDATE 3 — font index map, the render chain, and an editable conversion table

## Font glyph map (menu's own 16×16 font, VRAM ~0x26000 = char 0x1300+)
Read directly off the font sheet (TL tile char number; +4 per glyph). Latin already present:
```
S=0x149C A=0x14A0 V=0x14A4 L=0x14AC O=0x14B0 D=0x14B4 K=0x14CC Y=0x14D4 ...
勝=0x148C 利=0x1490 条=0x1494 件=0x1498   ゲ=0x14B8 ー=0x14BC ム=0x14C0 設=0x14C4 定=0x14C8
```
Menu words are stored as **consecutive glyph runs** (勝利条件 = 0x148C–0x1498; ゲーム設定 = 0x14B8–0x14C8).

## Render chain (16×16 pop-up menus)
font glyph (char 0x13xx+) → builder **composes** it into a low "display slot" (char ~0x4xx–0x8xx)
→ writes the slot's char number into a **HWRAM tilemap buffer** (~0x06076880) → DMA to VRAM tilemap
(0x08000) → on screen. So translating means making the builder compose **different** font glyphs
(the Latin ones, which exist) for a given menu item.

## What resisted: the editable "menu definition"
The thing that tells the builder which glyphs per item was **not** found as a static char-number or
glyph-index table — byte-searches for the computed index runs (e.g. ゲーム設定 → 6E 6F 70 71 72)
hit only coincidental matches inside math/ramp lookup tables. So the definition is either built by
code or encoded in a form not yet matched; pinning it needs a focused disassembly of the specific
16×16 builder (a deeper trace).

## An editable artifact found (different renderer, but real)
A half-width text renderer at **0x60354A0** reads 1-byte codes from the shared UI grid (0x060A21F0)
and translates them through a **conversion table at LANG1 file 0x63A98 (CPU 0x06073A98)** — masked to
7 bits — before writing to VRAM. That table **is inside LANG1's static range, so it is editable on
disc** (splice like FONT/SCEN). It belongs to the half-width status/class-name path (whose font is
the one missing many letters), but it confirms the *kind* of lever Route 1 needs and that LANG1 data
tables are reachable.

## Honest status
We've gone from "total mystery" to: menu font identified and mapped, full render chain understood,
capacity confirmed (147 codes / 585 tiles), glyph generator built, and an editable LANG1 conversion
table located. The remaining crux — the 16×16 pop-up **menu definition** (the exact bytes to rewrite)
— is a multi-renderer trace that hasn't fully yielded, and importantly **none of this is verifiable
without in-game testing on your side**. This is a large, multi-session reverse-engineering effort
with several independent text systems; each layer has revealed another.
