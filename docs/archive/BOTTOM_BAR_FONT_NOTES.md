> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> Early bottom-bar font investigation; assumed LANG1 relocates (later disproven). Compressed-codec notes still useful.
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# Langrisser I — Bottom-Bar Class/Name Font Investigation

**Status: PARTIALLY CRACKED — paused.** Name→glyph mapping is solved and the compressed
font has been located on disc/in RAM, but the *compression codec itself* is not yet broken.
This document records everything found so a future pass can resume without re-deriving it.

Companion file: `bottom_bar_font_map.png` (visual map of all 256 font tiles).

---

## 1. The Goal

Show **English class names and character names on the bottom status bar** (the `ﾛｰﾄﾞ`
"Lord" / `ﾚﾃﾞｨﾝ` "Ledin" text under a unit). This is a *separate* text system from the
dialogue (which is done) and from the 16×16 character/class-change screen.

There are **two renderers that both read the same string** and both must show English:
- **Bottom status bar** — uses a custom half-width font in **VDP2 VRAM at offset 0x20000**
  (4bpp, 8×8 tiles, 32 bytes/tile). *This font is the hard part — see §4.*
- **16×16 character/class-change screen** — draws from **FONT.DAT** (which we already edit
  and which has every letter) but **crashes on out-of-range codes**. This is the tractable
  path and is being done first; see the main hacking reference / §7.

---

## 2. Where the strings live (EDITABLE — confirmed working)

Class and character names are **null-terminated half-width katakana (JIS X 0201)** strings
in **LANG1.BIN** (loads flat at runtime base **0x06010000**; file offset F → RAM
0x06010000+F).

- **Class-name string pool:** starts ~file **0x617AC** (e.g. `ﾌｧｲﾀｰ` Fighter, `ﾅｲﾄ` Knight,
  `ﾛｰﾄﾞ` Lord at **0x6181C**, `ﾊﾞﾝﾊﾟｲｱ` Vampire …) running to ~0x61C24, with an advanced/boss
  region further on.
- **Character-name pool:** ~file **0x6202C** (`ﾚﾃﾞｨﾝ` Ledin at 0x6202C = bytes
  `DA C3 DE A8 DD`, then Taylor, Jessica, Hawking, Volkoff …).
- **classID → string pointer table:** file **0x61C2C**, **255 entries × 4-byte big-endian**
  pointers (base 0x06010000). Duplicate IDs share a string (IDs 20/21/22 → Lord, etc.).

**Confirmed editable:** overwriting the Lord string in place (file 0x6181C) with byte `0xB1`
changed Ledin's bottom-bar class to `ｱ` in-game. So **re-encoding the names is a solved,
mechanical step** — the only blocker is getting English *glyphs* into the bottom-bar font.

---

## 3. Byte → tile mapping (CONFIRMED)

The bottom-bar renderer maps a string byte to a VRAM font tile. Verified two independent
ways (the on-screen VDP2 tilemap in `VDP2DUMP.bin` around VRAM 0x8C90, and an in-game test):

> **For the katakana range: `tile = byte − 0x70`** (equivalently `byte = tile + 0x70`).

Ground-truth points from the live tilemap (source string byte → displayed tile):
`ﾛ(0xDB)→0x6B(ロ)`, `ﾄ(0xC4)→0x54(ト)`, `ﾚ(0xDA)→0x6A(レ)`, `ﾃ(0xC3)→0x53(テ)`,
`ﾝ(0xDD)→0x6D(ン)`. So katakana bytes **0xB1–0xDD → tiles 0x41–0x6D**.

(Non-katakana byte ranges go through a lookup table that was *not* fully pinned, but the
katakana range above is all that the font-replacement plan needs — see §6.)

**Earlier dead ends (for the record):** the mapping is NOT `byte+2` and NOT ASCII-ordered.
Feeding ASCII `A`(0x41) lands on a katakana tile, not an 'A'. The two "tables" found near
LANG1 0x6472D and 0x60688 are a math ramp and a 16-bit tilemap respectively — *not* char maps.

