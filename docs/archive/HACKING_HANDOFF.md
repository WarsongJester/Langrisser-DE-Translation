> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> Route A (full-width) era — predates the Route B half-width breakthrough.
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# Langrisser I (Dramatic Edition, Saturn) — ROM-Hacking Handoff

**Read this to take over a fan-translation in progress.** It explains what has been reverse-engineered, what has been patched, and *how* — with the key algorithms inline so the tooling can be rebuilt from scratch (the sandbox filesystem resets between sessions, so assume no working files survive; only the user's uploads and this doc do).

---

## 0. TL;DR for the new assistant

- Game: *Langrisser - Dramatic Edition* (Sega Saturn). We are translating the **Langrisser I** half to English.
- The user provides English translations as **.xlsx**; you do all RE, text reinsertion, and disc rebuilding. The user tests in the **SSF emulator** and replies with screenshots. You cannot run the game.
- The text engine is **strictly fullwidth (2-byte)**. Encode all English as fullwidth SJIS.
- A real half-width font hack was attempted and **abandoned**; the shipping plan is **fullwidth + voices (PCM) OFF + overflow re-segmentation**.
- **The dominant hard limit: a ~8-fullwidth-char fixed buffer for names/labels. Exceeding it crashes the game (jump to garbage at `PC 0606B4D8`).** This governs character names, item names, and menu labels.

---

## 1. Files the user must re-upload

- `Langrisser_-_Dramatic_Edition__SAT_.7z` — the original game (contains the raw `.bin`/`.cue`; the disc image extracts to a track1.iso plus tracks 2–6).
- `Langirsser_I_My_Script.xlsx` — main **dialogue**. Sheets `Scenario 1`..`Scenario 20` (06/08/09 are zero-padded). `<>` = end of a message box; `<clsr>` = page break; each row is a line.
- `Other_Langrisser_Stuff.xlsx` — **extras**. Sheets: `Names`, `Items`, `Menu`, `Scenario Prologues`, `Scenario Quiz`, `Quiz Battle Explanations`, `Endings`.
- (Optional) HWRAM dumps `kronos.bin`/`taylor.bin`/`freeze.bin` and `LANGRISSER_PCM_ON/OFF.bkr` for further RE.

The translation/patch artifact is an **xdelta3 patch** the user applies to the original raw `.bin`, plus a generated `.cue`.

---

## 2. What has been hacked (accomplishments)

1. **SCEN.DAT script format fully cracked** — lossless parse/serialize codec.
2. **Fullwidth SJIS reinsertion** with overflow re-segmentation for dialogue.
3. **Disc rebuild pipeline** — grows SCEN.DAT in place, fixes the ISO9660 directory + PVD, re-frames MODE1/2352 sectors with correct EDC/ECC, reattaches tracks 2–6, emits a matching `.cue`, and produces an xdelta patch.
4. **Dialogue**: 14 scenarios done & confirmed in-game (1,2,5,6,7,10,11,12,13,15,16,17,18,19).
5. **Prologues**: all 20 done & confirmed (title + body + win/lose, wrapped, indent removed).
6. **Item names**: translated, capped at 8 chars (safe).
7. **Menu/UI**: short labels (≤8 chars) translated; long messages left Japanese (buffer limit).
8. **Constraints discovered**: the 8-char buffer crash; the 2×16 item-description box; the separate status-bar name table; the separate "シナリオ N" intro-card asset.

---

## 3. HOW — SCEN.DAT format & codec

`SCEN.DAT` lives in the disc filesystem (path `LANG1/SCEN.DAT`). Big-endian throughout.

```
[top table]   32-bit ABSOLUTE offsets to N blocks; the entry after the last block = EOF.
              The table is padded to 0x800 (CD sector). #blocks = 21.
each block:   [section pointer table: M 32-bit offsets RELATIVE to block base][section data...]
              block i corresponds to Scenario i+1. Block 0 = the GLOBAL data block.
section 2     = the STRING TABLE: first 32-bit value = (count*4) = pointer-table size;
              then `count` relative offsets, then the concatenated strings.
              Strings are {00}-separated, Shift-JIS (cp932) + 1-byte control codes.
other sections= opaque bytecode/binary — PRESERVE VERBATIM.
```

Only the **byte content of section-2 string entries** is modified; entry **count and order are preserved** (bytecode references strings by index). All pointer tables are regenerated on serialize; blocks are padded to 0x800.

**Section-2 entries (per block):**

| idx | content | notes |
|---|---|---|
| 0 | UI/menu strings (139) | global; Menu sheet, SECT 0 |
| 1 | character/class names (93) | global; Names sheet; identical across all blocks |
| 2 | items: 37 names then descriptions (142) | global; Items sheet |
| 3 | big debug/config menu (503) | global; not in Menu sheet |
| 4 | places/proper nouns (239) | global |
| 5 | **main dialogue** | per-scenario |
| 6 | win/lose conditions (6) | per-scenario |
| 7 | **title + prologue** (1 long string) | per-scenario |
| 8 | 20 scenario titles | global |
| 9 | empty | |

Global entries (0,1,2,3,4,8) are **duplicated identically in all 21 blocks** → patch every block.

**Codec (rebuildable):**
```python
import struct
BE=lambda o,d: struct.unpack('>I',d[o:o+4])[0]
def p32(v): return struct.pack('>I',v)

def parse(d):
    blocks_off=[]; last=-1
    for i in range(0,0x800,4):
        v=BE(i,d)
        if v==0 and blocks_off: break
        if v<last or v>len(d): break
        blocks_off.append(v); last=v
    nblocks=len(blocks_off)-1; blocks=[]
    for bi in range(nblocks):
        base=blocks_off[bi]; bend=blocks_off[bi+1]
        nsec=BE(base,d)//4
        secptr=[BE(base+i*4,d) for i in range(nsec)]
        secs=[]
        for si in range(nsec):
            ss=base+secptr[si]; se=base+secptr[si+1] if si+1<nsec else bend
            secs.append(d[ss:se])
        strings=None
        if nsec>2:
            s2=secs[2]
            if len(s2)>=4:
                first=BE(0,s2)
                if first>0 and first%4==0 and first<=len(s2):
                    cnt=first//4; sp=[BE(j*4,s2) for j in range(cnt)]
                    if sp==sorted(sp) and (not sp or sp[-1]<=len(s2)):
                        strings=[s2[sp[j]:(sp[j+1] if j+1<cnt else len(s2))] for j in range(cnt)]
        blocks.append({'base':base,'nsec':nsec,'secs':secs,'strings':strings})
    return {'blocks':blocks,'orig_len':len(d),'header_size':blocks_off[0]}

def _build_sec2(strings):
    tbl=len(strings)*4; offs=[]; cur=tbl
    for s in strings: offs.append(cur); cur+=len(s)
    return b''.join(p32(o) for o in offs)+b''.join(strings)

def serialize(model, align=0x800):
    block_bytes=[]
    for blk in model['blocks']:
        secs=list(blk['secs'])
        if blk['strings'] is not None: secs[2]=_build_sec2(blk['strings'])
        nsec=len(secs); secptr=[]; cur=nsec*4
        for s in secs: secptr.append(cur); cur+=len(s)
        bb=b''.join(p32(o) for o in secptr)+b''.join(secs)
        if len(bb)%align: bb+=b'\x00'*(align-len(bb)%align)
        block_bytes.append(bb)
    hs=model['header_size']; offs=[]; cur=hs
    for bb in block_bytes: offs.append(cur); cur+=len(bb)
    offs.append(cur)
    table=b''.join(p32(o) for o in offs); table+=b'\x00'*(hs-len(table))
    return table+b''.join(block_bytes)
```

---

## 4. HOW — control codes

| code | meaning |
|---|---|
| `06 07` | box advance / page break (silent button-advance with PCM off) |
| `08` | newline within a box/page |
| `05` | prologue line-format marker; produces a leading **indent** (omit for flush-left) |
| `04 XX` | dictionary word — **drop** for English. Special: `04 1C`=Winning Conditions, `04 1D`=Losing Conditions; in prologue setup `04 01`+digit+`04 83` renders "SCENARIO-NN" and `04 83`≈ opening 「 |
| `09 XX` | name insert — drop |
| `02` | lord-name insert — drop |
| `03` | prologue title-setup code |

Dialogue box = text between `06 07`, must fit **3 lines × 14 fullwidth chars**.

---

## 5. HOW — fullwidth encoding (CRITICAL)

The renderer only draws 2-byte glyphs. Map every ASCII char to its fullwidth SJIS form (`U+FF01..FF5E`, i.e. `+0xFEE0`), space → `81 40`, and a few punctuation specials. Single-byte ASCII = garbage on screen.

```python
_SPECIAL={0x27:'\u2019',0x22:'\u201d',0x2d:'\u2015',0x60:'\u2018'}  # ' " - `
def sj(s):
    out=bytearray()
    for ch in s:
        c=ord(ch)
        if c==0x20: out+=b'\x81\x40'; continue                 # fullwidth space
        if c in _SPECIAL:
            try: out+=_SPECIAL[c].encode('cp932'); continue
            except: pass
        if 0x21<=c<=0x7e:
            try: out+=chr(0xFEE0+c).encode('cp932'); continue   # ASCII -> fullwidth
            except: pass
        try: out+=ch.encode('cp932')
        except: out+=b'\x81\x48'                                 # fullwidth ?
    return bytes(out)
```

---

## 6. HOW — dialogue overflow re-segmentation

Each script "unit" (one `{00}` string in entry 5) is re-emitted as a chain of ≤3-line display boxes joined by `06 07`, wrapping at width 14. Original control codes are dropped (names spelled out in English). Boxes are mapped positionally onto the **non-empty** units of entry 5.

```python
LB=b'\x08'; ADV=b'\x06\x07'
def encode_box(box, width=14, maxlines=3):     # box = list of pages; page = list of lines
    import textwrap
    screens=[]
    for page in box:
        text=' '.join(page).strip()
        if not text: continue
        lines=textwrap.wrap(text,width,break_long_words=True) or ['']
        for i in range(0,len(lines),maxlines): screens.append(lines[i:i+maxlines])
    if not screens: screens=[['']]
    out=bytearray()
    for si,lines in enumerate(screens):
        for li,ln in enumerate(lines):
            out+=sj(ln)
            if li<len(lines)-1: out+=LB
        if si<len(screens)-1: out+=ADV
    return bytes(out)
```

**Speaker-label detection** (in the dialogue sheet, some rows are speaker labels / stage directions, not dialogue): treat a row as a label if it is multi-word Title-Case or a parenthetical, requiring every word capitalized (so "Oh no" stays dialogue). Validated: 170 labels, 0 false positives.

**6 scenarios are NOT aligned** (box count ≠ non-empty unit count): 3,4,8,9,14,20. Auto-alignment (length-correlation / Needleman-Wunsch) is unreliable — it skips real dialogue. Align manually with the user, or leave Japanese.

---

## 7. HOW — prologues (entry 7)

One string = `setup header` + bracketed `title` + body pages + win/lose conditions, segments split by `06 07`. Method:
- **Preserve the original setup header** verbatim (`05 08 04 01 <digit> 03 08 04 83 …`) — it renders "SCENARIO-NN" and initializes the crawl. Find the `04 83` marker; the title text sits between it and the trailing 」 (`81 76`), optionally wrapped in `05 … 05`. Swap only the title text (keep the `05` wrappers if present).
- **Body + conditions**: wrap to width 14, paginate ~5 lines/page, join lines with `08`, pages with `06 07`. **Do NOT prefix pages with `05`** (it indents the first line).
- **Titles** render centered with 「 」; the title line fits ~12–14 chars, so force-wrap long titles with `08`.
- All 20 confirmed working. The Scenario-NN crawl line is English; the separate "シナリオ N" card before it is a different Japanese asset (not in SCEN).

A standalone HTML "prologue fitter" tool was built so the user can tune wording to the wrap rules and export JSON.

---

## 8. HOW — the 8-char buffer limit (most important gotcha)

Names, item names, and menu labels are copied into a **fixed ~8-fullwidth-char (~16-byte) buffer**. Longer strings overflow it and crash: CPU executes `0x0000` at **`PC 0606B4D8`**.

- Confirmed crashers: "Imperial Commander" (17, character name) on lord-select; long menu messages ("Load which save data?", 21) on save-load.
- Confirmed safe: ≤8-char strings (e.g. "Jessica"=7, item names capped at 8).

**Rules:** all name/label strings ≤8 fullwidth chars. English UI **messages** are longer than their Japanese originals and cannot be translated in these slots — leave them Japanese. (Separate from this, some ≤8 strings still visually overlap in very tight slots — cosmetic, not a crash.)

- **Status-bar names** (bottom of screen) come from a **different table/font path** than entry 1 and are still Japanese — source not yet located.
- **Item descriptions**: the box is a hard **2 lines × 16 fullwidth chars** + a stat line; `08` does NOT grow it. English descriptions (~50 chars) must be trimmed to ~32. (Decision on whether to trim/skip still open.)

---

## 9. HOW — disc rebuild pipeline

Disc geometry (constants discovered for this image): `SCEN_LBA=136946`, old SCEN size `322` sectors, directory-shift threshold `THRESH=137268`, track-1 length `167225` sectors, `RAW=2352`, `U=2048`. The image is MODE1/2352 for track 1; tracks 2–6 follow (one MODE2/2352 + audio).

Steps:
1. **Patch SCEN**: write the new `LANG1_SCEN_overflow.dat`, pad to 2048. `K = new_sectors - 322` (growth).
2. **Build logical ISO**: `prefix(up to SCEN) + new_scen + everything from THRESH on`. (Original logical ISO is `track1.iso`, extracted from the raw bin by stripping MODE1/2352 framing.)
3. **Patch ISO9660 directory records**: walk the dir tree (pycdlib for the layout), then for each record in the raw image bytes — if it points at `SCEN_LBA` with the old size, write the new size (LE at +10, BE at +14); if its extent LBA ≥ THRESH, bump it by `K` (LE at +2, BE at +6).
4. **Patch the PVD** (LBA 16): `volume_space_size += K` (LE at +80, BE at +84).
5. **Re-frame to MODE1/2352**: for each 2048-byte logical sector, if it is unchanged AND not shifted, reuse the original raw 2352 bytes (fast path); otherwise rebuild the sector with sync + MSF header + 2048 data + **EDC + ECC** (ECMA-130 / Corlett `cdecc.build_sector(lba,data)`). Append the raw bytes of tracks 2–6 (shifted by `K`).
6. **Emit `.cue`**: track 1 `MODE1/2352`; tracks 2–6 with their INDEX MSF offsets bumped by `K`. (`msf(lba)= mm:ss:ff` at 75 fps, 4500 sectors/min.)
7. **xdelta3** the rebuilt `.bin` against the original raw `.bin`.

The EDC/ECC math (`cdecc.py`) is standard ECMA-130; reconstruct from any CD-ROM MODE1 sector reference if needed (sync `00 FF*10 00`, MSF+mode header, EDC = CRC-32/MPEG over bytes 0..2063, then P/Q ECC over the 2340-byte block). This was validated against the original.

---

## 10. Build pipeline (commands)

```
python3 build_all.py        # dialogue + prologues + names/items/menu -> LANG1_SCEN_overflow.dat
python3 rebuild_disc.py     # -> new_track1.iso (patched dir + PVD)
python3 final_assemble.py   # MODE1/2352 framing + tracks 2-6 -> Langrisser1_EN_test.bin, writes .cue
xdelta3 -e -9 -f -s "<ORIGINAL_RAW_BIN>" Langrisser1_EN_test.bin <out>.xdelta
```

`build_all.py` assembles everything: `patch_dialogue` for the 14 aligned scenarios, `build_prologue` for all 20, `patch_menu` (≤8 guard), `patch_item_names` (cap 8). **User applies** the xdelta to the original bin, names the result `Langrisser1_EN_test.bin`, loads the `.cue` in SSF, sets **PCM OFF**.

---

## 11. Current status & how to continue each item

- **6 unaligned dialogue scenarios (3,4,8,9,14,20)** — align boxes↔units manually with the user; do not trust automatic alignment.
- **Character names** — translate cleanly for dialogue labels/unit-info, but need **18 short forms (≤8)** for the long ones; **find the status-bar name table** (separate font path) to finish.
- **Item names** — capped at 8 placeholders; need **21 short forms** to finalize.
- **Item descriptions** — 2×16 box; decide trim vs skip, then write desc1/desc2 as two ≤16 lines (no `08`), keep the stat string.
- **Menu** — short labels done; long messages blocked. Big entry-3 menu (503) untouched.
- **Scenario titles (entry 8), quiz, endings, "シナリオ N" card** — not started; quiz/endings/card data locations not yet found.
- **PCM off by default** — save byte at offset `0x24d` (01=on/00=off), checksum at `0x9d`; boot default not yet flipped in code (non-blocking, setting persists once saved).

The two pending short-form lists (the over-8-char character names and item names) are in `PROJECT_NOTES.md`.

---

## 12. Memory map & emulator notes (for further RE)

- SSF (user's main emulator): no debugger, play-test only. Mednafen: read/write memory breakpoints work (Shift+R/W, range `060A0000-060BFFFF`); PC breakpoints did not fire.
- `0.BIN` loads at `0x060A8000`. Dialogue/battle engine overlay `0x06010000–0x06026000`. Text-render engine `~0x0604B000–0x0604E000`. SCEN block loads `~0x060A0000`. Command dispatcher `0x0604B970` (runtime-populated jump table). Box-frame drawer `0x0604CD18`. Word-copy primitive `0x0604D000`. Text drawn as **VDP1 sprites**.
- **Crash buffer**: `PC 0606B4D8`.
- Render-state vars (`0x060A6E00`, `0x060A7C88/90/94`, `0x060A7478`) are **transient** (zero when idle) — static dumps can't capture the cursor (why the half-width patch was abandoned).
- `FONT.DAT` is in VDP VRAM, not in HWRAM dumps.
- Tools: capstone 5.0.7 (`CS_ARCH_SH`, `CS_MODE_SH2|CS_MODE_BIG_ENDIAN`); `xdelta3`; `pycdlib`; `openpyxl`.

---

_This handoff pairs with `PROJECT_NOTES.md` (status/reference). If both are present, this one is the technical "how"; that one is the "what/where"._
