# Langrisser I (Sega Saturn, *Dramatic Edition*) — Hacking Handoff
## Session: EN_51 → EN_55 (deployment-menu translation + fixes)

This document records everything reverse-engineered and built in this session. It is written
to stand on its own for a future session (or a reviewer) that has the earlier project docs
(`LANGRISSER1_EN_HACKING_REFERENCE.md`, `FONT_DAT_FORMAT.md`, `SCEN_DAT_FORMAT.md`,
`00_MASTER_REFERENCE.md`, and the in-battle-menu `HANDOFF.md`) but not the chat history.
It assumes familiarity with SH-2 assembly and Sega Saturn VDP2.

---

## 0. TL;DR

The headline result of this session is **EN_55**: the on-map **deployment menu** is now in
English (Hire Troops / Equipment / Position / Sortie, plus the Commanders panel header).
Getting there also produced a chain of smaller fixes (EN_51–54) and one significant piece of
infrastructure: the ring-menu hook and the deployment translation now share a single
per-frame hook, with all glyph storage moved into FONT.DAT.

Shipped patches (all xdelta3 against clean JP `orig.bin`, 656,591,376 B,
md5 `ebcfaacf7a98419f237e5d02bfe62bf6`):

| Build | md5 | What it added |
|-------|-----|---------------|
| EN_51 | `75deba1b1d1ec3343fa2dcf5fbcdddd9` | VS-crash fix, G/B glyph weight, purchase first-view fix |
| EN_52 | `943803e78442fcf15796e3449e3fdb76` | bottom-bar name fix + half-width panel font (crashed on status screen) |
| EN_53 | `ff1906d6117d7a72d4f4e3a8da6d4f0d` | fixed the EN_52 status-screen crash (PR clobber) |
| EN_54 | `79aa9b35341e8d38b145964b04f90bf0` | proper bar **X**, tighter panel word spacing |
| **EN_55** | **`159862d001426667fe7ed82da14fa9fe`** | **deployment menu translated (this is the current build)** |

Apply: `xdelta3 -d -s orig.bin Langrisser1_EN_55_full.xdelta out.bin` → rename to
`Langrisser1_EN_test.bin` → load the `.cue` in Kronos/SSF/Mednafen with **PCM OFF**.
Each build is cumulative (EN_55 contains all of EN_47–54).

---

## 1. Workflow & environment (unchanged, but worth restating)

- **Division of labour:** you supply English text and test in-emulator (fresh boot, PCM off),
  reporting via screenshots / `.yss` save-states. All RE, patching, font work, and disc
  rebuilding is done offline; the game is never run on this side. Every result is verified
  offline (byte diff, EDC/ECC, xdelta round-trip, and simulated render) and in-game effects
  are flagged pending your test.
- **The sandbox filesystem resets between sessions.** Only `/mnt/user-data/outputs/` persists.
  At session start the working set is reconstructed:
  1. `7z e` the disc archive → `orig.bin` (verify md5 `ebcfaacf…`).
  2. `xdelta3 -d` the newest shipped patch onto `orig.bin` → the current base `.bin`.
  3. Extract LANG1.BIN (LBA 202, 413,460 B), FONT.DAT (LBA 135070, 220,732 B),
     0.BIN (LBA 142), IMG.DAT (LBA 134794) by reading 2048-byte user regions from each sector.
  4. Copy the build scripts + `pairmap_en45.json` + `ring_ref_writes.json` + `cdecc.py` +
     `wordblob.py` from the sendoff bundle, and the Toshiba TTF, out of `/mnt/user-data/uploads`.
- **Disc splice:** SCEN.DAT is unchanged since EN_46, so LANG1 and FONT are spliced *in place*
  (they sit before SCEN on disc; nothing shifts). Per changed 2048-byte sector, replace the
  user region and re-frame EDC/ECC with `cdecc.reframe(sector2352, lba)`. Then
  `xdelta3 -e -9` and a `-d` round-trip `cmp` to prove the patch reproduces the build.

**Reconstruct-from-shipped-patch is the canonical base.** Do not assume cached extracts are
current; re-verify each against the base `.bin` by re-reading its sectors.

