> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> FINAL class-name solution — content merged verbatim into docs/in_battle_ui/CLASS_NAMES.md (kept here as the detailed original).
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# Langrisser I (Sega Saturn, *Dramatic Edition*) — In-Battle Class / Unit-Name Text System
## Hacking Hand-off Notes

This document is a self-contained hand-off for the **in-battle class-name text system** —
the custom, non-SJIS text path that draws class and unit names on (1) the bottom status bar
and (2) the 16×16 status / class-change panel. Earlier project notes
(`LANGRISSER1_EN_HACKING_REFERENCE.md` §9) listed this as "deferred / not done." It is now
**solved**: both renderers display English, all 26 uppercase letters are available, and the
bottom-bar text has been recolored white to match the panel. Confirmed in-game (build
`Langrisser1_inject_AZ.xdelta`, test strings "HAWK" and "JOY").

It assumes familiarity with the main reference (disc layout, SCEN/FONT formats, the Route-B
dialogue system). Everything here is about the *separate* class-name system, which does **not**
use SCEN.DAT or the dialogue font.

---

## 0. TL;DR

- Class/unit names are null-terminated strings in **LANG1.BIN** in a **custom 1-byte code page**
  (not SJIS). One string feeds **two independent renderers**.
- **Bottom status bar**: byte → `bbtable` → glyph index → an **8×8 4bpp font in VDP2 VRAM at
  offset 0x20000**. That font is runtime-decompressed (source compressed; not statically
  editable) and is **missing J K W Y**. Fix = inject those glyphs into blank VRAM slots at
  runtime via a CPU hook; map them in `bbtable`.
- **16×16 panel** (status / class-change): byte → `panelTABLE` → **full-width SJIS** → drawn
  via **FONT.DAT**, which already contains every Latin letter. Needs no glyph work.
- **Color**: bottom-bar text color = `CRAM[palette][glyph_fg_nibble]`. Letters use a *mix* of
  nibbles (1/2/14). White recolor = write `0x7FFF` into the bar palette's green entries in CRAM
  (done in the same hook).
- All edits are in LANG1.BIN, built against the **clean Japanese disc** (LANG1 @ LBA 202), then
  spliced in-place and shipped as an xdelta3 patch.

---

## 1. Where the class strings live (LANG1.BIN)

LANG1.BIN: 413,460 bytes (0x64F14), loaded to **CPU 0x06010000**. `file_off = CPU − 0x06010000`.

- **Class name string pool**: null-terminated strings, custom 1-byte encoding.
  - Main pool (basic classes: Fighter, Knight, …, Lord): file **0x617AC–0x61C2A**.
  - Second region (advanced/boss: Vampire Lord, Necromancer, Phoenix, …): **~0x621A0+**.
- **Class pointer table**: a **255-entry, 4-byte big-endian** table at file **0x61C2C**
  (classID → string CPU address, base 0x06010000; contains duplicates). These strings load to
  **HWRAM 0x060717AC** at runtime; both renderers read them from there.
