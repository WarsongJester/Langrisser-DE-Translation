# In-Battle Class / Unit Names — Reference (SOLVED)

**Status: DONE & confirmed in-game.** Both renderers display English; all 26 uppercase letters
are available; bottom-bar text recolored white to match the panel. Confirmed with build
`patches/Langrisser1_inject_AZ.xdelta` (test strings "HAWK" and "JOY").

This is the authoritative class-name reference. It documents the **final runtime-hook solution**.
A different earlier approach (katakana-slot repaint) is recorded in
`docs/archive/LANGRISSER1_CLASSNAMES_MENU_HANDOFF.md`; see §8 for why this one supersedes it —
**do not naively combine the two**.

This system is **separate** from SCEN.DAT and the dialogue font. It does not use Route B.

---

## 0. TL;DR

- Class/unit names are null-terminated strings in **LANG1.BIN**, in a **custom 1-byte code
  page** (not SJIS). One string feeds **two independent renderers**.
- **Bottom status bar:** byte → `bbtable` → glyph index → an **8×8 4bpp font in VDP2 VRAM at
  0x20000**. That font is runtime-decompressed from IMG.DAT and is **missing J K W Y**. Fix =
  inject those 4 glyphs into blank VRAM slots at runtime via a CPU hook, and map them in `bbtable`.
- **16×16 panel** (status / class-change): byte → `panelTABLE` → **full-width SJIS** → drawn via
  **FONT.DAT**, which already has every Latin letter. No glyph work needed.
- **Color:** bottom-bar text color = `CRAM[palette][glyph_fg_nibble]`. White recolor = write
  `0x7FFF` into the bar palette's green entries in CRAM (same hook).
- All edits are in LANG1.BIN, built against the **clean Japanese disc** (LANG1 @ LBA 202), spliced
  in-place, shipped as xdelta3. **LANG1 loads verbatim → code patches are reliable** (this is what
  made the hook approach possible).

---

## 1. Where the class strings live (LANG1.BIN)

LANG1.BIN = 413,460 B (0x64F14), loaded to **CPU 0x06010000** (`file_off = CPU − 0x06010000`).

- **Class-name string pool** (null-terminated, custom 1-byte encoding):
  - Main pool (Fighter, Knight, …, Lord): file **0x617AC–0x61C2A**.
  - Second region (Vampire Lord, Necromancer, Phoenix, …): **~0x621A0+**.
- **Class pointer table:** **255-entry, 4-byte big-endian** at file **0x61C2C** (classID →
  string CPU address, base 0x06010000; contains duplicates). Strings load to **HWRAM 0x060717AC**;
  both renderers read them there.
