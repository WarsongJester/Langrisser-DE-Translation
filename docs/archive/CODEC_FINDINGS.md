> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> IMG.DAT codec findings — merged into docs/in_battle_ui/IMG_DAT_CODEC.md.
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# IMG.DAT Codec — Reverse-Engineering Findings (this session)

## What the menus actually are
The in-battle **command menu** (Move/Attack/Magic/Cure/Command) and **system menu**
(Save/Load/Victory/Settings/End Phase) are **pre-rendered 4bpp graphics**, not SJIS text.
They live in **LANG1/IMG.DAT** (disc LBA 134794), the compressed asset archive
(207-entry big-endian uint32 offset table; every asset begins 0xC0). Translating them
means editing graphics inside this archive — which requires cracking its compression.

## Matched pair obtained
`VDP2VRAM.bin` (Mednafen, option menu open) confirms **asset 0 = the bottom-bar font**,
decompressed at **VRAM 0x20000** (verified by rendering: A T D F M P V H P L, digits,
katakana, TURN/SCEAIO, bold digits). So we now have a known
(compressed asset0 = IMG.DAT[0x33C:0xCF2], 2486 B) ↔ (decompressed 8192 B @ VRAM 0x20000) pair.

## The codec is NOT LZSS — it is a stateful Huffman+LZ (LZH-family) coder
Exhaustively tested and VALIDATED against the real output (all fail past the trivial
33-byte leading-zero run):
- byte-aligned LZSS (output-relative AND 4K ring buffer)
- continuous-bitstream LZSS (output-relative AND ring)
- 16-bit control-word LZSS
- PCX-style RLE
Evidence it's Huffman-coded LZ:
- Compressed data is high-entropy; output is low-entropy 4bpp (40 palette values).
- Literal bytes are **bit-misaligned** — e.g. output's first 0x0e (index 36) corresponds
  to compressed byte ~401, impossible for any fixed-width literal field. Literals are
  variable-length codes straddling byte boundaries.
- No fixed (offbits,lenbits,threshold) reproduces the zero→glyph transition in ANY config.
- Font-class assets (0, 29, 30) share only a 5-byte prefix (identical leading-zero coding),
  consistent with a shared initial Huffman state, not a header.

## Load path (fully mapped)
orchestrator @0x0601DED0  (sets r8=archive 0x20200000, r9=loader, r5=VRAM dest)
  -> loader @0x06011850   (resolves asset via @0x06011704; computes size)
    -> enqueuer @0x0604A238  pushes async command {cmd=2, dest, src, size} onto a queue
      -> task-based decompressor (runs as a scheduled task — why static tracing stalled)

## The decompressor itself
Main decode function located at **~0x0604A4D8** (file 0x3A4D8):
- Initializes **8 tables** in a loop (r9=0..7) via helper @0x0604A5F0  → multiple Huffman trees
- Drives a **jump-table state machine** (mova @0x0604A524 + jmp; cases 0..5)
This is the classic shape of an LHA/LZH -lh5--style decoder (code-length tree → literal/length
tree → offset tree, with periodic block reconstruction).

## Bottom line
Cracking this unlocks BOTH battle menus AND the deferred bottom-bar class/name font (same codec).
Two ways to finish:
1. **Transcribe the decoder** from disassembly (deterministic; ~the 0x0604A4D8 state machine +
   the 8-table init). Then write a matching encoder. Self-contained, no emulator needed, but
   involved (it's a full Huffman-LZ).
2. **Runtime confirm** via Mednafen's SH-2 debugger: breakpoint @0x0604A4D8, capture the
   Huffman table contents at runtime to shortcut step 1's hardest part (tree reconstruction).

Either way, recompression is required unless the codec has a raw/stored mode (TBD once the
state machine is read).

---

# UPDATE 2 — full memory snapshot analysis

Using your four dumps (HIGHWORKRAM, LOWWORK, VDP1VRAM, + the earlier VDP2VRAM):

## Confirmed facts
- **IMG.DAT is loaded to Low Work RAM 0x00200000** (header at 0x00200000, font asset at
  0x0020033C) — matches the archive base 0x20200000 the loader passes.
- **LANG1.BIN loads 100% verbatim at 0x06010000** — the HWRAM dump is byte-for-byte identical
  to LANG1.BIN across the entire 0x60000-byte code region. **=> code AND data patches to
  LANG1.BIN are reliable** (no relocation). This is a major enabler; it also reopens the
  previously-deferred in-game class-name problem to a code-patch solution.
- The breakpoint at 0x0604A4D8 fired during the LANG1 title/boot load (loading these common
  assets: font->VDP2 0x20000, plus assets 1/5/6/29/30/31 -> VDP2 banks 0x22000..0x2C000,
  asset2 -> VDP1 0x70000).

## The codec is an async STREAMING Huffman-LZ pipeline (not a one-shot function)
Stage by stage (all addresses runtime):
1. **0x0604A4D8** — per-call state machine (6 states); each invocation decodes ONE symbol.
2. **0x0604AD3C** — Huffman symbol decoder. Tables: 0x060775F8, 0x0607763A; per-symbol 8-byte
   descriptor table at 0x06077638; "last symbol" byte at 0x060A69CF.
3. **0x060569F8 -> 0x060579A0** — packs (symbol + 3 descriptor bytes) into a 16-byte record and
   enqueues it into a **7-slot ring at 0x060776EC** (busy flag 0x060776C8).
4. **a separate async consumer** drains the ring and produces the actual output bytes (the
   pixel-writing stage — runs in another context; not yet located).

This streaming/queue design is exactly why every blind LZSS/RLE model failed and why simple
static tracing stalled: no single function does "src -> dst".

## Strategic options to finish the menus
- **Crack the full codec (decode + encode).** Large and risky: requires reversing the Huffman
  table build, the symbol->descriptor->byte mapping, the async consumer, AND writing a matching
  compressor. Not recommended as first move.
- **Emulate the game's own decompressor.** Write a small SH-2 interpreter, load the memory
  snapshot (code + LOWWORK source + a VRAM output region), run the real decode pipeline to
  completion, validate against the known font output. Guarantees a correct DECODER without
  understanding the algorithm; the async stages run as plain SH-2 in the same interpreter.
  Bounded, mechanical, reliable. Still leaves ENCODE to solve.
- **Runtime patch (leverages verbatim load).** Skip the compressor entirely: store English menu
  tiles raw in the patch and inject a small SH-2 hook that blits them over the decompressed
  tiles in VRAM right after the menu loads. Needs the exact menu render path pinned down first.

## Open question that picks the path
Are the menu labels **pre-rendered bitmap strips**, or a **tilemap referencing the kanji/font
tiles already in VRAM**? The VRAM renders show the full kanji/status font present but no obvious
pre-rendered "Save/Load/..." strips, which hints the menu may be a tilemap of font glyphs. This
determines whether we edit a graphic, a tilemap, or hook the renderer.