- The **"Lord" string** (Ledin's class, original bytes `DB B0 C4 DE 00 00` = ﾛｰﾄﾞ) sits at file
  **0x6181C** and was used as the in-place test target (overwritten with "VANDAL", "HAWK",
  "JOY" during bring-up — see §9). Same length or shorter avoids relocation.

> The custom code page is **not** ASCII and **not** SJIS. The renderers translate each byte
> through their own lookup (`bbtable` / `panelTABLE`). To emit English you can either (a) write
> ASCII letters into the strings and make the tables map ASCII→glyph/SJIS (the approach taken
> here — `bbtable['A']`, `panelTABLE` idx for 'A', etc. are set up), or (b) keep the original
> code page and remap. Approach (a) is in place and proven.

---

## 2. Renderer A — bottom status bar (half-width, custom 8×8 font)

### 2.1 Code path
- Class-name **character loop**: CPU **0x0601C002–0x0601C08E** inside the function whose
  prologue is at file **0xBFD0** (CPU 0x0601BFD0):
  `mov.l r8/r9/r10/r11/r14,@-r15 ; sts.l pr,@-r15 ; mov r15,r14 ; mov r5,r0 ; mov r6,r9 …`
- Per character: byte → conversion → glyph index → draw. The **glyph-draw routine** is at
  **0x0601BED8**; it writes a VDP2 tilemap entry `= (r7<<12) | glyph_index` into the bar
  tilemap (HWRAM base **0x060989D0**, DMA'd to VRAM). The loop sets **r7 = 1** (palette 1).
- Out-of-range codes here **do not crash** — they just draw wrong glyphs.

### 2.2 The conversion (`bbtable`)
Clean firmware computed the glyph index arithmetically (thresholds, byte−112/−53/−30, a couple
of specials, and the 0xDE/0xDF combining-mark paths). That arithmetic path was **replaced** with
a flat table lookup:

- **Code patch @ file 0xC034** (6 bytes + a literal), keeping the 0xDE/0xDF combining paths intact:
  ```
  0xC034  d1 02   mov.l @(2,pc),r1     ; r1 = const@0xC040 = 0x06074DB0  (bbtable base)
  0xC036  00 1c   mov.b @(r0,r1),r0    ; r0 = bbtable[byte]
  0xC038  60 0c   extu.b r0,r0
  0xC03A  a0 1f   bra 0x0601C07C       ; -> draw-setup (skips old arithmetic)
  0xC03C  00 09   nop (delay)
  0xC03E  00 09   nop
  0xC040  06 07 4d b0   .long 0x06074DB0   (bbtable base literal)
  ```
- **`bbtable`** = 256 bytes at file **0x64DB0** (CPU 0x06074DB0). `glyph = bbtable[byte]`.
  - Non-letter bytes keep the original-formula values (so katakana/symbols/digits still render).
  - `byte 0x20` (space) → glyph 0x40 (64, a blank tile).
  - **ASCII A–Z** (0x41–0x5A) are mapped to font slots (see §2.4).

### 2.3 The font in VRAM
- Located at **VDP2 VRAM offset 0x20000** = CPU **0x25E20000** (cached) / 0x05E20000.
- Format: **8×8 pixels, 4 bits/pixel = 32 bytes/tile**. `glyph slot N` → `0x25E20000 + N*32`.
  Row layout: 4 bytes/row, high nibble = left pixel of each pair.
- **Runtime-decompressed from IMG.DAT.** The decompressor takes its destination as a parameter
  (it does not reference 0x25E20000 as a literal), so it is not findable by literal-scan and was
  **not** reversed. The font is **not present as plain bitmap anywhere on disc** → it cannot be
  edited statically. Three sites load the 0x25E20000 base (file 0xDEEE, 0x2BB86, and the
  0x3FA54/0x3FAB0/0x3FB14 cluster); the 0x3FAxx cluster is VDP2 map/cell-address **setup**, not
  the pixel decompressor.
- This is why glyph fixes are done by a **runtime VRAM write** (§4), not by editing the font on
  disc.

### 2.4 Verified font slot map (8×8 tiles in VRAM 0x20000)
Rendered and read directly from a Kronos VDP2 dump. **Uppercase letters present natively**
(slot numbers as currently mapped in `bbtable`):

```
A=1  B=31 C=155 D=3  E=156 F=4  G=143 H=8  I=160 L=10 M=5
N=141 O=161 P=6 R=140 S=154 T=138 U=139 V=7  Q=42  X=56  Z=44
```
- `Q` (slot 42), `X` (slot 56), `Z` (slot 44) **are present** — an earlier sweep wrongly listed
  them missing, and had `Z` pointed at slot 45 (which is actually a **C** glyph). These three
  mappings were corrected.
- Digits 0–9 live around slots 18–27 (a 2nd bold digit set sits at 144–169 — **not letters**).
- Katakana occupy slots ~64–137.
- **Truly missing (no glyph anywhere): J, K, W, Y.** These are the only letters that need
  injection. For *class names* specifically only **K** (Knight) and **W** (Hawk/Warlock) are
  required; J and Y are for unit/character names.
- 162 blank (all-zero) tiles exist; injection uses slots **200–203**.

---

## 3. Renderer B — 16×16 status / class-change panel

### 3.1 Code path
- Class-byte → SJIS **converter** at CPU **0x0602B270**: builds a full-width SJIS string into an
  output buffer (`r5`), then the standard full-width text drawer renders it via **FONT.DAT**.
  Per byte:
  - `0x20` → full-width space (0x8140);
  - `0x30–0x39` (digit) → SJIS `byte + 0x821F`;
  - else `idx = (byte + 0x60) & 0xFF`, `SJIS = panelTABLE[idx]`.
- Out-of-range codes here historically **crashed** (corrupted indirect call). Because we now feed
  it valid table entries for every letter, that path is never exercised.

### 3.2 `panelTABLE`
- 192-entry **big-endian u16** table at file **0x64C30** (CPU 0x06074C30). Repointed from the
  original 0x06072E78 by patching the two base-pointer constants:
  - file **0x1B316**: `2E 78 → 4C 30`  (high-byte pointer → 0x06074C30)
  - file **0x1B31A**: `2E 79 → 4C 31`  (low-byte pointer  → 0x06074C31)
- Entries: original katakana copied for idx 0x00–0x41; **all A–Z mapped to SJIS Latin**
  (`'A' idx 0xA1 → 0x8260`, `'H' → 0x8267`, `'K' → 0x826A`, `'W' → 0x8276`, … `'Z' idx 0xBA →
  0x8279`); remaining entries = 0x8140 (space) filler.
- **FONT.DAT already contains every Latin glyph** (full-width ASCII at S1 slots 17–42), so the
  panel renders any letter correctly with **no glyph injection**. Panel side is fully done.

---

## 4. Glyph injection (bottom-bar font) + white recolor — the runtime hook

Because the bar font is decompressed at runtime and lacks J/K/W/Y, the fix is a **CPU hook** that,
every time the class-name function runs, (a) copies the four missing glyph bitmaps from LANG1 into
blank VRAM slots, and (b) writes white into the bar palette. Writing every call (idempotent) means
the glyphs survive any font re-decompress; the cost is trivial (128 bytes + 2 CRAM words).

### 4.1 Glyph data (in LANG1 free space)
8×8, 4bpp, foreground nibble 0xE. 32 bytes each.

| Letter | VRAM slot | VRAM dest      | LANG1 source (file / CPU) |
|--------|-----------|----------------|---------------------------|
| K | 200 | 0x25E21900 | 0x64EB0 / 0x06074EB0 |
| W | 201 | 0x25E21920 | 0x64ED0 / 0x06074ED0 |
| J | 202 | 0x25E21940 | 0x64EF0 / 0x06074EF0 |
| Y | 203 | 0x25E21960 | 0x62866 / 0x06072866 |

K/W/J are contiguous (one 96-byte copy); Y is in a separate zero-run (one 32-byte copy).

### 4.2 The hook (file 0x62970, CPU 0x06072970)
Preserves r1–r3, performs two VRAM copies, two CRAM writes, runs the three displaced prologue
instructions, then `rts`:

```
06072970  mov.l r1,@-r15
06072972  mov.l r2,@-r15
06072974  mov.l r3,@-r15
06072976  mov.l 0x60729b0,r1      ; SRC1 = 0x06074EB0  (K,W,J)
06072978  mov.l 0x60729b4,r2      ; DST1 = 0x25E21900
0607297A  mov   #48,r3            ; 48 words = 96 bytes
0607297C  mov.w @r1+,r0           ; loop1
0607297E  mov.w r0,@r2
06072980  add   #2,r2
06072982  dt    r3
06072984  bf    0x607297c
06072986  mov.l 0x60729b8,r1      ; SRC2 = 0x06072866  (Y)
06072988  mov.l 0x60729bc,r2      ; DST2 = 0x25E21960
0607298A  mov   #16,r3            ; 16 words = 32 bytes
0607298C  mov.w @r1+,r0           ; loop2
0607298E  mov.w r0,@r2
06072990  add   #2,r2
06072992  dt    r3
06072994  bf    0x607298c
06072996  mov.w 0x60729c8,r0      ; WHITE = 0x7FFF
06072998  mov.l 0x60729c0,r1      ; CR2  = 0x25F00024  (palette 1, nibble 2)
0607299A  mov.w r0,@r1
0607299C  mov.l 0x60729c4,r1      ; CR14 = 0x25F0003C  (palette 1, nibble 14)
0607299E  mov.w r0,@r1
060729A0  mov.l @r15+,r3
060729A2  mov.l @r15+,r2
060729A4  mov.l @r15+,r1
060729A6  mov   r15,r14           ; displaced prologue instr 1
060729A8  mov   r5,r0             ; displaced prologue instr 2
060729AA  mov   r6,r9             ; displaced prologue instr 3
060729AC  rts
060729AE  nop
; literal pool (4-byte aligned):
060729B0  .long 0x06074EB0   060729B4 .long 0x25E21900
060729B8  .long 0x06072866   060729BC .long 0x25E21960
060729C0  .long 0x25F00024   060729C4 .long 0x25F0003C
060729C8  .word 0x7FFF
```

### 4.3 Trampoline (function entry)
The hook is too far for a direct branch and the literal pool around the function is fully packed,
so the trampoline borrows a **dead-code slot**: the `conv` patch's `bra` (§2.2) made the old
arithmetic path at **0xC044–0xC07B unreachable**, so the hook address is stored there.

- **Hook-address literal @ file 0xC044** = `06 07 29 70` (0x06072970).
- **Trampoline @ file 0xBFDC** (overwrites the 3 original prologue instructions
  `mov r15,r14 / mov r5,r0 / mov r6,r9`, which the hook re-executes):
  ```
  0xBFDC  d0 19   mov.l @(25,pc),r0   ; -> literal @0xC044 = hook
  0xBFDE  40 0b   jsr @r0
  0xBFE0  00 09   nop
  ```
  `jsr` return address is 0xBFE2 (the original next instruction); the original `pr` was already
  saved to the stack one instruction earlier, so clobbering `pr` here is safe.

---

## 5. Color / palette model

- **CRAM** at CPU **0x25F00000**: 16 palettes × 16 colors, **RGB555 big-endian**
  (`w=(b0<<8)|b1; r=w&0x1F; g=(w>>5)&0x1F; b=(w>>10)&0x1F; white=0x7FFF`).
  Palette P entry N → CRAM offset `(P*16 + N)*2`.
- Displayed bar text color = **`CRAM[r7][glyph_foreground_nibble]`**. The bar loop uses **r7 = 1**.
- **Letters do not share one foreground nibble** — measured: nibble **14** (A, Z), nibble **2**
  (L, Q), nibble **1** (G, and all digit glyphs). So a single-entry palette edit cannot recolor
  every letter uniformly.
- **Palette 1** (clean): nibble 1 ≈ white (30,30,30); nibbles 2 and 14 = green (11,31,10).
- **White recolor used**: write `0x7FFF` to **palette 1 nibble 2 (0x25F00024)** and **nibble 14
  (0x25F0003C)**. Nibble 1 is already ~white, so every palette-1 letter becomes white. Stat
  **numbers** use a *different* palette, so they stay green. Net in-game result (confirmed): class
  + unit name + stat letter-labels render **white**, stat numbers green — and the bar white
  matches the panel's white class name.
- The bar palette is loaded dynamically (RAM buffer ~0x06075060, populated by a fade routine
  @0x06013EA0; the raw palette is **not** present on disc, compressed). Hence the recolor is a
  **runtime CRAM write**, not a static edit.
- **Tooling note:** the **Mednafen** debugger cannot read CRAM (its 0x5F00000 view is a TODO
  placeholder). Use **Kronos** to dump CRAM for palette work.

### Optional refinement (not done)
To whiten **only** class + unit name and leave the stat letter-labels green (exact panel match),
give the bar loop its own palette: set up a spare palette with white at nibbles 1, 2, **and** 14
(CRAM writes), and change the loop's `mov #1,r7` to that palette number. Labels are drawn by a
separate routine and would keep palette 1 (green). Deferred; current all-letters-white was
accepted in testing.

---

## 6. Complete list of LANG1 byte changes

| File offset | CPU | What | Bytes (→) |
|-------------|-----|------|-----------|
| 0xBFDC | 0x0601BFDC | trampoline (jsr hook) | `D0 19 40 0B 00 09` |
| 0xC034 | 0x0601C034 | char-loop conversion → bbtable lookup + bra | `D1 02 00 1C 60 0C A0 1F 00 09 00 09` |
| 0xC040 | 0x0601C040 | bbtable base literal | `06 07 4D B0` |
| 0xC044 | 0x0601C044 | hook-address literal (in dead code) | `06 07 29 70` |
| 0x1B316 | 0x0602B316 | panelTABLE base hi-ptr | `4C 30` |
| 0x1B31A | 0x0602B31A | panelTABLE base lo-ptr | `4C 31` |
| 0x6181C | 0x0607181C | **test** class string (Lord) | `"JOY\0\0\0"` (restore real class here) |
| 0x62866 | 0x06072866 | Y glyph (slot 203), 32 B | 8×8 4bpp |
| 0x62970 | 0x06072970 | hook code + literals, ~0x5A B | see §4.2 |
| 0x64C30 | 0x06074C30 | panelTABLE (192 × u16) | katakana + A–Z→SJIS |
| 0x64DB0 | 0x06074DB0 | bbtable (256 B) | formula + A–Z→slots |
| 0x64EB0 | 0x06074EB0 | K,W,J glyphs (slots 200–202), 96 B | 8×8 4bpp |

LANG1 free space used: the **736-byte zero-run at 0x64C30** holds panelTABLE (≈0x64C30–0x64DB0),
bbtable (0x64DB0–0x64EB0) and K/W/J glyphs (0x64EB0–0x64F10); Y glyph in the isolated zero-run at
**0x62866**; hook in the zero-run at **0x62970**; hook-address literal in the **dead arithmetic
code at 0xC044**. No code/data the game uses is overwritten (the 0x62866/0x62970 runs are zero
padding; 0xC044 is unreachable after the conv patch).

---

## 7. Build / splice / ship

Everything is built **against the clean Japanese disc** (`…/LANGRISSER_DRAMATIC_EDITION.bin`),
where LANG1.BIN is at **LBA 202** (MODE1/2352: user data at `sector*2352 + 16`, 2048 B/sector;
LANG1 byte N → sector `202 + N//2048`).

Pipeline (scripts in `/home/claude/lang/`):
1. `build_inject.py` — applies all §6 edits to `work_LANG1.bin` (the recovered working LANG1) →
   `out_LANG1.bin`.
2. Splice: copy clean disc → temp; for each changed LANG1 sector, overwrite the 2048-byte user
   region and re-frame with `cdecc.reframe(sector2352, lba)` (rewrites sync/header/EDC/ECC).
3. `xdelta3 -e -9 -f -s <clean.bin> temp.bin <out>.xdelta`.
4. Validate: re-apply the xdelta, re-extract LANG1, assert it equals `out_LANG1.bin`; spot-check
   EDC on changed sectors.

Verification helpers:
- `sh2dis.py <fileoff_hex> <N_instr> [label]` — SH-2 BE disassembly (Capstone). Reads
  `extracted/LANG1.BIN`; `sed`-swap the filename to disassemble a build.
- `cdecc.py` — EDC/ECC framing (`reframe`, `edc`).

> **Recovering the working base after a sandbox reset:** the working LANG1 (all §6 infra minus the
> latest test string) can be extracted from any already-built `*_cleanJP.bin` disc, or rebuilt
> from clean by applying `Langrisser1_conv_vandal.xdelta` and diffing. `extracted/LANG1.BIN` is the
> **clean** copy; `extracted/LANG1_vandal.bin` / `work_LANG1.bin` is the working base.

### EN-build integration caveat
The **story/dialogue build (EN_45)** shifts LANG1 by **+42 sectors** (LANG1 is *not* at LBA 202
there). All class-name work above is built at LBA 202 against clean JP. To merge into the full
English release, apply the LANG1 byte edits to the EN build's LANG1 at its shifted location, or
rebuild the disc with both sets of edits. Do **not** assume LBA 202 in EN_45.

---

## 8. Status

**Done & confirmed in-game:**
- Bottom-bar renderer feeds from `bbtable`; panel renderer feeds from `panelTABLE`; both accept
  ASCII letters.
- Full **A–Z** available on the bottom bar (22 native glyphs + injected **K, W, J, Y**); panel has
  all letters via FONT.DAT.
- Corrected mismaps: **Z→44, Q→42, X→56**.
- Bottom-bar text recolored **white** (matches panel class-name color).
- Test strings **"HAWK"** (H,A + injected W,K) and **"JOY"** (injected J,Y + O) render correctly
  on both renderers.

**Remaining work:**
1. **Translate and insert the real English class names** into the LANG1 class-string pool
   (§1: strings @ 0x617AC–0x61C2A and ~0x621A0+, pointer table @ 0x61C2C). Write ASCII; mind
   per-string length vs the original (shorter/equal avoids relocation; longer needs pool/pointer
   work). The bottom bar is half-width so width is generous; verify each fits the on-screen field.
2. Restore the **Lord** string at 0x6181C (currently the "JOY" test) to its real English value.
3. **(Optional)** isolate the white recolor to class + name only (dedicated palette; §5) if green
   stat labels are preferred.
4. **(Optional)** lowercase letters — currently only uppercase is mapped; add glyphs/mappings if
   mixed-case names are wanted (FONT.DAT has lowercase for the panel; the bar font would need
   lowercase glyphs verified/injected).
5. Merge into the full **EN build** honoring the +42-sector LANG1 shift (§7).
6. The **"シナリオ N" intro card** remains a separate unlocated graphic asset (out of scope here).

---

## 9. Quick reference — key constants

```
LANG1.BIN      : 413,460 B (0x64F14); CPU base 0x06010000; file_off = CPU − 0x06010000; LBA 202 (clean JP)
Bottom bar
  char loop    : CPU 0x0601C002–0x0601C08E ; fn prologue file 0xBFD0 ; glyph-draw fn 0x0601BED8
  tilemap      : entry = (r7<<12)|glyph ; HWRAM base 0x060989D0 ; loop r7 = 1
  conv patch   : file 0xC034 ; bbtable base literal @0xC040 = 0x06074DB0
  bbtable      : file 0x64DB0 (256 B) ; glyph = bbtable[byte]
  font in VRAM : CPU 0x25E20000 (VDP2 VRAM off 0x20000) ; 8×8 4bpp = 32 B/tile ; slot N @ +N*32
                 runtime-decompressed (compressed source; NOT statically editable)
  missing      : J K W Y (injected slots 200 K / 201 W / 202 J / 203 Y)
  present fix  : Z→44, Q→42, X→56
Panel (16×16)
  converter    : CPU 0x0602B270 ; idx=(byte+0x60)&0xFF ; digits→SJIS byte+0x821F ; space 0x20→0x8140
  panelTABLE   : file 0x64C30 (192 × u16 BE) ; base ptr consts patched @ file 0x1B316 / 0x1B31A → 0x06074C30
  draws via    : FONT.DAT (has all Latin) — no injection needed
Color
  CRAM         : CPU 0x25F00000 ; 16 pal × 16 col ; RGB555 BE ; white 0x7FFF ; entry (P*16+N)*2
  bar color    : CRAM[r7][glyph_fg_nibble] ; letters use nibbles 1/2/14 ; bar uses palette 1
  white write  : 0x25F00024 (pal1 nib2) and 0x25F0003C (pal1 nib14) = 0x7FFF
  note         : Mednafen can't read CRAM — use Kronos
Hook
  code         : file 0x62970 (CPU 0x06072970) ; trampoline @ file 0xBFDC ; hook-addr literal @ file 0xC044
  glyph data   : K/W/J @ file 0x64EB0/0x64ED0/0x64EF0 ; Y @ file 0x62866
Build          : edit work_LANG1.bin → splice changed sectors into clean JP (cdecc.reframe) → xdelta3
                 EN_45 build has +42-sector LANG1 shift — class work is built at LBA 202 vs clean JP
```