---

## 2. Disc / memory constants (as used this session)

```
orig.bin (clean JP)   656,591,376 B   md5 ebcfaacf7a98419f237e5d02bfe62bf6
LANG1.BIN   LBA 202     413,460 B   loads verbatim to HWRAM 0x06010000 (file off = CPU-0x06010000)
                                    LANG1 image ends at file 0x64F14; a live ptr sits at 0x64F10
FONT.DAT    LBA 135070  220,732 B   resident in VDP2 VRAM at 0x25E40000 (so FONT off F -> VRAM 0x25E40000+F)
0.BIN       LBA 142     121,852 B
IMG.DAT     LBA 134794  514,624 B   compressed graphics archive (see §5)
SCEN.DAT    LBA 136946  745,472 B   (EN_46 size; unchanged this session)
Kanji slot math: S4=0x3EBC (ku16-62), S5=0x266FC (ku63-83); slot=(ku-lo)*94+(ten-1)
FONT glyph = 16x16 1bpp = 32B; row word=(byte1<<8)|byte0 (byte1=LEFT 8px, byte0=RIGHT 8px)
```

**Kronos `.yss` layout** (both save-states this session share it): LE chunks from 0x14
(tag,ver,size). `VDP2` chunk data starts with a **0x120-byte internal struct header** (NOT raw
registers), then VRAM (0x80000) at +0x120, then CRAM at VRAM+0x100000. `OTHR` chunk = HWRAM
(1 MB, **16-bit byte-swapped**) then LWRAM at +0x100000 (also swapped). CPU HWRAM addr → yss:
`OTHR_data + (addr-0x06000000)`, then byteswap16. **The +0x120 VRAM offset and the HWRAM
byte-swap are the two gotchas that have each cost a test cycle historically — respect them.**

---

## 3. EN_51–54 (the fixes leading up to the menu work)

These were incremental and are documented in their own `EN5x_NOTES.md`; summarised here.

### EN_51 — three fixes
- **VS-screen crash:** an off-by-one in the assembler's `bt` fixup produced a bad branch;
  added the BT fixup. Also house-weight G/B tiles and a purchase-first-view fix
  (MAP_ENTRY + INJG refactor; KWJY made contiguous, clobbering a dead `19 0A` literal).

### EN_52 — bottom-bar names + half-width panel font
- **Commander names:** replaced positional name mapping with **content-keyed JP matching**
  (spreadsheet order ≠ ROM pool order). Added a 12-entry KANA2KANJI bridge for generic roles
  (e.g. テイコクシキカン = 帝国軍指揮官).
- **Half-width panel font:** the status panel's class field rendered full-width; added a
  runtime SH-2 pair-packing routine so two half-width letters share one cell (the "Route B"
  trick applied to the panel). **This build crashed on the status screen.**

### EN_53 — the crash fix
- The panel converter is a **leaf function that never saves PR**. The EN_52 patch used `jsr`,
  which clobbered the caller's return address → wild `rts` → PC = 0xFFFFFFFF. Fix: convert the
  hook to **jmp-in / jmp-out** so PR is never touched. `verify52`'s SH-2 harness now hard-fails
  if the routine uses `rts` or touches PR.

### EN_54 — proper X + word spacing
- **Bar X:** the bottom bar's only native X was the small × used for item counts (what "xELD"
  was borrowing). Added a house-weight X, injected at runtime alongside G and B. To make room,
  the G/B/X source tiles were moved out of LANG1 into free FONT.DAT space (`GBX_VRAM =
  0x25E40000 + 0xDABC`) and the injector reads them from VRAM. Freed 64 B in LANG1.
- **Word spacing:** class-name spaces still went through the full-width path (a 16-px cell,
  reading as a double gap). The converter's space branch now jumps into the pair routine at a
  second entry point (`A_CPU+14`) with the space index preloaded in the jump's delay slot,
  reusing the branch's own dead literal. Pair table grew to 27×27 = 729 entries at FONT
  `0xD4FC`. SILVER KNIGHT dropped from 8 cells to 7.
