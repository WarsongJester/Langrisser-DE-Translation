> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> In-battle UI research — merged into docs/in_battle_ui/MENU_CHROME.md and IMG_DAT_CODEC.md.
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# Langrisser I (Sega Saturn, Dramatic Edition) — In-Battle UI / Menu Rendering Research

Authoritative notes for the in-battle command menu, option/save menu, and the IMG.DAT
graphics codec. Written so the command-menu work can resume later without re-deriving
anything. Companion to `LANGRISSER1_EN_HACKING_REFERENCE.md` (the shipped text work).

---

## 0. TL;DR

- **Option / save menu** = ordinary **SJIS text in LANG1.BIN**, rendered through the
  standard font path. LANG1.BIN loads verbatim, so it is directly editable. **This is the
  tractable target and is being worked now.**
- **Command menu (移動/攻撃/魔法/治療/指令)** = the game's **custom in-battle rendering**
  (NOT SJIS, NOT a VDP2 pre-rendered strip, NOT VDP1 text sprites). Same hard family as the
  in-game class names. Translating it is a research-grade effort (custom font + renderer,
  possibly the IMG.DAT codec). **Deferred.**
- **Key enabler discovered:** LANG1.BIN is loaded **byte-for-byte verbatim** at
  `0x06010000` (verified against the disc file across the whole code region, in both a
  title-load and an in-battle dump). => **code and data patches to LANG1.BIN are reliable.**
  This also reopens the previously-deferred class-name problem to a code-patch approach.

---

## 1. Memory dumps on hand (from Mednafen, via Tim)

| File | Region (base) | Captured when | Notes |
|------|---------------|---------------|-------|
| `VDP2VRAM.bin` | VDP2 VRAM 0x05E00000 (512KB) | in battle, **option** menu open | has bottom-bar font @0x20000, kanji font, pre-rendered prompts (セーブしますか, はい/いいえ) |
| `HIGHWORKRAM.BIN` | High Work RAM 0x06000000 (1MB) | LANG1 title/boot load | LANG1.BIN code @0x10000 + work RAM |
| `LOWWORK.BIN` | Low Work RAM 0x00200000 (1MB) | title/boot load | **IMG.DAT archive loaded here** (header @0x00200000, font asset @0x0020033C) |
| `VDP1VRAM.bin` | VDP1 VRAM 0x05C00000 (512KB) | title/boot load | mostly framebuffer/cmd data |
| `SH-2ExternalBus.bin` | whole external bus (128MB) | title/boot load | includes VDP/SCU register space (title state) |
| `highworkinbattlemenu.bin` | HWRAM 0x06000000 (1MB) | in battle, **command** menu open | LANG1.BIN still verbatim @0x10000 |
| `vdp2inbattlemenu.bin` | VDP2 VRAM (512KB) | in battle, command menu open | font + kanji + prompts; **no command-menu strip** |
| `VDP1commandmenu.bin` | VDP1 VRAM (512KB) | in battle, command menu open | command list = battlefield unit sprites + portrait |

Saturn address mirrors: cached `0x00xxxxxx/0x06xxxxxx/0x05Exxxxx`, uncached
`+0x20000000` (so `0x20200000`=archive, `0x25E20000`=VDP2 VRAM). Mask with `& 0x07FFFFFF`.

---

## 2. IMG.DAT graphics codec (the compressed asset archive)

- **IMG.DAT**: disc LBA 134794, 514,624 B. Header = 207-entry big-endian uint32 offset
  table (`[0]=0x33C [1]=0xCF2 [2]=0x178A ...`). Every asset begins with byte `0xC0`.
- Loaded whole into **Low Work RAM 0x00200000** at runtime (font asset at 0x0020033C).
- **Asset 0 = bottom-bar font** (2486 B compressed → 8192 B at VDP2 VRAM 0x20000). Confirmed
  by rendering: `A T D F M P V H P L`, digits, katakana, `TURN`, `SCEAIO`, bold digits.

### Codec = async STREAMING Huffman-LZ pipeline (not a one-shot function)
This is why every LZSS / RLE / 16-bit-control-word model failed past the trivial 33-byte
leading-zero run, and why the literals are bit-misaligned (variable-length codes).

Stage map (runtime addresses; LANG1 file offset = addr − 0x06010000):
- **0x0604A4D8** — per-call decode state machine (6 states; jump table at 0x0604A524,
  cases 1..6 → 0x0604A530 / 0x0604A54E / 0x0604A562 / ...). State byte @ `0x060A69CE`.
  Each invocation decodes ONE symbol.
- **0x0604AD3C** — Huffman symbol decoder. Tables: `0x060775F8`, `0x0607763A`; per-symbol
  8-byte descriptor table `0x06077638`; "last symbol" byte `0x060A69CF`.
- **0x060569F8 → 0x060579A0** — packs (symbol + 3 descriptor bytes) into a 16-byte record
  and enqueues into a **7-slot ring at 0x060776EC** (busy flag `0x060776C8`).
