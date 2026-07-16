# Langrisser I EN — Crash Investigation Send-Off (EN_55 → EN_63)

Single-session record of the load/new-game crash hunt and its resolution.
Authoritative for what was tried, what was proven, and what remains. All builds
are xdelta3 vs clean JP `orig.bin` (md5 `ebcfaacf7a98419f237e5d02bfe62bf6`).

---

## 1. The presenting problem

- **Symptom:** Clicking **Load** or **New Game** from the title screen threw a
  MasterSH2 crash: **PC = 0x00000002, code = 0200 ("Unknown code")**.
- **Cross-emulator:** eventually the key clue. **Kronos** reached the load screen;
  **SSF** crashed; **Mednafen** froze before the title.
- **Starting build:** EN_55. The crash signature (indirect call through a ~0
  pointer) matched the project's long-documented 16×16-blitter failure mode.

---

## 2. What we shipped, in order

| Build | Change | Result |
|-------|--------|--------|
| EN_56 | Buffer gate at hook entry (2nd buffer passed through) | not tested |
| EN_57 | Restored title bars, two-word main gate | crashed (same spot) |
| EN_58 | FONT-residency check + sub-screen context gate | crashed (same spot) |
| **EN_59** | **Kana-clamp guard** on the 16×16 converter | **Kronos fixed; SSF still crashed** |
| EN_60 | Moved converter's pair-row read out of VRAM into HWRAM | SSF still crashed |
| EN_61 | Diagnostic: hook install reverted (hook dormant) | optional bisect tool |
| **EN_62** | **Rebased on EN_54** (SSF-proven) + kana clamp | **crash gone both emulators; background missing** |
| **EN_63** | **Clamp stub relocated off a live window struct** | **current build — expected clean** |

The three dispatch-theory builds (56/57/58) were ultimately a wrong branch: the
save states proved the hook dispatch was never the cause.

---

## 3. The decisive evidence — three Kronos save states

Tim supplied `titlescreen.yss`, `loadscreen.yss`, `working.yss`. Parsing them
(helpers in `parse_yss.py`) settled the direction of the whole investigation:

1. **EN_58 loads and installs perfectly.** In-RAM LANG1 at the title screen was
   byte-identical to the disc image (only known runtime regions differed). The
   CD-load path, EDC/ECC, and hook install were all exonerated.
2. **The hook is passive on the real load screen.** Replaying the EN_58 dispatch
   against the actual staging-buffer bytes from the state: no gate matched,
   nothing ran. Dispatch design was never the killer.
3. **The crash is intermittent.** `loadscreen.yss` was EN_58 *alive on the load
   screen*. A crash that sometimes doesn't fire was almost certainly never a
   Rev-3 regression — every build since the class-name work carried the latent
   hole, and earlier builds simply got lucky on the visits that were observed.

Also mapped from the states (useful for future work): the master→slave DMA
architecture — producer `copy_fn` family at `0x0604A26C/A2A0/A2D4` (job types
3/5/4) writing 16-byte `{type,dst,src,count}` records at HWRAM `0x06008000+`,
tail ptr `0x060A690C`, flag byte `0x060A6910`; consumer is the **slave SH-2**
running an LWRAM program at `0x20293400` with a per-type handler table at
`0x20297400`, booted via an SMPC routine at LANG1 file `0x39684`.

**.yss parsing crib (proven):** chunks from offset 20 as `[tag4][u32 ver][u32
size][data]` — CART, CS2, MSH2, SSH2, SCSP, SCU, SMPC, VDP1, VDP2, OTHR.
**HWRAM** lives in OTHR, **16-bit byte-swapped**, locate via
`swap16(LANG1_orig[0x1000:0x1040])`, base = hit − 0x11000. **LWRAM** = HWRAM
base + 0x100000, also swapped. **VDP2 VRAM**: FONT visible at chunk offset
`0x40000 + 0x120 + font_file_offset`, raw byte order. **MSH2/SSH2 regs**: R0–R15
LE u32 at +0x00–0x3C, then SR, GBR, VBR, MACH, MACL, PR, **PC at +0x58**.

---

## 4. Root cause #1 — the kana hole (fixed the Kronos crash)

The EN class-name patch to the 16×16 renderer (EN_47–54 era) **removed the
original kana path**. The patched converter handles:

- byte 32 (space) and bytes 48–90 (digits, punctuation, A–Z) — inline, safe;
- bytes < 48 — mapped to `0x821F + c`, valid original codes — safe;
- **any byte > 90** (lowercase, half/full-width kana, any SJIS lead/trail byte)
  → treated as pair-table row `(c − 65) × 27`, indexing **past** the 27×27
  (729-word) pair table at FONT `0xD4FC` / VRAM `0x25E4D4FC` → garbage word →
  garbage glyph code → 16×16 blitter's corrupted indirect call → **PC = 2**.