- **"Lord" string** (Ledin's class, original `DB B0 C4 DE 00` = ﾛｰﾄﾞ) at file **0x6181C** — used
  as the in-place test target ("VANDAL"/"HAWK"/"JOY" during bring-up). Same-length-or-shorter
  edits avoid relocation.
- **Character-name pool:** ~file **0x6202C** (ﾚﾃﾞｨﾝ=Ledin at 0x6202C). Character-name pointer
  table at CPU 0x06072314.

> The custom code page is **not** ASCII and **not** SJIS. The chosen approach writes **ASCII
> letters** into the strings and makes both tables map ASCII → glyph/SJIS. That mapping is in
> place and proven.

---

## 2. Renderer A — bottom status bar (half-width, custom 8×8 font)

### 2.1 Code path
- Class-name **character loop:** CPU **0x0601C002–0x0601C08E** (fn prologue file 0xBFD0 / CPU
  0x0601BFD0).
- **Glyph-draw routine** at CPU **0x0601BED8**; writes a VDP2 tilemap entry `= (r7<<12) |
  glyph_index` into the bar tilemap (HWRAM base **0x060989D0**, DMA'd to VRAM). The loop sets
  **r7 = 1** (palette 1).
- Out-of-range codes here **do not crash** — they just draw wrong glyphs.

### 2.2 The conversion (`bbtable`)
The clean firmware computed the glyph index arithmetically (thresholds + byte−112/−53/−30 + a
couple of specials + the 0xDE/0xDF combining-mark paths). That arithmetic was **replaced** with
a flat 256-byte table lookup, keeping the combining paths intact:

```
0xC034  d1 02   mov.l @(2,pc),r1     ; r1 = const@0xC040 = 0x06074DB0 (bbtable base)
0xC036  00 1c   mov.b @(r0,r1),r0    ; r0 = bbtable[byte]
0xC038  60 0c   extu.b r0,r0
0xC03A  a0 1f   bra 0x0601C07C       ; -> draw-setup (skips old arithmetic)
0xC03C  00 09   nop (delay)
0xC03E  00 09   nop
0xC040  06 07 4d b0   .long 0x06074DB0  (bbtable base literal)
```
- **`bbtable`** = 256 bytes at file **0x64DB0** (CPU 0x06074DB0). `glyph = bbtable[byte]`.
- Non-letter bytes keep the original-formula values (katakana/symbols/digits still render).
- `byte 0x20` (space) → glyph 0x40 (blank tile). **ASCII A–Z** (0x41–0x5A) → font slots (§2.4).

### 2.3 The font in VRAM
- VDP2 VRAM offset **0x20000** = CPU **0x25E20000** (uncached). **8×8, 4bpp = 32 B/tile**;
  slot N → `0x25E20000 + N*32`. Row layout: 4 bytes/row, high nibble = left pixel of each pair.
- **Runtime-decompressed from IMG.DAT** (the decompressor takes its dest as a parameter, so it
  isn't findable by literal-scan and wasn't reversed). The font is **not present as plain bitmap
  anywhere on disc** → cannot be edited statically. Hence glyph fixes are done by a **runtime
  VRAM write** (§4).

### 2.4 Verified font slot map (8×8 tiles in VRAM 0x20000)
Uppercase letters present natively (as mapped in `bbtable`):
```
A=1   B=31  C=155 D=3   E=156 F=4   G=143 H=8   I=160 L=10  M=5
N=141 O=161 P=6   R=140 S=154 T=138 U=139 V=7   Q=42  X=56  Z=44
```
- **Corrected mismaps:** Z→44, Q→42, X→56 (an earlier sweep had these wrong; Z had pointed at a
  C glyph).
- Digits 0–9 ≈ slots 18–27; katakana ≈ 64–137.
- **Truly missing (no glyph anywhere): J, K, W, Y** — the only letters needing injection. (For
  class names alone, only K and W are required; J/Y are for unit/character names.)
- 162 blank tiles exist; injection uses slots **200–203**.

---

## 3. Renderer B — 16×16 status / class-change panel

### 3.1 Code path
- Class-byte → SJIS **converter** at CPU **0x0602B270**: builds a full-width SJIS string into an
  output buffer (`r5`), then the standard full-width drawer renders it via **FONT.DAT**. Per byte:
  - `0x20` → full-width space (0x8140);
  - `0x30–0x39` → SJIS `byte + 0x821F`;
  - else `idx = (byte + 0x60) & 0xFF`, `SJIS = panelTABLE[idx]`.
- Out-of-range codes historically **crashed** (corrupted indirect call → MasterSH2 "unknown
  code"). Because we now feed valid table entries for every letter, that path is never exercised.

### 3.2 `panelTABLE`
- 192-entry **big-endian u16** table at file **0x64C30** (CPU 0x06074C30). Repointed from the
  original 0x06072E78 by patching the two base-pointer constants:
  - file **0x1B316**: `2E 78 → 4C 30`
  - file **0x1B31A**: `2E 79 → 4C 31`
- Entries: katakana copied for idx 0x00–0x41; **all A–Z mapped to SJIS Latin** (`'A' idx 0xA1 →
  0x8260` … `'Z' idx 0xBA → 0x8279`); remaining = 0x8140 (space) filler.
- **FONT.DAT already contains every Latin glyph** (full-width ASCII at S1 slots 17–42), so the
  panel renders any letter with **no glyph injection**.

---

## 4. Glyph injection + white recolor — the runtime hook

Because the bar font is runtime-decompressed and lacks J/K/W/Y, the fix is a **CPU hook** that,
each time the class-name function runs, (a) copies the four missing glyph bitmaps from LANG1 into
blank VRAM slots, and (b) writes white into the bar palette. Writing every call is idempotent, so
glyphs survive any font re-decompress; cost is trivial (128 bytes + 2 CRAM words).

### 4.1 Glyph data (in LANG1 free space) — 8×8, 4bpp, fg nibble 0xE, 32 B each
| Letter | VRAM slot | VRAM dest | LANG1 source (file / CPU) |
|--------|-----------|-----------|---------------------------|
| K | 200 | 0x25E21900 | 0x64EB0 / 0x06074EB0 |
| W | 201 | 0x25E21920 | 0x64ED0 / 0x06074ED0 |
| J | 202 | 0x25E21940 | 0x64EF0 / 0x06074EF0 |
| Y | 203 | 0x25E21960 | 0x62866 / 0x06072866 |

K/W/J are contiguous (one 96-byte copy); Y is in a separate zero-run (one 32-byte copy).

### 4.2 The hook (file 0x62970, CPU 0x06072970)
Preserves r1–r3, does two VRAM copies + two CRAM writes, runs the three displaced prologue
instructions, then `rts`:
```
06072970  mov.l r1,@-r15
06072972  mov.l r2,@-r15
06072974  mov.l r3,@-r15
06072976  mov.l 0x60729b0,r1      ; SRC1 = 0x06074EB0 (K,W,J)
06072978  mov.l 0x60729b4,r2      ; DST1 = 0x25E21900
0607297A  mov   #48,r3            ; 48 words = 96 bytes
0607297C  mov.w @r1+,r0           ; loop1
0607297E  mov.w r0,@r2
06072980  add   #2,r2
06072982  dt    r3
06072984  bf    0x607297c
06072986  mov.l 0x60729b8,r1      ; SRC2 = 0x06072866 (Y)
06072988  mov.l 0x60729bc,r2      ; DST2 = 0x25E21960
0607298A  mov   #16,r3            ; 16 words = 32 bytes
0607298C  mov.w @r1+,r0           ; loop2
0607298E  mov.w r0,@r2
06072990  add   #2,r2
06072992  dt    r3
06072994  bf    0x607298c
06072996  mov.w 0x60729c8,r0      ; WHITE = 0x7FFF
06072998  mov.l 0x60729c0,r1      ; CR2  = 0x25F00024 (palette 1, nibble 2)
0607299A  mov.w r0,@r1
0607299C  mov.l 0x60729c4,r1      ; CR14 = 0x25F0003C (palette 1, nibble 14)
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
060729B0 .long 0x06074EB0  060729B4 .long 0x25E21900
060729B8 .long 0x06072866  060729BC .long 0x25E21960
060729C0 .long 0x25F00024  060729C4 .long 0x25F0003C
060729C8 .word 0x7FFF
```

### 4.3 Trampoline (function entry)
The hook is too far for a direct branch and the local literal pool is packed, so the trampoline
borrows a **dead-code slot**: the conv patch's `bra` (§2.2) made the old arithmetic path at
0xC044–0xC07B unreachable, so the hook address lives there.
- **Hook-address literal @ file 0xC044** = `06 07 29 70`.
- **Trampoline @ file 0xBFDC** (overwrites the 3 original prologue instructions the hook
  re-executes):
  ```
  0xBFDC  d0 19   mov.l @(25,pc),r0   ; -> literal @0xC044 = hook
  0xBFDE  40 0b   jsr @r0
  0xBFE0  00 09   nop
  ```
  `pr` was already saved one instruction earlier, so clobbering it here is safe.

---

## 5. Color / palette model

- **CRAM** at CPU **0x25F00000**: 16 palettes × 16 colors, **RGB555 big-endian**
  (`w=(b0<<8)|b1; r=w&0x1F; g=(w>>5)&0x1F; b=(w>>10)&0x1F; white=0x7FFF`). Palette P entry N →
  CRAM offset `(P*16 + N)*2`.
- Bar text color = **`CRAM[r7][glyph_fg_nibble]`**; the bar loop uses **r7 = 1**.
- **Letters don't share one fg nibble** — measured nibble **14** (A, Z), **2** (L, Q), **1** (G,
  digits). So a single palette-entry edit can't recolor every letter.
- Palette 1 (clean): nibble 1 ≈ white; nibbles 2 and 14 = green.
- **White recolor used:** write `0x7FFF` to palette 1 **nibble 2 (0x25F00024)** and **nibble 14
  (0x25F0003C)**. Net in-game (confirmed): class + unit name + stat letter-labels render **white**,
  stat numbers stay green (different palette), matching the panel's white.
- The bar palette is loaded dynamically (RAM buffer ~0x06075060 via fade @0x06013EA0; raw palette
  not on disc), hence a **runtime CRAM write**, not a static edit.
- **Tooling note:** **Mednafen can't read CRAM** (its 0x5F00000 view is a TODO placeholder). Use
  **Kronos** for palette work.

### Optional refinement (not done)
To whiten *only* class + unit name and leave stat labels green: give the bar loop its own palette
(white at nibbles 1, 2, 14) and change `mov #1,r7` to that palette number. Deferred.

---

## 6. Complete list of LANG1 byte changes

| File offset | CPU | What | Bytes (→) |
|-------------|-----|------|-----------|
| 0xBFDC | 0x0601BFDC | trampoline (jsr hook) | `D0 19 40 0B 00 09` |
| 0xC034 | 0x0601C034 | char-loop conv → bbtable lookup + bra | `D1 02 00 1C 60 0C A0 1F 00 09 00 09` |
| 0xC040 | 0x0601C040 | bbtable base literal | `06 07 4D B0` |
| 0xC044 | 0x0601C044 | hook-address literal (dead code) | `06 07 29 70` |
| 0x1B316 | 0x0602B316 | panelTABLE base hi-ptr | `4C 30` |
| 0x1B31A | 0x0602B31A | panelTABLE base lo-ptr | `4C 31` |
| 0x6181C | 0x0607181C | **test** class string (Lord) | `"JOY\0\0\0"` (restore real class) |
| 0x62866 | 0x06072866 | Y glyph (slot 203), 32 B | 8×8 4bpp |
| 0x62970 | 0x06072970 | hook code + literals (~0x5A B) | see §4.2 |
| 0x64C30 | 0x06074C30 | panelTABLE (192 × u16) | katakana + A–Z→SJIS |
| 0x64DB0 | 0x06074DB0 | bbtable (256 B) | formula + A–Z→slots |
| 0x64EB0 | 0x06074EB0 | K,W,J glyphs (slots 200–202), 96 B | 8×8 4bpp |

Free space used: the 736-byte zero-run at 0x64C30 holds panelTABLE + bbtable + K/W/J glyphs;
Y glyph in the isolated zero-run at 0x62866; hook in the zero-run at 0x62970; hook-address
literal in the dead arithmetic code at 0xC044. No code/data the game uses is overwritten.

---

## 7. Build / splice / ship + the EN-merge caveat

Built **against the clean Japanese disc**, where LANG1.BIN is at **LBA 202** (user data at
`sector*2352+16`, 2048 B/sector; LANG1 byte N → sector `202 + N//2048`).

1. `build_inject.py` (to be re-created in `/home/claude/lang/`) applies all §6 edits to a working
   LANG1 → `out_LANG1.bin`.
2. Splice: copy clean disc → temp; for each changed LANG1 sector, overwrite the 2048-byte user
   region and re-frame with `tools/cdecc.py` `reframe(sector2352, lba)`.
3. `xdelta3 -e -9 -f -s <clean.bin> temp.bin <out>.xdelta`.
4. Validate: re-apply, re-extract LANG1, assert == `out_LANG1.bin`; spot-check EDC.

Verification helpers: `tools/sh2dis.py <fileoff_hex> <N> [label]` (SH-2 BE disasm),
`tools/cdecc.py`.

> **⚠ EN-build integration caveat.** The story build (EN_45) shifts LANG1 by **+42 sectors** —
> **LANG1 is NOT at LBA 202 there.** All class-name work above is built at LBA 202 against clean
> JP. To merge into the full English release, apply the LANG1 byte edits to the EN build's LANG1
> at its shifted location (or rebuild the disc with both edit sets). **Do not assume LBA 202 in
> EN_45.** This merge is the main remaining engineering step.

---

## 8. Why this supersedes the earlier katakana-repaint approach

There are two distinct solutions in the project history. **This runtime-hook approach is the
current one.**

| | Runtime hook (THIS doc / `inject_AZ`) | Katakana repaint (`archive/…CLASSNAMES_MENU_HANDOFF`) |
|--|--------------------------------------|-------------------------------------------------------|
| Bottom bar | **Solved** (glyph injection + bbtable) | **Not solved** (deferred) |
| 16×16 panel | Solved via `panelTABLE` → SJIS → FONT.DAT (all letters) | Solved via repainting FONT.DAT **katakana** slots; hybrid 80-slot pair encoding |
| Class strings | ASCII letters | Stay in katakana code range |
| FONT.DAT katakana slots | untouched | **repainted with English** (would corrupt remaining Japanese katakana) |
| LANG1 code | patched (relies on verbatim load) | data-table only (predates the verbatim-load finding) |

They edit the **same files in incompatible ways** (the repaint approach overwrites katakana
glyph slots; the hook approach leaves them alone and patches code/tables). **Pick one. Don't
merge them.** The hook approach is preferred: it fixes the bottom bar too, doesn't sacrifice
katakana glyphs, and gives a clean full A–Z. The earlier approach's **menu work** is a separate
thing and is tracked in `docs/in_battle_ui/MENU_CHROME.md`.

---

## 9. Status & remaining work

**Done & confirmed in-game:** both renderers accept ASCII letters; full A–Z on the bottom bar
(22 native + injected K/W/J/Y); panel has all letters via FONT.DAT; mismaps Z→44/Q→42/X→56
fixed; bottom bar recolored white; "HAWK"/"JOY" render correctly on both.

**Remaining:**
1. **Translate and insert the real English class names** into the LANG1 pool (§1: strings @
   0x617AC–0x61C2A and ~0x621A0+, pointer table @ 0x61C2C). Write ASCII; mind per-string length
   (shorter/equal avoids relocation; longer needs pool/pointer work). Verify each fits the
   on-screen field. (A 132-class romanized list — ROM pool order — is in
   `docs/archive/LANGRISSER1_CLASSNAMES_MENU_HANDOFF.md` §11; note its source-of-truth caveats.)
2. **Restore the Lord string** at 0x6181C (currently the "JOY" test) to its real value.
3. **Merge into the full EN build** honouring the +42-sector LANG1 shift (§7).
4. *(Optional)* isolate the white recolor to class + name only (dedicated palette; §5).
5. *(Optional)* lowercase letters (FONT.DAT has them for the panel; the bar font would need
   lowercase glyphs verified/injected).

---

## 10. Quick reference

```
LANG1.BIN   : 413,460 B; CPU base 0x06010000; LBA 202 (clean JP); loads VERBATIM (no reloc)
Bottom bar  : char loop CPU 0x0601C002–8E; fn prologue file 0xBFD0; glyph-draw 0x0601BED8
              tilemap entry=(r7<<12)|glyph; HWRAM base 0x060989D0; loop r7=1
              conv patch file 0xC034; bbtable @file 0x64DB0 (256 B); glyph=bbtable[byte]
              font VRAM 0x20000 (CPU 0x25E20000), 8×8 4bpp 32 B/tile; runtime-decompressed
              missing J K W Y → injected slots 200/201/202/203; mismaps fixed Z44 Q42 X56
Panel 16×16 : converter CPU 0x0602B270; idx=(byte+0x60)&0xFF; digit→SJIS byte+0x821F; sp→0x8140
              panelTABLE @file 0x64C30 (192×u16 BE); base ptrs patched @file 0x1B316/0x1B31A
              draws via FONT.DAT (all Latin) — no injection
Color       : CRAM CPU 0x25F00000; RGB555 BE; white 0x7FFF; entry (P*16+N)*2
              bar color CRAM[r7][fg_nibble]; letters nibbles 1/2/14; white @0x25F00024 & 0x25F0003C
              Mednafen can't read CRAM — use Kronos
Hook        : code file 0x62970; trampoline file 0xBFDC; hook-addr literal file 0xC044
              glyphs K/W/J @file 0x64EB0/0x64ED0/0x64EF0; Y @file 0x62866
Build       : edit LANG1 → splice changed sectors into clean JP (cdecc.reframe) → xdelta3
              EN_45 has +42-sector LANG1 shift — class work is at LBA 202 vs clean JP
Patch       : patches/Langrisser1_inject_AZ.xdelta (A–Z proof; test strings HAWK/JOY)
```
