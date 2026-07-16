# Langrisser I (Sega Saturn, *Dramatic Edition*) — In-Battle Menu Hacking Handoff

Prepared for an independent reviewer. This document is self-contained: it covers the
in-battle **command ring** and **Order sub-menu** English translation built this session,
the mechanism behind it, every hard-won constraint, the final **EN_46** merge, and what
remains. It assumes familiarity with SH-2 assembly and Sega Saturn VDP2, but explains the
project-specific parts.

Companion docs already in the project (not reproduced here): `LANGRISSER1_EN_HACKING_REFERENCE.md`,
`SCEN_DAT_FORMAT.md`, `FONT_DAT_FORMAT.md`, `docs/in_battle_ui/CLASS_NAMES.md`.

---

## 0. TL;DR status

| Piece | State |
|-------|-------|
| Story text (dialogue, prologues, names, items, quiz, tutorial, conditions, endings) | DONE (EN_45), unchanged this session |
| In-battle **command ring** (Move/Attack/Magic/Treat/Order, all unit types incl. frozen) | **DONE, confirmed in-game** |
| **Order sub-menu** (DUEL/RUSH/HOLD/USER) | **DONE, confirmed in-game** |
| "Undease" → "Undead" troop-type typo | **DONE** (21 occurrences) |
| Combined release **EN_46** = EN_45 + menus + typo | **BUILT & fully verified offline; awaiting final in-game spot-check** |
| Summon command (Volkoff etc.) | Left Japanese (out of scope) |
| Entry-4 place names (SCEN) | **NOT started** — last remaining story-text task |
| In-game class names (status bar + 16×16 panel) | Deferred; separate solved-but-unmerged RE (see project `CLASS_NAMES.md` / `inject_AZ`) |

Deliverables: `Langrisser1_EN_46_full.xdelta` (combined, ship this) and
`Langrisser1_EN_menu_ring_full.xdelta` (menus-only, on clean JP — useful for isolated menu testing).

---

## 1. Build & test workflow

- All patches are **xdelta3** against the **clean Japanese `.bin`** (MODE1/2352, 656,591,376 bytes).
- Apply: `xdelta3 -d -s <CLEAN_JP.bin> <patch>.xdelta out.bin` → rename → load `.cue` in
  **Kronos, PCM OFF** (SSF/Mednafen also work; Kronos is primary and has the debugger).
- EN_46 uses the **same `Langrisser1_EN_test.cue` as EN_45** (disc geometry identical, +42 sectors).
- **Note:** the EN_45 xdelta uses LZMA secondary compression — decode it with the real
  `xdelta3` binary, not the pure-python `pyxdelta` (which lacks LZMA).

---

## 2. Disc layout (verified by parsing both filesystems)

| File | clean JP LBA | EN_45 LBA | size |
|------|-------------:|----------:|-----:|
| LANG1.BIN | 202 | **202 (unchanged)** | 413,460 |
| LANG1/FONT.DAT | 135,070 | **135,070 (unchanged)** | 220,732 |
| LANG1/SCEN.DAT | 136,946 | 136,946 | 659,456 → **745,472 in EN_45** |
| LANG2/FONT.DAT | 144,527 | 144,569 (+42) | 220,732 (untouched) |
| LANG2/SCEN.DAT | 157,751 | 157,793 (+42) | 4,517,888 (untouched) |

**Key merge finding:** the old handoff warned that EN_45 shifts LANG1 by +42 sectors. That
is **wrong** — SCEN.DAT grew *in place*, so only files with LBA **> SCEN** shifted. LANG1
(202) and FONT.DAT (135070) are **before** SCEN and did **not** move, and EN_45's LANG1 is
**byte-identical to clean JP**. So the menu hook splices into EN_45 at the exact same file
offsets as on clean JP.

LANG1.BIN loads verbatim to HWRAM **0x06010000** (file offset = CPU − 0x06010000).
LANG1 image ends at file **0x64F14**. Code for another overlay lives immediately after.

---

## 3. The in-battle menu system (what this session reverse-engineered)

### 3.1 The tilemap / staging buffer
The command ring is a VDP2 NBG tilemap. The game builds it in a **HWRAM staging buffer at
0x060765F8** (call it `BUF`), then a DMA copies it to VDP2 VRAM each frame. Cells are 2-byte
big-endian **character numbers**; each 8×8 tile. Row stride **0x80** (64 cells). A 16-px-tall
menu row = a **top row** at offset `X` plus a **bottom row** at `X + 0x80`.

