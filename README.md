# Langrisser I (Sega Saturn, *Dramatic Edition*) — English Fan Translation

A from-scratch English fan translation of **Langrisser I**, the first half of *Langrisser –
Dramatic Edition* (Sega Saturn, Japan-only). Langrisser II on the same disc is untouched.

All work ships as **xdelta3** patches against the clean Japanese disc image — no ROM/ISO is
redistributed here, only the diffs, the tooling used to produce them, and the reverse-engineering
notes that got us there.

## Current status

- **Latest build: `patches/Langrisser1_EN_63_full.xdelta`** — see
  `docs/sessions/2026-07-16_en63_crash_investigation.md` for exactly what's fixed (a
  load/new-game crash on hardware-accurate emulators) and what's still open.
- Story text (dialogue, prologues, names, items, scenario titles, conditions, endings, quiz,
  battle tutorial), in-battle command ring + Order submenu, the on-map deployment menu, and
  in-game class names (A–Z) are all translated and merged into the current build.
- Known limitation: the bottom-bar half-width font is still missing several letters and most
  lowercase, so kana/lowercase class-name input renders blank rather than crashing. See the
  open items in the EN_63 session doc.

**Read `docs/00_MASTER_REFERENCE.md` first** — it's the single source of truth for disc/file
formats, the text-encoding technique (Route B), the build pipeline, and translation status.
`docs/sessions/` then carries the story forward chronologically from there (June 23 – July 16).

## Applying a patch

```
xdelta3 -d -s <clean_JP.bin> patches/Langrisser1_EN_63_full.xdelta out.bin
# rename out.bin to match the FILE line in patches/Langrisser1_EN_test.cue
# load the .cue in an emulator with PCM audio OFF
# (Kronos and SSF both verified; Mednafen may freeze pre-title -- unrelated open issue)
```

The clean Japanese `.bin` is **656,591,376 bytes**, md5 `ebcfaacf7a98419f237e5d02bfe62bf6`. It is
not included in this repository -- supply your own dump.

## Editing the script

**`langtool/`** is the current, self-contained tool for reading and rewriting Langrisser I's
text directly on a disc image -- extract to plain `.txt`, edit, reinsert, repackage as a patch.
Start with `langtool/README.md`. A ready-made extraction of the script (as of EN_46) is included
in `langtool/script_en46/` so you can start editing without a disc image.

## Repository layout

```
docs/
  00_MASTER_REFERENCE.md   authoritative: formats, build pipeline, translation status
  format_specs/            SCEN.DAT / FONT.DAT container specs
  in_battle_ui/            class names, menu chrome, the IMG.DAT codec
  content/                 per-batch translation records (battle text, conditions, endings)
  sessions/                chronological session handoffs, June 23 - July 16 (post-toolkit work)
  archive/                 superseded early-project notes, kept for history (banner-tagged)
langtool/                  current script extraction/edit/reinsertion tool + extracted script
tools/                     the wider RE toolchain: disc/ISO helpers, SH-2 disassembly, font and
                           codec tooling, menu-ring hook generator, content builders
patches/                   all shipped xdelta3 patches + PATCH_MANIFEST.md + the test .cue
reference_images/          font/glyph-index maps and RE renders
build_artifacts/           intermediate FONT_en.DAT / SCEN_en.DAT / hook binaries (regenerable)
fonts/                     MxPlus_ToshibaSat_8x16.ttf -- source font for the half-width glyphs
assets/                    misc previews (e.g. deployment-menu screenshot)
```

## Workflow

Translator supplies English text and tests builds in emulators (SSF / Mednafen / **Kronos**,
always **PCM audio off**); the tooling in this repo does all reverse engineering, text encoding,
disc rebuilding, and patch generation offline. Every patch is verified offline (byte round-trip,
EDC/ECC validity) before being handed back for in-game testing.

## License / disclaimer

Fan translation project for personal/community use. No original Sega Saturn disc image,
copyrighted game assets, or commercial ROM data is included here -- only original tooling,
diffs, and documentation produced by this project.