---

## 4. The font (VRAM 0x20000) and its glyph layout

4bpp, 8×8, 32 bytes/tile. See `bottom_bar_font_map.png` for the full visual. Highlights:

| Tiles | Contents |
|-------|----------|
| 0x01–0x0A | `A T D F M P V H P L` (the letters used by the stat line) |
| 0x12–0x1B | digits `0`–`9`; 0x1C = a combined "10" glyph; 0x1D = `±` |
| 0x1F | `B` |
| 0x20–0x2F | `· X / ◢ ◣ a A P P R Q S Z C M D` |
| 0x30–0x37 | hiragana (`し き は ん い ゅ う せ`) |
| 0x40–0x6E | **katakana** (`ア` ≈ 0x41 … `ン` 0x6D, `ー` 0x6E) ← repaint targets |
| 0x70–0x7A | small katakana + dakuten/handakuten marks |
| 0x8B–0x8F | `T U R N X` (placed for the word "TURN") |
| 0x9A–0x9F | `S C E A I O` (placed for "SCENARIO" etc.) |
| 0xA0–0xA9 | bold digits 0–9 |
| 0xC0–0xC6 | solid blocks |

**Available uppercase letters:** A B C D E F G H I L M N O P Q R S T U V X Z.
**MISSING uppercase:** **J, K, W, Y** (these break Knight, Monk, Hawk Knight, Warlock,
Werewolf). Lowercase is sparse (only `a` seen clearly). The old note claiming B/F/H/L/V were
missing was **wrong** — they are present.

---

## 5. The font is COMPRESSED — located but codec not cracked

The font is **not present on disc or in any RAM dump** in 4bpp, 2bpp, 1bpp, or
nibble-swapped form (all searched). It is genuinely compressed.

**Where the compressed font lives (found via RAM dumps):**
- The game loads a **compressed asset archive into Low Work RAM at 0x00200000**
  (= uncached 0x20200000). Layout: an **offset table of ~207 big-endian uint32 entries**
  at the start, then the compressed asset blobs.
- Offset table head: `[0]=0x33C [1]=0xCF2 [2]=0x178A [3]=0x1DCA [4]=0x2232 [5]=0x232C
  [6]=0x342A [7]=0x4026 …`
- **The font is asset 0:** compressed bytes = `lo[0x33C : 0xCF2]` = **2486 bytes**,
  unpacking to the ~6 KB VRAM font. First bytes:
  `C0 01 C0 51 A2 7C 08 FC 61 0F D6 20 8B EE 04 3C 3B E0 44 F8 …`

**Loader chain (LANG1.BIN file offsets; runtime = +0x06010000):**
- Boot/scene font setup at **0xDEEA** calls loader **0x11850** repeatedly:
  `0x11850(r4=assetID, r5=VRAMdest, r6=-1, r7=0x20200000)`.
  Sequence loads asset IDs `1,0,0,2,5,6` to VRAM `0x25E26000, 0x25E20000(FONT),
  0x25C70000(VDP1), 0x25E22000, 0x25E24000, 0x25E28000`. **asset 0 → VRAM 0x20000 = the font.**
- `0x11850` is a **load-queue manager**, not the codec; it ends by calling **0x1F55C**.
- `0x1F55C` is a **multi-state dispatcher** fanning out to handlers
  `0x06033F40, 0x0602C3A4, 0x0602C3BC, 0x0602C32C, 0x0602F13C, 0x0602FED8, 0x0602C4D4`.
  The inner decompressor is somewhere below this; it was **not reached** (each layer is
  another dispatch layer in a staged/async load system).
- VDP2 NBG character-base is pointed at 0x25E20000 by register-setup code at LANG1
  0x3FA54/0x3FAB0/0x3FB14 and 0.BIN 0x8998 (these are *setup*, not the data upload).

