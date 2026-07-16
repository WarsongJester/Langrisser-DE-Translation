# Archive — superseded & historical notes

Everything here is kept for history. Each file has a banner pointing to its current replacement.
The **current** docs are in the parent `docs/` folder. Lineage:

## Story / text references (newest wins)
1. `PROJECT_NOTES.md`, `HACKING_HANDOFF.md` — **Route A** (full-width SJIS) era. The ~8-char
   buffer crash, disc-grow/shift/PVD rebuild. Superseded by Route B.
2. `LANGRISSER_HACKING_REFERENCE.md` — **Route B** breakthrough, Scenario 1 only.
3. `LANGRISSER1_EN_HACKING_REFERENCE.md` — all text done; class names listed "deferred".
4. `LANGRISSER1_EN_MASTER_REFERENCE.md` — newest text ref (EN_45: + conditions + endings; splice-
   in-place via SCEN slack; the cdecc ECC-Q bug). **→ merged into `docs/00_MASTER_REFERENCE.md`.**

## In-battle UI / class-name workstream
5. `BOTTOM_BAR_FONT_NOTES.md` — early bottom-bar font probe; assumed LANG1 relocates (later
   disproven); located the compressed font but didn't crack the codec.
6. `BOTTOMBAR_CONVERSION_CRACKED.md` — bottom-bar byte→glyph conversion cracked; 16×16 panel
   still crashing on out-of-range codes.
7. `LANGRISSER1_CLASSNAMES_MENU_HANDOFF.md` — **alternative** class-name approach (repaint FONT.DAT
   katakana slots; hybrid pair encoding) + the UI menu; bottom bar deferred.
8. `LANGRISSER1_INBATTLE_CLASSNAME_HANDOFF.md` — **final** class-name solution (runtime CPU hook,
   full A–Z, white recolor, confirmed in-game). **→ merged into `docs/in_battle_ui/CLASS_NAMES.md`.**
   See that doc §8 for why it supersedes #7 and why the two must not be combined.

## In-battle menu / codec research
9. `ROUTE1_PROGRESS.md`, `INBATTLE_UI_RESEARCH.md`, `INBATTLE_MENU_DUMP_FINDINGS.md`,
   `BATTLE_MENU_INVESTIGATION.md`, `BATTLE_MENU_STATUS.md` — command/system menu RE.
   **→ merged into `docs/in_battle_ui/MENU_CHROME.md`.**
10. `CODEC_FINDINGS.md` — IMG.DAT codec RE + the key discovery that **LANG1 loads verbatim**.
    **→ merged into `docs/in_battle_ui/IMG_DAT_CODEC.md`** (and is why the class-name hook works).
