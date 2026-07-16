# Langrisser I Script Tool (langtool)

Extract, edit, and reinsert the Langrisser I script directly on a Sega Saturn
disc image (`.bin`, MODE1/2352). Works on the clean Japanese disc **and** on the
English builds (it reads the Route-B pair glyphs straight out of FONT.DAT, so it
decodes the packed English text with no extra data files).

## Requirements
- Python 3 (no third-party packages needed)
- The three files in this folder kept together:
  `langtool.py`, `cdecc.py`, `letterglyphs.json`

## Recommended workflow

Work on top of the current English build (EN_46), because its SCEN.DAT has a
larger on-disc allocation than the clean Japanese disc:

```
xdelta3 -d -s CLEAN_JP.bin Langrisser1_EN_46_full.xdelta en46.bin

python3 langtool.py extract en46.bin  myscript      # pull script -> .txt files
  ... edit the .txt files in myscript/ ...
python3 langtool.py check   en46.bin  myscript      # validate only (fast)
python3 langtool.py insert  en46.bin  myscript out.bin
```

`out.bin` is a complete, playable image (EDC/ECC recomputed). Use it with the
existing EN `.cue`. To share it as a patch:

```
xdelta3 -e -9 -f -s CLEAN_JP.bin out.bin MyTranslation.xdelta
```

A ready-made extraction of the EN_46 script is included in `script_en46/` so
you can start editing immediately.

## The script files

```
globals/     0_menu.txt   1_names.txt   2_items.txt   3_debug.txt
             4_places.txt 8_scenario_titles.txt
scenarios/   sNN_dialogue.txt  sNN_winlose.txt  sNN_prologue.txt   (NN = 01..20)
extra/       quiz.txt  battle_tutorial.txt  b20_prologue.txt
```

File format:

```
### 12                <- string number. NEVER renumber, add, or delete headers.
First line of text    <- a plain line break = in-box line break
Second line
<page>                <- box break (next message box), alone on its own line
Text of the next box
```

- Lines starting with `#` (other than `###`) are comments and are ignored.
- `{..}` tags such as `{05}`, `{02}`, `{04:C3}`, `{09:0A}` are engine control
  codes (name inserts, dictionary words, formatting). Keep them exactly as
  found; move them with their text if you rearrange a line.
- Two consecutive ASCII spaces = one blank screen cell.
- Japanese appears as literal kanji/kana and may be freely replaced with
  English. Mixed English/Japanese on one line is fine.
- An empty string is just a `### N` header with nothing under it.

## Limits (enforced by `check`/`insert`)

| Where | Limit |
|---|---|
| dialogue / quiz / tutorial | 28 characters per line, 3 lines per box |
| names (1_names.txt) | 16 characters (hard engine buffer — longer crashes) |
| item names (2_items.txt, strings 0–36) | 16 characters |
| item description lines (strings 37+) | 32 characters per line, no `<page>` |
| whole script | must fit SCEN.DAT's on-disc allocation (the tool checks) |

`4_places.txt` mixes place names with victory-condition strings; keep the place
names themselves to 16 characters to be safe.

The character set for English text is:

```
 !"'()*+,-.0123456789:;?A-Z a-z
```

Anything outside this set that exists in SJIS (kanji, kana, ★, etc) is encoded
as a full-width character taking a whole cell. Characters outside SJIS (é, …)
are rejected with the exact file/line.

## What the tool does under the hood

- Finds FONT.DAT / SCEN.DAT via the ISO9660 directory (no hardcoded LBAs, so it
  works on any build of the disc).
- Decodes text: SJIS for Japanese; for English it OCRs each kanji-bank glyph in
  FONT.DAT against the known Toshiba 8×16 letter shapes and recognizes
  letter-pair glyphs automatically.
- On insert, it re-encodes every string, reusing existing pair glyphs and
  composing new ones for pairs your edits introduce. New glyphs are allocated
  only in kanji slots that are not referenced by SCEN.DAT, LANG1.BIN, or 0.BIN
  (so the world map, class names, and remaining Japanese are never disturbed).
- Splices FONT.DAT and SCEN.DAT back into a copy of the image and recomputes
  the Mode-1 EDC/ECC of every touched sector.
- It never moves files or resizes the ISO: if your text outgrows SCEN.DAT's
  allocation it stops with a byte count to trim. (The EN_46 base has roughly
  60 KB of headroom, so this is unlikely to bite.)

## Notes

- Editing a *global* file (everything under `globals/`) writes the change into
  all 21 script blocks automatically — that duplication is how the game stores
  them.
- Inserting a full English script into the **clean Japanese** disc will fail
  the size check (its SCEN allocation is smaller). Always build on the EN base.
- `3_debug.txt` is the debug/sound-test menu; translating it has no in-game
  effect and it can be ignored.