- **a separate async consumer** drains the ring and emits the actual output bytes (the LZ
  back-end / pixel writer). **Not located.** Likely CPU writes; runs in another context.

### Load path (fully mapped)
```
orchestrator 0x0601DED0
  sets r8=0x20200000 (archive), r9=loader 0x06011850, r5=VRAM dest
  -> loader 0x06011850 (resolves asset via 0x06011704; computes size)
     -> enqueuer 0x0604A238  pushes {cmd=2, dest, src, size} to a queue
        -> task spawner 0x0604A308  builds a task, then BUSY-WAITS for completion
           (loop at ~0x0604A37C: jsr <done?>; tst; bf loop)  <-- decode IS synchronous-ish
```
The busy-wait means decode completes cooperatively (good for emulation in principle), but
the path is entangled with the task scheduler + CD runtime.

### Orchestrator asset → VRAM destination map (LANG1 boot/common assets)
| asset | dest (uncached) | VDP2 VRAM offset |
|------:|-----------------|------------------|
| 1 | 0x25E26000 | 0x26000 |
| 0 (font) | 0x25E20000 | 0x20000 |
| 2 | 0x25C70000 | VDP1 0x70000 |
| 5 | 0x25E22000 | 0x22000 |
| 6 | 0x25E24000 | 0x24000 |
| 29 | 0x25E28000 | 0x28000 |
| 30 | 0x25E2A000 | 0x2A000 |
| 31 | 0x25E2C000 | 0x2C000 |

There are **21 call sites** of loader 0x06011850 in LANG1 (literal-pool refs at 0x06010bac,
0x06010d58, 0x060153a0, 0x0601a654, 0x0601ac44, 0x0601b940, 0x0601de5c, 0x0601df54, …) —
title, map, battle, each menu. The battle-menu loads are among these (not individually
identified yet).

### Separate synchronous LZSS-style decompressor in LANG1 (different codec!)
At **0x060115A0**: stores output ptr → `0x060116E0`, src → `0x060116E4`; bit-reader
`0x0601139C` (reads a byte, tests bit 7, shifts left to consume — MSB-first); helper fns
`0x06011544`, `0x060113EC`, `0x06011470`. Decompresses to a HWRAM work buffer (current
ptrs `0x06075028`/`0x0607502C`), NOT to VRAM — so this is for some other data, not the
VRAM graphics. Listed here only to avoid confusing it with the IMG.DAT codec.

### SH-2 emulator (built this session)
`/home/claude/lang/sh2emu.py` — a working big-endian SH-2 interpreter (validated: correct
memory reads, runs the real code). Memory map backs the dumps (LOWWORK, HWRAM, VDP1/VDP2).
**Limitation:** running the codec cold from a static snapshot wanders into wrong code
(async/CD runtime not present) — it needs a *synchronous per-asset decode entry* isolated
and the scheduler stubbed. Reusable foundation if we ever edit IMG.DAT directly. Not on the
critical path for either menu via the runtime-overlay approach.

---

## 3. Render-path analysis per UI element

### Option / save menu → SJIS text in LANG1.BIN (TRACTABLE — current focus)
- Confirmed SJIS strings inside LANG1.BIN:
  - `セーブできません` ("cannot save") @ file **0x2B4E8**
  - `データが壊れています` ("data is corrupted") @ file **0x2B4FC**
  - `セーブ` present (as prefix of the above).
- Rendered through the standard SJIS→font path. Editable on disc thanks to verbatim load.
- TODO when working it: confirm exactly which strings are the menu *items*
  (セーブ/ロード/勝利条件/ゲーム設定/フェイズ終了) vs system messages, find their table/structure,
  confirm which font the in-battle renderer uses (kanji font in VRAM vs FONT.DAT), and
  whether English uses full-width or the half-width pair-packing technique.

### Command menu (移動/攻撃/魔法/治療/指令) → custom rendering (HARD — deferred)
Eliminated, with evidence:
- **Not SJIS**: none of 移動/攻撃/魔法/治療/指令 appear as SJIS in LANG1.BIN or in the
  in-battle HWRAM dump (RAM). (セーブ does; the command kanji do not.)
- **Not a VDP2 pre-rendered strip**: every bank of the in-battle VDP2 dump was rendered;
  the menu words are not present as a contiguous bitmap. (Pre-rendered *prompts* like
  セーブしますか and English `EXIT` DO appear — proof the engine mixes pre-rendered English.)
- **Not VDP1 text sprites**: parsed the VDP1 command list (32-byte commands from VRAM 0).
  The 9 sprite commands are the **battlefield**: unit figures (24×24, textures
  0x10000/0x10780/0x10F00/0x11680) arranged on the map + a 48×48 portrait at (112,32).
  The cross of positions around (235,110) is the unit/cursor layer, not menu text.

