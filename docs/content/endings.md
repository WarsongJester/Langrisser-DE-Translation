# Character Endings / Epilogues — Translated (EN_45)

**Patch:** `Langrisser1_EN_45.xdelta` (supersedes EN_44 — includes the conditions **and** the
endings). Disc size unchanged; splice-in-place.

## What this is
The post-game character epilogues ("what became of each hero") — **50 epilogue strings** in
**SCEN.DAT block 17, entry 9**. This is the only displayed SCEN-backed text that was still
Japanese after the conditions pass. Covers the full cast and their branching fates: the knight
(Knight Commander / Anzel border patrol), the court mage (Ledin's advisor / law-giver /
assassinated / grimoire), Taylor (Baldea navy / pirate), Narm (sword mastery / cult),
Lance (demons of Velzeria / amnesia / founds a kingdom), Chris (marries Ledin, first prince),
and Ledin (king, re-seals Langrisser, unifies the continent).

## Source & encoding
- English from your `langendings.xlsx` — 50 `<>`-delimited blocks, `<clsr>` = page break.
  Parsed 1:1 onto the 50 game strings (exact match).
- Re-wrapped to **28 half-width chars/line, 3 lines/box** (the established Route B box),
  paginated with `{06}{07}`; your `<clsr>` breaks are honoured as box boundaries.
- Route B half-width; reused existing pairs + **6 new glyphs** (10 total with the conditions),
  all in **blank font slots** (safe).
- SCEN grew to **355 sectors** — within SCEN's 364-sector ISO allocation, so still spliced in
  place (no file shifting, no ISO/PVD edits). EDC/ECC clean on all touched sectors; patch
  reproduces the build byte-for-byte.

## Test
Apply `Langrisser1_EN_45.xdelta` to the clean JP `.bin` → rename `Langrisser1_EN_test.bin` →
load the `.cue` in SSF (PCM OFF) → reach the ending sequence.

**Please verify in-game:** I wrapped the epilogues to the same box geometry as dialogue
(28 half-width × 3 lines). If the ending screen's text box is a different width or shows a
different number of lines, some lines may clip or the boxes may paginate oddly — tell me the
actual geometry and I'll re-wrap. Everything else (line breaks, box advances) follows your
`<clsr>`/`<>` markers.