**Codec is NOT standard LZSS.** A thorough brute-forcer (all bit polarities/orders, ring
init/start, the common 12-bit-offset/4-bit-length match encodings, header offsets 0–14,
thresholds 1–3) was run against the known decompressed output. **No parameter set produced
even a 16-byte run of real (non-zero) glyph data.** (Blank tiles produce false-positive
all-zero "matches" — beware of that when scoring.) So it is a custom/non-LZSS scheme, or the
intermediate format differs (planar / pre-expansion) in a way not yet identified.

---

## 6. The intended fix (once the codec is cracked)

No renderer patch needed for the bottom bar — just swap glyphs + re-encode names:
1. **Repaint katakana tiles 0x41–0x5A** (the `ｱ…` block, abandoned in an all-English build)
   with a clean **A–Z**.
2. **Encode each name** with bytes **0xB1–0xCA** (`A`→0xB1 … `Z`→0xCA, since byte−0x70=tile).
   Full alphabet, all-caps, no missing letters.
3. Write the edited names into the LANG1.BIN string pool (§2) in place.

To do step 1 the glyphs must reach VRAM 0x20000. **Runtime hooking was tried and fails**
because LANG1 is an overlay that (a) **relocates pointer literals at load** (a repointed
literal reverted to its original value in the RAM dump) and (b) its **file tail is BSS**
(an injected routine there was zeroed, not loaded as code). So the glyphs must be injected
at the **compressed-source level** — i.e., the codec must be cracked so we can re-pack the
font with the new glyphs, OR the loader must be hooked at a non-relocated/non-BSS site.

---

## 7. Fastest way to finish (recommended for a future pass)

The brute-force approach is a guessing game because of the blank-tile false positives. The
deterministic unlock is to **catch the decompressor in the act**:

- In an emulator with a debugger (Kronos / Mednafen / SSF if it has one), set a
  **write breakpoint on VDP2 VRAM 0x25E20000** during boot. It will trap inside the
  decompressor's inner loop. A short instruction trace there gives the exact format
  immediately.
- Alternatively keep tracing the `0x1F55C` state handlers (esp. `0x06033F40` and
  `0x0602FED8`) down to the byte-reading loop with the ring buffer.

We already have **both ends of the codec** in hand to verify against:
- compressed input: `LOWWORKRAM.BIN` bytes `0x33C–0xCF2` (also `extracted` archive).
- decompressed output: the font in `VDP2DUMP.bin` at 0x20000 (and `bottom_bar_font_map.png`).

So once the algorithm is known, writing a decoder/encoder and re-packing the font is quick.

---

## 8. Key constants (quick reference)

```
Bottom-bar font     : VDP2 VRAM 0x20000, 4bpp 8x8, 32 B/tile
Byte->tile (katakana): tile = byte - 0x70   (byte 0xB1..0xDD -> tile 0x41..0x6D)
Encoding plan        : repaint tiles 0x41-0x5A = A..Z; name byte = 0xB1 + (letter-'A')
Missing uppercase    : J K W Y   (present: A-I except J, L-V except none, X Z; no W Y)
LANG1.BIN base       : 0x06010000 (flat load, but RELOCATES pointer literals at load)
Class strings        : LANG1 file ~0x617AC ; Lord @0x6181C
Character names      : LANG1 file ~0x6202C ; Ledin @0x6202C = DA C3 DE A8 DD
classID->name table  : LANG1 file 0x61C2C, 255 x 4-byte BE ptrs (base 0x06010000)
Asset archive (RAM)  : LowWorkRAM 0x00200000 ; offset table (~207 x u32) + blobs
Font = asset 0       : archive offset 0x33C..0xCF2 (2486 B compressed)
Font loader          : LANG1 0x11850 (queue mgr) <- called from 0xDEEA ; -> 0x1F55C dispatcher
Codec                : NOT standard LZSS; inner decompressor not yet located
Runtime hook         : DOES NOT WORK (overlay relocation + BSS tail)
RAM dumps on hand    : HIGHWORKRAM(0x06000000) LOWWORKRAM(0x00200000) SCSPRAM SH2EXTBUS VDP2DUMP
```
