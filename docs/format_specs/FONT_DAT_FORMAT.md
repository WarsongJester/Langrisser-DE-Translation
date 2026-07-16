# FONT.DAT — Format Specification

**Game:** Langrisser — Dramatic Edition (Sega Saturn)
**File:** `FONT.DAT` — the glyph bank for Langrisser I
**Endianness:** big-endian
**Status:** reverse-engineered and verified (structure, anchors, pixel order, kanji-slot
math, and spare-slot survey all confirmed against the file).

This document is self-contained. A companion document, `SCEN_DAT_FORMAT.md`, covers the
text container that references these glyphs.

---

## 1. Location on disc

The disc contains two FONT.DAT files (Langrisser I and II); only the Langrisser I file is
documented/edited here.

| File | LBA | Size (bytes) |
|------|-----|--------------|
| FONT.DAT (Langrisser I) | 135070 | 220,732 |
| FONT.DAT (Langrisser II) | 144527 | 220,732 (untouched) |

The Langrisser I FONT.DAT sits **before** SCEN.DAT (LBA 136946), so it is unaffected by
SCEN growth and can be overwritten in place (its size never changes when only glyph pixels
are edited).

---

## 2. File layout

```
FONT.DAT
├─ Header : 7 × big-endian uint32 pointers
└─ 6 glyph banks (S0..S5), back to back
```

The 7 pointers are the start offsets of the 6 banks plus an end marker:

| Pointer | Value | Bank start |
|--------:|-------|-----------|
| 0 | 0x0001C | S0 |
| 1 | 0x00D9C | S1 |
| 2 | 0x021DC | S2 |
| 3 | 0x0349C | S3 |
| 4 | 0x03EBC | S4 |
| 5 | 0x266FC | S5 |
| 6 | 0x35E3C | end of S5 |

---

## 3. Glyph format

- Every glyph is **16×16 pixels, 1 bit per pixel = 32 bytes** (16 rows × 2 bytes/row).
- A glyph at bank-base `B`, slot `n` starts at byte offset `B + n*32`.

### 3.1 Row pixel order (the byte-swap quirk)
Within a row, the two bytes are **swapped** relative to the naive left-to-right assumption:

```
byte at (row*2)     = RIGHT 8 pixels of the cell
byte at (row*2 + 1) = LEFT  8 pixels of the cell

render: word = (byte_at[row*2 + 1] << 8) | byte_at[row*2]
        word bit 15 = leftmost column ... bit 0 = rightmost column
```

A symmetric glyph (e.g. `0`) looks correct even if you forget the swap; asymmetric glyphs
(`A`, `a`) come out mirrored-in-halves unless the swap is applied.

---

## 4. Bank contents

Banks follow JIS X 0208 row (ku) order.

| Bank | Offset | Glyphs | Contents | JIS ku |
|------|--------|-------:|----------|--------|
| S0 | 0x001C | 108  | symbols / punctuation | 1–2 |
| S1 | 0x0D9C | 162  | full-width ASCII (slots 0–78) + hiragana (slots 79–161) | 3–4 |
| S2 | 0x21DC | 150  | katakana + Greek | 5–6 |
| S3 | 0x349C | 81   | Cyrillic | 7 |
| S4 | 0x3EBC | 4418 | kanji — a complete **47 ku × 94 ten** grid | 16–62 |
| S5 | 0x266FC| 1978 | kanji level-2 (+ a few extra) | 63–83 |

### 4.1 S1 ASCII layout (verified anchors)
S1 is straight JIS order. Confirmed anchors:

```
slot 0  = '0'      (digits 0–9 = slots 0–9)
slot 17 = 'A'      (A–Z = slots 17–42)
slot 49 = 'a'      (a–z = slots 49–74)
slots 79–161       = hiragana (83 glyphs)
```

---

## 5. SJIS ↔ kanji-slot math

Because S4/S5 are complete JIS grids, any kanji's glyph slot is computable from its
(ku, ten):

```
16 ≤ ku ≤ 62 :  S4 slot = (ku - 16) * 94 + (ten - 1)
63 ≤ ku ≤ 83 :  S5 slot = (ku - 63) * 94 + (ten - 1)
```

### 5.1 SJIS ↔ (ku, ten) conversion
```
# SJIS bytes (s1, s2) → ku, ten
j1 = s1 - 0x81 if s1 < 0xA0 else s1 - 0xC1
ku = j1*2 + (1 if s2 >= 0x9F else 0) + 1
ten = (s2 - 0x9E) if s2 >= 0x9F else (s2 - 0x40 if s2 >= 0x80 else s2 - 0x3F)

# (ku, ten) → SJIS bytes
j1 = (ku - 1) // 2
s1 = j1 + (0x81 if j1 <= 0x1E else 0xC1)
if ku % 2 == 1:            # odd ku
    s2 = ten + 0x3F
    if s2 >= 0x7F: s2 += 1 # skip 0x7F
else:                      # even ku
    s2 = ten + 0x9E
```
Round-trip verified for all ku 16–83, ten 1–94. As a sanity check, all 825 kanji codes
that actually appear in SCEN.DAT map to non-blank glyph slots under this formula.

---

## 6. Spare-slot survey & glyph composition

### 6.1 Which slots are safe to repurpose
- **All-zero (blank) glyphs in the whole font: only 92.** Too few for serious use.
- The game displays only **825 distinct kanji** (of 6,396 kanji slots). The remaining
  **~5,571 kanji slots are never emitted** and are therefore safe to overwrite.
- **Do NOT repurpose hiragana / katakana / Greek / Cyrillic slots** — the still-Japanese
  menus, status bar, and any untranslated text render those glyphs.

### 6.2 Composing a half-width pair glyph
To place two 8-pixel-wide letters in one cell (left = char A, right = char B), with `gA[r]`
/ `gB[r]` being each char's row byte (MSB = leftmost of its 8 columns):

```
for row r in 0..15:
    FONT[base + r*2]     = gB[r]   # right half  (byte0)
    FONT[base + r*2 + 1] = gA[r]   # left half   (byte1)
```

Then emit, in the text stream, the SJIS code of the unused kanji slot `base` corresponds
to. The engine draws the kanji cell, which now shows two half-width letters. This is the
basis of the half-width "Route B" packing (no renderer patch required); see
`SCEN_DAT_FORMAT.md` §5.2.

---

## 7. Verification notes

- Header pointers, bank sizes, and the S4 = 47×94 = 4418 exact grid confirmed by parsing
  the file.
- Anchors (`0`/`A`/`a`) confirmed by rendering the glyphs (with the byte-swap applied).
- Kanji-slot formula confirmed: 825/825 SCEN-used kanji → non-blank slots; SJIS round-trip
  exact for the full kanji range.