Character number → glyph pixels: cell value `W` selects the VRAM tile at
**`VRAM_charbase + W*0x20`**, where the live charbase is **0x25E20000** (so `W=0x00C7` →
0x25E218E0). In save-states the VDP2 VRAM is stored with a **+0x120 byte offset** relative to
CPU addresses — i.e. `raw_vram[0x20120 + W*0x20]` (see §7, this cost us a full test cycle).

### 3.2 Command ring layout (all verified from save-states)
Commands are a **fixed sequence, packed with no gaps**, a subset per unit:
`移動 Move, 攻撃 Attack, 魔法 Magic, 召喚 Summon, 治療 Treat, 指令 Order`.
Item *slots* are **0x180 apart**: slot1=0x28E, slot2=0x40E, slot3=0x58E, slot4=0x70E,
slot5=0x88E, slot6=0xA0E (these are the **top-row, column-7** cell of each item).
Per item: 5 usable cells (cols 7–11) on the top row, bottoms at +0x80. Col 6 = cursor cell.

**Guard = the Japanese first-character's tile code, position-independent:**
Move=0x5CC, Attack=0x5D4, Magic=0x5D8, Treat(治)=0x5E8, Order(指)=0x428. Cursor glyph=0x306F.
Blank=0x1000 (opaque). The ring hook keys off these guards so it works regardless of which
slot a command lands in for a given unit.

Confirmed unit command sets: Soldier {Move,Attack}; Hawk Lord {Move,Attack,Treat,Order};
Fighter/Lord (Ledin) {Move,Attack,Magic,Treat,Order}; Sword Master (Volkoff)
{Move,Attack,Magic,Summon,Treat,Order}; frozen unit {Order only, cursor at 0x28C=0x306F,
guard 0x428 at 0x28E}.

### 3.3 Order sub-menu
Selecting Order opens a second box (behaviour modes: 戦闘/突撃/防御/手動). It is drawn into
the **same staging buffer**, overlapping the ring's lower rows. Measured geometry (from
`ordermenu.yss` / `ordermenu2.yss`):
- Box rows are the item rows 11/14/17/20 (top) with the **box right-border tile 0x314 at col 15**.
- Each behaviour label is a **4-cell kanji pair** occupying **cols 11–14**; the menu **cursor
  sits at col 10** (one cell left of the pair) and must never be overwritten.
- Guard kanji tiles: 戦=0x4F1, 突=0x691, 防=0x611, 手=0x619 (all at **col 12** of their row).
- The box is at the **same screen position regardless of which slot Order occupies** (verified
  on Hawk Lord, where Order is a different slot than on Ledin) — so **fixed offsets are safe**.

---

## 4. The hook (mechanism)

### 4.1 Injection
The per-frame menu draw calls a small DMA-enqueue helper we call **`copy_fn` @ 0x0604A26C**.
A call site at CPU **0x0603C0B8** (file 0x2C0B8) loads copy_fn's address from a literal; the
patch **rewrites that literal to 0x06074C30** (our hook), so the hook runs first, then
tail-calls copy_fn to do the original work. copy_fn preserves r5/r6/r8–r13 and enqueues a
16-byte DMA descriptor {mode=3, dst=r5, src=r4, count=r6 longs} at queue base 0x06008000;
it clobbers r1,r2,r3,r7,r14. PR is preserved through the hook so copy_fn's `rts` returns to
the original caller (~0x0603C060).

### 4.2 Hook structure (see `tools/build_ring_shared.py`, the generator)
1. Push r4,r5,r6,r11,r12,r13,r14,pr.
2. **Gate** — inject only if a real ring is open: `(Move@slot1 AND Attack@slot2)` OR
   `(cursor 0x306F @0x28C AND Order 0x428 @0x28E)` (frozen). Two-cell signatures so boot/map/
   load never trigger.
3. **Write pass** — a table of 14 descriptors (10 ring + 4 sub-menu). For each: check guard;
   if matched, write `ncols` top cells and derive the bottom row.
4. **DMA loop** — 12 entries, uploads the 36 custom ring glyph tiles from LANG1 into VDP2
   char RAM (see §5).
5. Restore, tail-jump to copy_fn.

### 4.3 Descriptor format (FINAL — aligned, 12-byte fixed stride)
`[H top_off][H guard][B packed][B ncols][6 × B top-tiles]` where `packed = (extra<<4)|bmode`:
- `top_off` — first cell written (top row).
- `guard` — value compared against `BUF[top_off + (extra>>1)]`. For **ring** items `extra=0`
  (packed hi-nibble carries the palette, which is 0 for ring), so guard is checked at
  `top_off`. For **sub-menu** items `extra` is derived from the palette nibble (`pal>>1 = 2`),
  so guard is checked at `top_off+2` — i.e. the kanji sits one cell right of where the English
  word starts. (Reusing `pal>>1` as the guard delta was a deliberate byte-saving trick; see §8.)