- **False alarm worth recording:** "Sold▮▮r" and "un it." in a screenshot looked like an EN_52
  font regression. Traced every glyph byte and proved both are **pre-existing EN_46 artifacts**
  (equipment icons overdrawing longer English text; an old mid-word wrap), not regressions.

**The EN_54 base is the starting point for EN_55.** Its LANG1 differs from clean JP in 3,993
bytes; its FONT.DAT carries the 27×27 pair table (0xD4FC, 1458 B) and the GBX block (0xDABC).

---

## 4. EN_55 — translating the deployment menu (the main event)

### 4.1 What the labels actually are
The five deployment labels (兵士配属, アイテム装備, 指揮官配置, 出撃, and the 指揮官 panel
header) are **not stored as text anywhere** — searched SJIS, byte-swapped SJIS, the custom
menu encodings, and every candidate file. They are **pre-rendered bold-kanji graphics**,
decompressed from **IMG.DAT entry 29** into VDP2 VRAM.

### 4.2 The VRAM / tilemap facts (reverse-engineered from `kronos.yss`)
- The menu's pattern-name table (PNT / tilemap) lives in VRAM at **0x8000** (NBG layer).
- Menu-font tiles are **4bpp 8×8**, resident starting at **char# 0 → VRAM 0x28000**
  (i.e. tile *charno* 0x1400). Palette bank 0.
- **A 16×16 label glyph = 4 consecutive tiles**: TL, TR, BL, BR = charno, +1, +2, +3.
- **The pattern-name word is: bits 0–9 = character # (10-bit!), bits 10–11 = flip,
  bits 12–15 = palette.** This is the single most important fact for the build and the cause
  of the first-cut bug (§4.6). The full VRAM tile is `charno = 0x1400 + (entry & 0x3FF)`.
  Original kanji entries are `0x0400 | char#` — i.e. **flip bit set, palette 0**.
- Nibble scheme inside a tile: **0 = background, 3 = main (bold) stroke, 1 = edge/antialias.**
  Because our English tiles use the *same* nibble 3 and the *same* palette bits as the kanji,
  they inherit the identical on-screen colour (white) — no CRAM edits needed.
- Menu box interior = **6 glyph-cells wide (cols 4–15 = 12 half-cells)**; short JP labels are
  padded with real "05Cx" filler tiles. Header row 2/3, the 指揮官 kanji sit at cols 21–26 with
  blank space to col 36.

### 4.3 THE KEY FINDING — shared staging buffer + shared DMA path
The menu PNT is **staged in HWRAM at 0x060765F8** — the *same buffer* the in-battle command
ring uses — and DMA'd to VRAM 0x8000 every frame via **copy_fn @ 0x0604A26C**, invoked at
call-site **file 0x2C0B8 / CPU 0x0603C0B8** (dst literal 0x25E08000 @0x2C0B4, src = staging).
This is the *exact* copy_fn call-site the existing EN_46 ring hook already rewrites (literal →
hook @ 0x06074C30). **So the per-frame hook already runs while the deployment menu is open; it
just gated the menu out.** That collapsed a "crack the IMG.DAT compression" problem into
"extend a hook we already own."

The menu's own tilemap-build loop is at file 0x2BFA4–0x2BFEC (reads a layout source table via
r10 = HWRAM 0x060A1960, glyph source r7-base 0x060755F8). We do **not** touch it — we inject
into the staging buffer just before the DMA.

### 4.4 Storage problem and its solution (the one structural change)
The English tiles (92) needed a home and LANG1 was full (only ~84 contiguous free bytes; the
other "gaps" are zero-runs *inside* live byte tables and are unsafe). Solution: **relocate the
command ring's 36 glyph tiles out of LANG1 into FONT.DAT-VRAM** (FONT is resident, so the
ring's tile DMA just sources from there — same trick EN_54 used for GBX). That frees enough
LANG1 room to fold the deployment logic into the same hook.

The ring DMA was 12 chunks × 96 B (dst += 0x60 per chunk). Relocation kept the chunk order, so
the ring tiles land at the identical VRAM cells and render identically — verified byte-for-byte
(see §4.7). This needed the Toshiba TTF to regenerate the ring tiles; the standalone ring
generator (`build_ring_shared.py`) reproduces the installed hook **byte-identically**, which is
what made it a safe base to extend.