**Fix (EN_59+):** a 28-byte guard stub — any byte > 90 is routed to the space
path (`r0 = 26`, pair cell [26][26], always in range). The renderer's
other-handler literal at file `0x1B320` is repointed to the stub; the
uppercase/digit/space paths are untouched, so every class name renders exactly
as before. Kana/lowercase now draw as blanks instead of crashing.

Confirmed by converter simulation: uppercase output unchanged; kana / SJIS /
lowercase inputs move from out-of-range reads to in-range. Kronos went clean at
EN_59.

---

## 5. Root cause #2 — the EN_54→EN_55 hook rewrite (the SSF crash)

EN_59 fixed Kronos but SSF kept crashing identically. The bracket test was
decisive: **EN_54's load screen works in SSF.** The full-disc diff EN_54 → EN_55
is only **seven sectors**, and the hook *install literal is not among them* —
EN_54 runs the same hook, same address, same mechanism, fine in SSF. So the SSF
crasher lives entirely in the seven-sector content delta:

- LANG1 LBA 403 — the hook body (EN_54 ring-only → EN_55 extended
  deployment/title hook);
- LANG1 LBA 394 — ring tiles removed from LANG1 gaps;
- FONT ×5 — tables restructured; ring tiles + title tables moved into FONT VRAM.

Disassembling EN_54's hook showed the safe pattern: it gates on staging-buffer
words, uses an **inline HWRAM data table** for ring labels, and issues 12–13
small queued DMAs sourced from **LANG1 gaps (HWRAM)** — **no VRAM-resident
tables, no VRAM sources.** EN_55 moved that machinery into FONT VRAM and added a
VRAM-resident write loop — the family of accesses SSF (and real hardware) treat
strictly during active display. (This also killed the earlier queue-overflow
theory: EN_54 queues 13 jobs per ring activation and SSF is fine.)

**Decision:** stop debugging EN_55's hook build-by-build. **EN_62 rebases
wholesale onto EN_54** — identical everywhere except those seven sectors (same
SCEN, same script, same class names, same working command ring, all SSF-proven)
— and grafts on only the independently-proven kana clamp. The converter bytes
are identical between EN_54 and EN_55, so the same hole existed there and the
same stub fixes it.

**Trade-off:** EN_62/63 drop EN_55's deployment-menu tile labels and sub-screen
title bars (which never demonstrably worked outside Kronos). Those will be
rebuilt on the EN_54 pattern — tables and tile sources in HWRAM/LANG1, never
FONT VRAM.

---

## 6. Root cause #3 — the stomped window structure (missing background)

EN_62 killed the crash in **both** emulators, but the load-screen background
graphics vanished (text intact). Cause: EN_62's clamp stub was placed at
`0x0607065C`, which *scanned* as a zero gap but is the zero-initialized tail of
a **display/clip-window parameter block** at `0x60620–0x60656` (the `013F 00DF`
in it is 319×223 — full-screen window coords). Stamping code there programmed
garbage window parameters and the VDP2 background layer got clipped away —
deterministic, hence identical on SSF and Kronos.

**Fix (EN_63):** the same stub relocated to `0x0607291C`, a gap in the
class-strings sector verified three ways — zero in the original, zero in EN_54,
and **referenced by nothing** (no literal in all of LANG1 resolves into it; no
class-pointer-table entry lands in it). LBA 394 (ring tiles + window struct) is
byte-identical to EN_54 again. Total delta from pure EN_54: 27 bytes of stub + a
4-byte literal.

**Lesson banked:** zero bytes are not free bytes. A reuse gap must be proven
*unreferenced*, not merely empty — confirm against all code literals *and* the
255-entry class pointer table before writing.

---

## 7. Current build — EN_63

- **Patch:** `Langrisser1_EN_63_full.xdelta` → result md5
  `9e3d420aaef3b7a90d1b90550ee7849e`.
- **Content:** EN_54 (SSF-proven load path + working command ring) + kana clamp
  at `0x0607291C`, renderer literal `0x1B320 → 0x0607291C`.
- **Verified offline:** stub disassembles correctly; diffs vs EN_54 are exactly
  the 27-byte stub + 4-byte literal, nothing else; EDC/ECC valid on touched LBAs
  256 + 399; xdelta round-trips byte-exact.
- **Expected in-game:** load screen background restored, no crash, class names
  render as before; kana/lowercase draw as blanks on the 16×16 screens.

Apply → rename output `Langrisser1_EN_test.bin` → load the cue → PCM OFF →
fresh boot. Given the historical intermittence, test Load and New Game a few
times each, in both SSF and Kronos.