- `ncols` — cell count (≤6).
- `bmode` (packed low nibble): **0 ⇒ bottom row = 0x1000 (opaque blank)** (sub-menu, since the
  game-font letters are single 8×8 tiles). **Non-zero ⇒ bottom tile = top+bmode** (ring letters
  are 8×16 = a top tile plus a bottom tile at a fixed +0x0D offset for the alphabet, +0x05 for
  the condensed Attack blob).
- Palette: the packed hi-nibble is shifted to `pal<<12` and OR'd into each written cell, so
  sub-menu cells carry palette 4 (the stat-label palette) — needed because the borrowed
  game-font letters use pixel value 14, which is invisible under palette 0.

**Border truncation:** when a descriptor is a *ring* item (bmode≠0) **and** the box border
tile 0x314 is present at `top_off+0x10` (col 15), the write is truncated to **2 cells** — so
the ring labels on box rows read `Ma / Tr / Or` instead of the full word, matching the
Japanese (which shows only the first kanji there). 0x314 is present only when the box is open
(verified across all save-states), so this can't false-fire.

### 4.4 Ring vs sub-menu descriptors (the actual data)
Ring (guard = JP first-char tile, position-independent, bmode 0x0D/0x05):
Move@0x28E, Attack@0x40E, Magic@0x58E, Treat@{0x58E,0x70E,0x88E}, Order@{0x28E(frozen),0x70E,0x88E,0xA0E}.
Sub-menu (write@col11, guard@col12 via extra, bmode=0, palette 4):
`(0x596,0x4F1,DUEL) (0x716,0x691,RUSH) (0x896,0x611,HOLD) (0xA16,0x619,USER)`.

---

## 5. Glyph storage (the ring's custom letters)

The ring uses a **shared 8×16 half-width alphabet** rendered from `MxPlus_ToshibaSat_8x16.ttf`
(via `wordblob.py`), **36 tiles total** = 13 letters (M,o,v,e,a,g,i,c,T,r,t,O,d) as top+bottom
(26) + a condensed "Attack" blob (10). These are uploaded by the DMA loop into VDP2 char RAM
at cell codes 0x00C7…, i.e. the same 8-px-wide "half-width kanji cell" the menu uses.

**Storage locations (all inside LANG1, verified-safe zero regions only):**
- **9 gaps** at file offsets 0x60130, 0x601BC, 0x60248, 0x602D4, 0x60378, 0x60414, 0x604A0,
  0x6052C, 0x605B8 — each holds 3 tiles (96 B). These are trailing-zeros **after VDP2
  address tables** (preceded by 0x25E0xxxx constants), structurally safe.
- **Hook tail** 0x64C30…: the hook code + literals + descriptor table + DMA table + the
  remaining **9 tiles** all live here.

**BUDGET = 736 bytes (0x64C30–0x64F10), NOT 740.** There is a **live pointer 0x06074BFC at
file 0x64F10** that must not be overwritten. An earlier 740-byte build clobbered it. Current
hook is **732 bytes** (margin 4). Every build asserts the tail region is zero before writing
and re-checks the pointer after.

**DO NOT** repurpose other zero runs in LANG1 (0x61xxx/0x62xxx/0x63xxx, 0x6065C): they are
zero-*runs inside live byte-data tables* and corrupt graphics when written.

---

## 6. The font-in-VRAM discovery (how the sub-menu needs zero new storage)