### 4.5 The combined hook (`build_combined.py`)
The hook at **0x06074C30** (554 B; budget 736; the live pointer at 0x64F10 is untouched) now
does, in order:
1. **Prologue** — push r4,r5,r6,r11,r12,r13,r14,pr (unchanged).
2. **Deployment block (new, runs first):**
   - **Gate:** `buf[0x308]==0x043C` (兵 TL tile) AND `buf[0x30C]==0x0440` (士 TL). Two distinct
     graphic-tile values, so nothing else false-fires. (`buf` = r4 = staging base 0x060765F8;
     0x308 = offset of row6/col4.)
   - **Tile upload (every frame):** two `copy_fn` calls uploading the 92 English tiles from
     FONT.DAT-VRAM to VRAM char# region (split 57 + 35 because the free FONT run wasn't big
     enough for 92 contiguous). r4 is saved in r14 across the calls and restored.
   - **Staging-write loop:** 110 entries `{off16, val16}` read from a table in FONT.DAT-VRAM;
     each writes `val` to `buf+off`. 92 entries place the English label cells; 18 clear leftover
     kanji cells to 0x1000 (the game's transparent blank).
   - Falls through into the ring block.
3. **Ring block (unchanged logic):** its gate, write pass (14 descriptors: 10 ring + 4 Order
   sub-menu), and the tile-DMA loop — now with **SRCBASE = 0x25E66F5C** (FONT-VRAM ring block)
   and 12 offsets 0,0x60,…,0x420.
4. **Epilogue:** restore pr + registers, `jmp @copy_fn` (PR preserved so copy_fn's `rts` returns
   to the original caller — identical tail behaviour to EN_46).

Because the deployment tile upload runs every frame, there is **no persistent flag to reset**
(simplest and always correct). If flicker ever appears there, switch to a one-shot upload.

### 4.6 The first-cut bug (colour + leftover kanji) and the fix
The first EN_55 rendered labels **dark/garbled** with kanji fragments left over. Root cause was
a single misread: the pattern-name **character field is only 10 bits**. The first cut placed
tiles at charno 0x1CF2+ (out of the 0x1400–0x17FF window a 10-bit field can address) and zeroed
the flip/palette bits. The hardware masked the char# to the wrong tiles (dark/garbled) and never
overwrote the real kanji (leftovers). **Fix:** tiles now live at **charno 0x1754–0x17AF** (a
172-cell free run inside the window), and each tilemap entry = **`0x0400 | (charno-0x1400)`** —
matching the kanji entries' flip+palette bits exactly. Result: white letters, all kanji cleared.

### 4.7 Verification (all offline)
- `verify52` PASS (198 class names convert, 0 fail; SILVER KNIGHT = 7 cells; digit path; the
  converter diff is exactly the intended bytes) and `verify51` PASS (battle X/G/B injection).
- EN_54 **pair table (FONT 0xD4FC) and GBX block (0xDABC) byte-identical** in the new FONT.
- Ring **write descriptors byte-identical** to EN_54; ring **gate constants** unchanged.
- **Ring tiles byte-identical** after relocation (36/36), landing at the same VRAM cells.
- LANG1 diff vs EN_54 confined to the hook region (0x64C30–0x64F10) and the 9 cleared ring-tile
  gaps — no unexpected diffs.
- Deployment staging table (110 writes) decodes to the intended cells; a full **simulated
  render** of the menu produces all five labels correctly, all charnos in-range.
- EDC/ECC fixed-point on all changed sectors; xdelta reproduces the build bit-for-bit.

### 4.8 EN_55 changed disc sectors
LANG1 LBAs **394, 403**; FONT LBAs **135124, 135125, 135147, 135148, 135149**.

---

## 5. IMG.DAT compression (investigated, not needed, but mapped for the future)

The deployment fix deliberately **avoids** cracking this, but the investigation is recorded
because the シナリオ intro card and other pre-rendered graphic text likely live here.

- IMG.DAT (LBA 134794, 514,624 B) loads verbatim to **LWRAM 0x00200000**. It is a **207-entry
  archive**: a BE u32 offset table (0x33C bytes) then per-entry `{u16 header ≈0xC001, u16, data}`.
- **Entry 29 = the deployment menu font**, uploaded to VRAM 0x28000. The loader wrapper is at
  LANG1 **0x1850**; it enqueues a job to a command-queue writer at LANG1 **0x3A238** (siblings
  0x4A26C/0x4A2A0/0x4A2D4 for other queue types). The queue ring is around **0x060A6908**
  (tail ptr var 0x060A690C, go-flag 0x060A6910).
- The **dispatcher** is at LANG1 **0x3A0C4** (a 5-entry jump table dispatches job types 1–5),
  and the actual **decompression worker** is at LANG1 **0x3A308** (sets up a control block and
  calls sub-decompressors via a bsr table at 0x3A3A4). Decompression is **asynchronous** — the
  loader only enqueues; the worker runs later (some of it on the slave SH-2, whose code wasn't
  located).
- Format is **not** a plain 2bpp→4bpp expansion (tested and rejected) and **not** a standard
  LZSS variant (brute-forced against known plaintext — the decompressed font from a save-state —
  with no hit). Cracking it needs either the slave-SH-2 worker located, or a longer
  known-plaintext attack with the correct pairing. **Deferred; injection sidesteps it entirely.**

---

## 6. Tools & files (in `/mnt/user-data/outputs/`)

New / updated this session:
- `Langrisser1_EN_55_full.xdelta` — the current shipped patch.
- `build_combined.py` — the **combined ring + deployment hook generator**. Extends
  `build_ring_shared.py`: relocates the 36 ring tiles to FONT.DAT, adds the deployment gate +
  two-part tile DMA + 110-entry staging-write loop, emits `hook_shared.bin` + meta + the
  FONT.DAT writes (ring tiles, deploy tiles, staging table).
- `hook_shared.bin` — the assembled 554-byte combined hook.
- `deploy_data.pkl` — `(tiles[92×32B], staging_writes[110×(off16,val16)], charno0=0x1754)`.
- `font_allocs.pkl` — FONT.DAT layout: RING36 @0x26F5C, TILES92_A @0x273DC, TILES92_B @0x1B29C,
  STAGETAB @0x1B6FC.
- `build_classnames.py`, `build_pairs.py`, `hookgen.py`, `verify51.py`, `verify52.py`,
  `paircode_map.json` — the EN_54 class-name / panel-font toolchain (carried, still passing).
- `EN51_NOTES.md … EN55_NOTES.md` — per-build notes.
- `en55_deploy_preview.png` — simulated in-game render of the finished menu.

Reused from the July-3 sendoff bundle (`sendoff/`): `build_ring_shared.py`, `wordblob.py`
(renders the Toshiba 8×16 glyphs; **requires `MxPlus_ToshibaSat_8x16.ttf`**), `cdecc.py`
(`reframe(sector2352, lba)` — import plainly, never double-`exec`), `memimg.py`,
`ring_ref_writes.json`, `pairmap_en45.json`, and the EN_46 xdelta.

---

## 7. Key constants (combined hook + deployment)

```
copy_fn                0x0604A26C   call-site literal @ file 0x2C0B8 (CPU 0x0603C0B8), dst 0x25E08000
combined hook entry    0x06074C30   (file 0x64C30), 554 B, budget 736 (live ptr @0x64F10)
staging buffer (HWRAM) 0x060765F8   shared by command ring AND deployment menu
deployment gate        buf[0x308]==0x043C (兵) AND buf[0x30C]==0x0440 (士)
menu PNT (VRAM)        0x8000       pattern-name word: bits0-9 char#, 10-11 flip, 12-15 palette
                                    full charno = 0x1400 + (entry & 0x3FF); kanji entry = 0x0400|char#
menu font tiles        char# 0 -> charno 0x1400 (VRAM 0x28000), 4bpp 8x8, pal 0, stroke nibble 3
English tiles          charno 0x1754-0x17AF (in-window free run), entry 0x0400|(charno-0x1400)
FONT.DAT (VRAM base)   0x25E40000
  RING36 (relocated)   FONT 0x26F5C  VRAM 0x25E66F5C  (36 tiles = 12 chunks x 96B; ring DMA SRCBASE)
  TILES92_A (57)       FONT 0x273DC  VRAM 0x25E673DC  -> VRAM dst 0x25E2EA80 (charno 0x1754)
  TILES92_B (35)       FONT 0x1B29C  VRAM 0x25E5B29C  -> VRAM dst 0x25E2F1A0
  STAGETAB (110x4B)    FONT 0x1B6FC  VRAM 0x25E5B6FC  (deployment {off16,val16} table)
EN_54 regions in FONT  pair table 0xD4FC (729 words), GBX block 0xDABC (both preserved)
IMG.DAT loader/queue   loader 0x1850; queue writer 0x3A238; dispatcher 0x3A0C4; worker 0x3A308
IMG.DAT in RAM         verbatim at LWRAM 0x00200000 (207-entry archive)
```

---

## 8. Hard-won lessons from this session (read before changing anything)

1. **The pattern-name char field is 10 bits.** Tiles you reference from the menu tilemap MUST
   have charno in 0x1400–0x17FF, and the entry MUST carry the kanji's flip+palette bits
   (`0x0400`). Getting this wrong masks to the wrong tile (dark/garbled) AND leaves the original
   graphic in place. This was the entire first-cut EN_55 bug.
2. **Match the original entry format to inherit colour.** Don't try to pick a "white" palette
   index from the save-state CRAM (its byte order is ambiguous). Use the same nibble (3) and the
   same palette bits the kanji use; the letters then render identically by construction.
3. **The deployment menu and command ring share one staging buffer and one DMA path.** That is
   why one hook can serve both. Verify any new menu the same way: search HWRAM (byte-swapped)
   for the tilemap row you see in VRAM; if it's in a 0x0607xxxx buffer, the copy_fn hook reaches it.
4. **LANG1 is full.** The only real free space is ~84 contiguous bytes; the other zero-runs are
   inside live tables and corrupt graphics if written. Put new *data* (tiles, tables) in
   FONT.DAT-VRAM and keep new *code* minimal. Relocating existing tiles to FONT.DAT is the lever
   that frees LANG1 room.
5. **Regenerate-and-diff proves safety.** `build_ring_shared.py` reproduces the installed ring
   hook byte-for-byte; that is what made extending it trustworthy. Any change to the shared hook
   must re-verify: ring descriptors identical, ring tiles identical, ring gate constants
   identical, EN_54 FONT regions identical.
6. **Async decompression means "after load" ≠ "at loader return".** The IMG.DAT loader only
   enqueues; tiles aren't in VRAM when it returns. A per-frame hook (which runs after the DMA)
   is the correct injection point, not the load routine.
7. **Alignment and PR discipline still bite** (from EN_52/53): SH-2 word/long reads need aligned
   addresses (misaligned = shifted garbage, not a fault); leaf routines don't save PR, so hook
   them jmp-in/jmp-out, never `jsr`.

---

## 9. Status & what's open

**Done and confirmed in-game (yours to re-confirm for EN_55):**
- All story text (dialogue, prologues, names, items, quiz, tutorial, conditions, endings).
- In-battle command ring + Order sub-menu.
- Bottom-bar class names, panel half-width font, proper X, word spacing (EN_51–54).
- **Deployment menu (EN_55)** — Hire Troops / Equipment / Position / Sortie / Commanders.

**Open / optional:**
- **Deployment menu final in-game confirmation** (colour + no leftover kanji + ring/panel
  regression check). Everything is verified offline; only the live check is outstanding.
- **In-game class names** on the bottom status bar and 16×16 class/status panel — the separate
  custom-encoding renderers; still the largest deferred item (needs the 16×16 conversion cracked
  and the VDP2 half-width font's missing Latin letters added). See the class-name track docs.
- **シナリオ N intro card** and other pre-rendered graphic text — same IMG.DAT archive; would
  need either the compression cracked (§5) or the same injection approach applied.
- **SCEN entry-4 place names** — last documented story-text backlog item.
- Deployment tile upload runs every frame; switch to one-shot if any flicker is observed.