---

## 8. Guard stub reference (as built in EN_63)

```
0607291C  E05A   mov   #90,r0
0607291E  3706   cmp/hi r0,r7        ; T = (char > 90)?
06072920  8902   bt    .clamp
06072922  D103   mov.l ORIG,r1
06072924  412B   jmp   @r1           ; in-range -> original handler
06072926  0009   nop
06072928  D102   .clamp: mov.l SPACE,r1
0607292A  412B   jmp   @r1           ; out-of-range -> space path
0607292C  E01A   mov   #26,r0        ; delay: pair-table row = 26
0607292E  0009   nop
06072930  0607 1C00   .long 0x06071C00   ; ORIG  (original handler)
06072934  0607 1C0E   .long 0x06071C0E   ; SPACE (space entry, r0=26)
```

Repointed literal: LANG1 file `0x1B320` = `0x06071C00` → `0x0607291C`.

---

## 9. Open items

1. **Rebuild the EN_55 deployment/title feature on the EN_54 pattern** — labels
   and tile sources in HWRAM/LANG1 gaps, no FONT-VRAM residency, no per-frame
   VRAM writes. This is the one capability EN_63 gives up vs EN_55.
2. **Mednafen freeze before title** — still suspected to be the PCM issue (a
   fresh Mednafen profile has neither the PCM-off save byte nor the setting),
   not a code regression. Open question: has *any* EN build ever passed the
   title in Mednafen? If none has, it's PCM, pursued separately.
3. **Direct clamp confirmation** — a save with a kana lord name, opened to its
   status/class screens, is the cleanest in-game test of the guard.
4. **Long-standing limitation** — the bottom-bar VDP2 half-width font is missing
   `B F H J K L V W Y` and most lowercase; full in-game class names need that
   font extended plus the 16×16 conversion fully reversed (deferred).

---

## 10. Key constants (this session)

```
Crash sig     : MasterSH2 PC=0x00000002 code=0200 (indirect call via ~0 ptr)
Converter     : 16x16 renderer; handler 0x06071C00, space entry 0x06071C0E,
                pair table VRAM 0x25E4D4FC (FONT 0xD4FC), 27x27 = 729 words
                renderer other-handler literal: LANG1 file 0x1B320
Clamp stub    : EN_63 @ 0x0607291C (file 0x6291C); routes byte>90 -> row 26
LANG1         : LBA 202, 413,460 B, base 0x06010000; hook sector LBA 403
FONT          : LBA 135070, VRAM base 0x25E40000
EN_54->EN_55  : 7 sectors — LANG1 LBA 394,403 + FONT LBA 135124-5,135147-9
EN_54 hook    : gates on buffer words; inline HWRAM label table; 12-13 small
                DMAs from LANG1 gaps; NO VRAM tables/sources (SSF-safe pattern)
Window struct : LANG1 file 0x60620-0x60656 (013F 00DF = 319x223) — DO NOT reuse
Safe gap      : LANG1 file 0x6291C (zero in orig+EN_54, unreferenced)
DMA queue     : producer copy_fn 0x0604A26C (types 3/5/4 at A26C/A2A0/A2D4),
                jobs @0x06008000, tail @0x060A690C, flag @0x060A6910;
                slave consumer LWRAM 0x20293400, handler table 0x20297400
Builds        : EN_63 md5 9e3d420aaef3b7a90d1b90550ee7849e
                EN_62 md5 ccfca1a41854b37bf64103691632a294
                EN_60 md5 9521fe04e1f6e4212a6361a2bb10da54
                EN_59 md5 a64197181249086935244080b306b0ac
```

---

## 11. Artifacts in `/mnt/user-data/outputs/`

- Patches: `Langrisser1_EN_63_full.xdelta` (current), `…_EN_62_full.xdelta`,
  `…_EN_60_full.xdelta`, `…_EN_59_full.xdelta`,
  `…_EN_61_UNHOOKED_TEST.xdelta` (diagnostic), plus EN_56/57/58.
- Notes: `EN63_NOTES.md`, `EN62_NOTES.md`, `EN60_NOTES.md`, `EN59_NOTES.md`,
  and this `EN63_SESSION_SENDOFF.md`.
- Tooling: `parse_yss.py` (.yss chunk/HWRAM/LWRAM/VRAM/reg parser), `sh2.py`
  (SH-2 disassembler helper), `cdecc.py` (Mode-1 EDC/ECC reframing), `edcscan.c`
  (whole-track EDC + MSF validator), `build_en59.py`, and the investigation
  state doc `CRASH_INVESTIGATION_STATE.md`.
```