LANG1 had no room for new glyph tiles for the sub-menu. Solution: the game keeps a **full
set of 8×8 capital letters permanently resident in VDP2 char RAM** (the same font the status
bar's "LV/AT/DF" uses). The sub-menu cells simply point at those existing tiles — no new
storage, no DMA.

**Letter → cell code (at the real charbase; verified stable across all 11 save-states):**
```
A=0x01 T=0x02 D=0x03 F=0x04 M=0x05 P=0x06 H=0x08 L=0x0A
R=0x29 C=0x36(alt) S=0x9A U=0x8B O=0x9F E=0x9C N=0x8D I=0x9E G=0x8F Y=0x99
```
(Also full sets at other slots.) Pixel value used is **14**, so cells must carry a non-zero
palette (we use 4). Two gotchas:
- The **'Y' tile is intrinsically two-tone** (pixel values 1 and 2 in one glyph) — it renders
  multi-coloured under any single palette. That's why 戦闘 is **DUEL**, not FRAY. Any word for
  the sub-menu must use only single-value tiles (checked with the histogram in the session log).
- Words cap at **4 letters** because the cursor occupies col 10 and the border col 15 must
  survive — cols 11–14. Hence DUEL/RUSH/HOLD/USER (GUARD/MANUAL don't fit).

---

## 7. Hard-won constraints (READ THIS BEFORE CHANGING ANYTHING)

1. **ALIGNMENT IS THE #1 KILLER (learned twice).** SH-2 `mov.w`/`mov.l` require even/4-aligned
   addresses; misaligned reads return **shifted garbage**, not a fault. This caused (a) the
   ring-freeze (a misaligned **DMA source table** — the "add r6,r2 → 0x25E2…" table landed at
   an odd address after the cursor-gate literals were added), and (b) a whole-menu corruption
   (a **7-byte-stride descriptor** put guard words at odd offsets → garbage guards matched
   everywhere). **Fix pattern:** fixed **even/4-aligned** table strides and pads; the current
   generator asserts `rwtbl`, `dmatbl`, and tailchunk alignment.
2. **The save-state VRAM +0x120 offset.** Kronos `.yss` stores VDP2 VRAM shifted +0x120 from
   CPU addressing. Reading letter tiles without accounting for it put every letter **9 slots
   off** → the "digits and kana" garbage. `memimg.py` exposes `vram_raw`; index it as
   `0x20120 + W*0x20` for the char at cell code `W`.
3. **Budget is 736 bytes** (live pointer at 0x64F10), not 740.
4. **Guard the injection**, and gate on **two cells** (single-cell signatures false-fire on
   boot). Rewrites must be gated too, not just the DMA.
5. **The debugger is decisive.** Both the freeze and the corruption were nailed by a Kronos
   Master-SH2 breakpoint at the hook entry (0x06074C30) reading the live register state —
   after static analysis had repeatedly mis-attributed the cause. Reach for it early.
6. **Verify the ring is byte-identical** after any hook change: `ring_ref_writes.json` holds
   the known-good per-unit cell writes; the generator's self-check simulates the write pass
   for every unit type and diffs against it. The current build is byte-identical for
   Soldier/Hawk Lord/Ledin/Volkoff/Frozen.

---

## 8. Byte-budget tricks used (so a reviewer knows they're intentional, not bugs)

The hook is at the ragged edge of 736 B; several micro-optimisations were needed:
- **Dropped redundant sign-extends** (`extu.w`/`extu.b`) where the source value is provably
  `< 0x8000` (guards/offsets) or `< 0x80` (packed/ncols): `mov.w`/`mov.b` sign-extension then
  equals zero-extension, so equality compares and address math are unaffected. Top-tile bytes
  are **not** in this set (they exceed 0x80) and keep their `extu.b`.
- **Guard delta reuses the palette nibble** (`extra = pal>>1`): ring pal=0 ⇒ delta 0; sub-menu
  pal=4 ⇒ delta 2. One field serves two purposes.
- **Skip-advance in a branch delay slot** (`bra NEXT` / `add …` in the slot).
- **Compute the frozen cursor cell** `BUF+0x28C` as `BUF+0x28E − 2` from a register already
  loaded, instead of a separate literal (saved a 2-byte word literal + reload).

---

## 9. The EN_46 merge & the "Undead" fix

- **Merge:** applied EN_45 to clean JP, confirmed LANG1/FONT unchanged & hook regions free,
  spliced the 3 changed LANG1 sectors (file-sectors 88/192/201 → LBA 290/394/403) with
  `cdecc.reframe` per sector, re-verified byte-perfect.
- **Typo:** "Undease" is stored in **Route-B half-width pair packing** (two ASCII halves
  composed into one unused-kanji glyph; see project `FONT_DAT_FORMAT.md` §6). The original
  build's pair→code map was lost with the sandbox, so it was **reconstructed** by rendering
  the Toshiba font's 95 half-glyphs and matching them against every **changed** kanji slot in
  EN_45's FONT.DAT — **1,370 pairs recovered** (`build_artifacts/pairmap_en45.json`). Lucky
  breaks: an **"ad" pair glyph already existed** (0xE658, verified by rendering), and
  **"Undead␣" is the same byte length as "Undease"** → pure in-place splice, no font change,
  nothing in SCEN moved. All **21** copies (global entry, duplicated per block) replaced;
  `Un de as e_` (E675 E84B E8FA E8F5) → `Un de ad ␣` (E675 E84B E658 8140).
- Full suite passed incl. xdelta round-trip reproducing the build bit-for-bit.

---

## 10. Tools in this package (`tools/`)

- **`build_ring_shared.py`** — the menu hook **generator**. Emits `hook_shared.bin` +
  `hook_shared_meta.json`. Contains the descriptor table, gate, write pass, DMA loop, all the
  constants above, and a self-check that diffs ring output vs `ring_ref_writes.json`. Start here.
- **`build_patch_shared.py`** — applies the hook into a clean-JP `.bin` copy: rewrites the
  copy_fn literal, writes the hook tail + 9 gap tiles, re-frames the 3 changed sectors
  (EDC/ECC via `cdecc`), and round-trips the resulting xdelta. Asserts tail-zero & alignment.
- **`wordblob.py`** — renders the 8×16 half-width Toshiba glyphs into 8×8 4bpp tiles for the ring.
- **`cdecc.py`** — Mode-1/2352 EDC + P/Q ECC re-framing. `reframe(sector2352, lba)`. NOTE: call
  it with a plain `import cdecc` (double-`exec` via importlib corrupts its `_F/_B` GF tables).
- **`memimg.py`** — loads a Kronos `.yss`; exposes `hwram`, `lwram`, `vram_raw` (remember the
  +0x120 VRAM offset). Byte-swapped HWRAM helper `hw(st,cpu,n)`.

`build_artifacts/`: current `hook_shared.bin`(+meta), the **known-good reference** hook
(`hook_working_ref.*`), `ring_ref_writes.json`, `pairmap_en45.json`, and both shipped xdeltas.
`reference/`: rendered font atlases used to identify letters (labeled cell codes).

---

## 11. What still needs doing

**Story text**
1. **Entry-4 place names** (SCEN entry 4, ~239 strings) — the **last remaining story-text
   task**. Global entry (duplicate across all 21 blocks). Use `scen_codec.py` (in the project
   toolkit) + the Route-B encoder; the reconstructed `pairmap_en45.json` gives the existing
   pair→code inventory to reuse before allocating new slots.

**In-battle UI polish (optional)**
2. **Summon** command (Volkoff and other summoners) is still Japanese — add a ring descriptor
   (guard = 召's tile code; needs a "Summon"/"Call" glyph set, and Summon can be at slot4).
3. **Sub-menu wording** is constrained to 4 letters by the cursor+border. DUEL/RUSH/HOLD/USER
   are the current choices; if a 5th cell can be reclaimed (e.g. by moving the cursor render),
   GUARD/MANUAL become possible. Low priority.
4. **Sub-menu letter size**: uses the game's 8-px status-bar caps (shorter than the ring's
   16-px letters). Acceptable and shipped, but a custom 8×16 cap set would match better (costs
   glyph storage — none free; would need the class-name-style font expansion).

**Bigger, already-scoped elsewhere**
5. **In-game class names** (bottom status bar + 16×16 class/status panel). This is **solved in
   the project's class-name track** (`inject_AZ.xdelta`, `docs/in_battle_ui/CLASS_NAMES.md`:
   bottom bar via glyph injection + `bbtable`; panel via `panelTABLE`→SJIS→FONT.DAT) but is
   **built on clean-JP LANG1 and not yet merged into the story build**. Merging needs the same
   in-place LANG1 splice used for the menu hook — but **check for byte-range collisions** with
   the menu hook's tail (0x64C30–0x64F10) and 9 gaps first.

**Verification owed**
6. Final **in-game spot-check of EN_46** (story unchanged, ring+sub-menu as approved, "Undead"
   line). Everything is verified offline; only the live confirmation is outstanding.

---

## 12. Quick constants reference
```
copy_fn                 0x0604A26C   (call-site literal @ file 0x2C0B8 / CPU 0x0603C0B8)
hook entry              0x06074C30   (file 0x64C30)
hook budget             736 B (0x64C30..0x64F10); live pointer 0x06074BFC @ 0x64F10
LANG1 load base         0x06010000   (file_off = cpu - 0x06010000); image ends file 0x64F14
menu staging buffer     0x060765F8   (BUF); row stride 0x80; item slots 0x180 apart
VRAM char base          0x25E20000   (cell W -> +W*0x20);  save-state raw: 0x20120 + W*0x20
ring guards             Move 0x5CC  Attack 0x5D4  Magic 0x5D8  Treat 0x5E8  Order 0x428
cursor / blank / border 0x306F / 0x1000 / 0x314
submenu guards          戦 0x4F1  突 0x691  防 0x611  手 0x619   (all at col 12)
9 safe glyph gaps       0x60130 0x601BC 0x60248 0x602D4 0x60378 0x60414 0x604A0 0x6052C 0x605B8
game-font letter cells  A01 T02 D03 F04 M05 P06 H08 L0A R29 S9A U8B O9F E9C N8D I9E G8F  (pal 4)
```
