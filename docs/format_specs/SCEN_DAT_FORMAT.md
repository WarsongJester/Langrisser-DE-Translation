# SCEN.DAT — Format Specification

**Game:** Langrisser — Dramatic Edition (Sega Saturn)
**File:** `SCEN.DAT` — the script / text container for Langrisser I
**Endianness:** big-endian
**Status:** fully reverse-engineered; round-trip (parse → serialize) is lossless.

This document is self-contained. A companion document, `FONT_DAT_FORMAT.md`, covers the
glyph format used to render the text described here.

---

## 1. Location on disc

The data track (track 1) is an ISO9660 filesystem. The disc contains two SCEN.DAT files
(Langrisser I and Langrisser II); only the Langrisser I file is documented/edited here.

| File | LBA | Size (bytes) | Sectors (2048 B) |
|------|-----|--------------|------------------|
| SCEN.DAT (Langrisser I) | 136946 | 659,456 | 322 |
| SCEN.DAT (Langrisser II) | 157751 | 4,517,888 | — (untouched) |

When the file is enlarged, every ISO file at LBA ≥ 137268 must be shifted and the
directory records + PVD `volume_space_size` patched accordingly (out of scope for this
spec; see the project's disc-rebuild tooling).

---

## 2. Three-level structure

```
SCEN.DAT
├─ Top table : 21 absolute block offsets (each block padded to a 0x800 boundary)
└─ Blocks[0..20]
   └─ Block
      ├─ Section pointer list (relative offsets)
      └─ Section data
         └─ String table (section 2) → exposed as 10 string "entries" (index 0–9)
```

### 2.1 Top table — 21 blocks
- There are **21 blocks**.
- **Block *i* contains Scenario *i*+1**: block 0 = Scenario 1, … block 19 = Scenario 20.
  Block 20 is extra/global.
- Each block offset is an absolute file offset, padded so blocks begin on 0x800 boundaries.

### 2.2 Block internals
A block begins with a list of relative section pointers, followed by the section data.
**Section 2 is the string table** and is the only section edited. On serialize, the
pointer tables and the 0x800 block padding are regenerated.

### 2.3 String entries (the 10 logical groups)
The string table is exposed by the codec as **10 entries, indexed 0–9**. Each entry is a
single blob of **`{00}`-separated strings** (the on-disk count/offset header is stripped on
parse and regenerated on serialize).

| Entry | Contents | Count (block 0) | Notes |
|------:|----------|-----------------|-------|
| 0 | UI / menu | 139 | dictionary-compressed; content-keyed, not positional |
| 1 | names | 93 | unit / character names |
| 2 | items | 142 | indices 0–36 = item names; 37+ = descriptions (desc1 / desc2 / stat) |
| 3 | debug menu | 503 | untouched |
| 4 | places | 239 | |
| 5 | **dialogue** | per-scenario | the main script for that block's scenario |
| 6 | win / lose | 6 | |
| 7 | **title + prologue** | 1 string | the scenario's prologue, per block |
| 8 | scenario titles | 20 | |
| 9 | empty | — | 2 bytes |

---

## 3. Duplicated globals (important for editing)

Entries **0, 1, 2, 3, 4, 8** are **global** and stored **identically in every block**.
A change to a name, item, menu string, or scenario title must therefore be written into
**all 21 blocks**, or the change will only appear in some scenarios.

Entries **5 (dialogue)** and **7 (title+prologue)** are **per-scenario** (unique to the block).

---

## 4. Control codes

These appear inside dialogue (entry 5) and prologue (entry 7) strings.

| Code | Meaning |
|------|---------|
| `{06}{07}` | box advance / page break (move to the next message box) |
| `{08}` | newline (line break inside a box) |
| `{05}` | prologue format / indent marker |
| `{04}{XX}` | dictionary word (text compression). Re-encoded text simply drops these. Known: `{04}{1C}`=Winning Conditions, `{04}{1D}`=Losing Conditions, `{04}{01}`+digit+`{04}{83}`=SCENARIO-NN, `{04}{83}` ≈ opening 「 |
| `{09}{XX}` | name insert |
| `{02}` | lord-name insert |
| `{03}` | prologue title setup |

**Message box geometry:** a dialogue box is **3 lines × 14 full-width cells**. Text between
`{06}{07}` markers is one box; `{08}` separates the lines within it. (After the English
pass, Scenario 1's dialogue uses only `{06}{07}` and `{08}`.)

---

## 5. Text encoding

The renderer draws **exactly 2 bytes per cell** (one SJIS/JIS double-byte code = one cell).

### 5.1 Full-width (default)
ASCII is mapped to full-width SJIS:
- letters/digits: Unicode `U+FEE0 + c` (e.g. `A`→`0x8260`, `a`→`0x8281`, `0`→`0x824F`)
- space → `0x8140`
- specials: `'`→U+2019, `"`→U+201D, `-`→U+2015, `` ` ``→U+2018

### 5.2 Half-width pair packing (optional technique)
Because the renderer is fixed at one double-byte code per cell, two half-width letters can
be packed into a single glyph cell by composing a custom glyph and emitting an otherwise-
unused double-byte code (in practice, an unused kanji code) that points at it. This is a
font-side technique; see `FONT_DAT_FORMAT.md` §6. From SCEN.DAT's perspective the text
simply emits those codes, doubling letters-per-line and halving byte count.

---

## 6. Codec behavior (reference implementation notes)

- `parse(bytes) → model`, `serialize(model) → bytes` — lossless.
- Only section-2 string bytes are edited. String counts and order are preserved.
- Pointer tables and 0x800 block padding are regenerated on serialize.
- Each entry is handled as the raw `{00}`-separated string data; to edit, split on `0x00`,
  modify the individual strings, and rejoin with `0x00`.

---

## 7. Verification notes

- Block→scenario mapping confirmed by the build tooling (`blocks[scenario-1]`).
- Lossless round-trip confirmed across all blocks.
- Scenario 1 dialogue (entry 5, block 0) audited: 65 strings, control codes limited to
  `{06}{07}` (69×) and `{08}` (174×), no residual kana/kanji after the English pass.