VDP1 command list parsed (command-menu moment), for reference:
```
cmd2  type0 tex=10000 24x24 colr=0070 pos=(163,86)
cmd3  type0 tex=10780 24x24 colr=0070 pos=(307,134)
cmd4  type0 tex=10f00 24x24 colr=0070 pos=(235,110)   center
cmd5  type0 tex=11680 24x24 colr=0080 pos=(211,110)   left
cmd6  type0 tex=11680 24x24 colr=0080 pos=(259,110)   right
cmd7  type0 tex=11680 24x24 colr=0080 pos=(235,86)    top
cmd8  type0 tex=11680 24x24 colr=0080 pos=(235,134)   bottom
cmd9  type0 tex=10000 24x24 colr=7070 pos=(72,192)
cmd10 type0 tex=78000 48x48 colr=7200 pos=(112,32)    portrait
cmd11 END
```
**Conclusion:** the command menu is drawn by the custom in-battle text system — most likely
a **VDP2 tilemap assembled from the kanji font** (the kanji 移動… exist as tiles in the
in-VRAM kanji font block ~0x2A000), or the **custom code-page/font/renderer** used by the
class names. This is the same hard problem family as the in-game class names
(see `LANGRISSER1_EN_HACKING_REFERENCE.md` §9).

### Class names (status bar + class-change screen) — prior finding, related
Custom non-SJIS code page → custom font(s) → custom renderer(s). Strings in LANG1.BIN
(main pool 0x617AC–0x61C2A; 255-entry pointer table at 0x61C2C). Status-bar font in VDP2
VRAM @0x20000 has only a partial Latin set (missing B F H J K L V W Y, most lowercase);
its source is compressed/unidentified. The 16×16 class-change renderer crashes on
out-of-range (ASCII) codes. Documented as deferred.

---

## 4. Concrete next steps for the COMMAND menu (when resumed)

Goal: get English where 移動/攻撃/魔法/治療/指令 are. Three viable angles, easiest first:

1. **Determine the exact draw mechanism.** Find the routine that runs on command-menu open
   in LANG1 (battle HWRAM `highworkinbattlemenu.bin` has the code). Look for: a VDP2
   pattern-name-table write (tilemap of kanji-font tiles) vs a custom-renderer call vs an
   IMG.DAT decompress to VRAM. This decides everything.
   - To find the VDP2 tilemap location, a **VDP2 register dump at the command-menu moment**
     (or reading VDP2 regs at 0x25F80000 from a full-bus dump taken then) gives the
     pattern-name-table + character-pattern base addresses; then the tilemap can be read
     and the kanji→tile mapping recovered.

2. **Runtime overlay (avoids codec/custom-renderer reversing).** Because LANG1 loads
   verbatim, inject a small SH-2 hook after the menu draws that blits English glyphs into
   the menu's VRAM location. Requires (a) the draw mechanism + VRAM target from step 1, and
   (b) authored English glyphs. Works regardless of the original render path.

3. **If it shares the class-name custom font/renderer:** solve once, fixes both. Trace the
   custom renderer live (Mednafen breakpoint where it reads the menu/class string), get the
   code→glyph mapping, patch it to accept Latin, and add the missing Latin glyphs to the
   custom font (locate its compressed source first).

Useful capture to advance it: a **VDP2 register dump** (or full external-bus dump) taken at
the command-menu moment, to locate the VDP2 tilemap/pattern data.

---

## 5. Key constants / addresses (quick reference)

```
LANG1.BIN          : disc LBA 202; loads VERBATIM at runtime base 0x06010000 (1MB HWRAM)
                     (file offset = runtime addr - 0x06010000)
IMG.DAT            : disc LBA 134794, 514,624 B; 207-entry BE u32 offset table; assets start 0xC0
                     loaded to Low Work RAM 0x00200000 (uncached mirror 0x20200000)
                     font asset 0 @ archive 0x33C -> RAM 0x0020033C ; decompresses to VDP2 0x20000

Codec stages (runtime):
  decode SM        0x0604A4D8   state byte 0x060A69CE ; jump table 0x0604A524
  huffman symbol   0x0604AD3C   tables 0x060775F8 / 0x0607763A ; descriptors 0x06077638
  record enqueue   0x060569F8 -> 0x060579A0 ; ring @0x060776EC (7x16B) ; busy 0x060776C8
  load orchestr.   0x0601DED0 ; loader 0x06011850 ; resolver 0x06011704 ; enqueuer 0x0604A238
  task/busy-wait   0x0604A308 (waits ~0x0604A37C)
  (separate LZSS)  0x060115A0 ; bit reader 0x0601139C ; -> HWRAM buffer (not VRAM)

Option/save SJIS in LANG1 (file offsets):
  セーブできません 0x2B4E8 ; データが壊れています 0x2B4FC

VDP1 (battle): command list at VRAM 0, 32B/command; menu-moment list = battlefield units
  (textures 0x10000/0x10780/0x10F00/0x11680, 24x24, 4bpp) + portrait 0x78000 48x48.

Tools: /home/claude/lang/sh2emu.py (SH-2 BE interpreter, validated; codec-cold-run limited)
```
