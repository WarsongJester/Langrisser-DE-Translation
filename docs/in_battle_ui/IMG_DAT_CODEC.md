# IMG.DAT Codec — Reverse-Engineering Notes (research, not cracked)

**Status: located but not transcribed.** The custom UI font (and other in-battle graphics) are
compressed in `LANG1/IMG.DAT` (disc LBA 134794). The codec is a **stateful streaming Huffman-LZ
(LZH-family)** — *not* LZSS. The decoder back-end is mapped but not turned into a standalone
decode/encode. Cracking it would unlock static editing of the menu/class font; the **runtime
glyph-injection route (`MENU_CHROME.md` §3) sidesteps it** and is the recommended path.

Consolidates `CODEC_FINDINGS.md` (archived). Codec experiment scripts: `tools/lzcrack.py`,
`tools/codec_*.py`, `tools/scan_codec*.py`, `tools/trace_*.py`, `tools/render_try*.py`.

---

## 1. The archive & the matched pair

- IMG.DAT = a compressed asset archive: a **207-entry big-endian uint32 offset table**, then
  blobs; every asset begins with `0xC0`.
- Loaded to **Low Work RAM 0x00200000** (= uncached 0x20200000): header @ 0x00200000, font asset
  @ 0x0020033C.
- **Asset 0 = the custom UI font**, decompressed to **VDP2 VRAM 0x20000** (verified by rendering:
  partial Latin A T D F M P V H + digits + katakana + TURN/SCENARIO + bold digits).
- **Known input↔output pair to validate any decoder against:** compressed `IMG.DAT[0x33C:0xCF2]`
  (2486 B, first bytes `C0 01 C0 51 A2 7C 08 FC 61 0F D6 …`) ↔ decompressed 8192 B @ VRAM 0x20000.

---

## 2. Why it is NOT LZSS

Exhaustively tested and rejected against the real output (all fail past the trivial leading-zero
run): byte-aligned LZSS (output-relative and 4K ring), continuous-bitstream LZSS (both), 16-bit
control-word LZSS, PCX-style RLE. Evidence for Huffman-coded LZ:
- Compressed data is high-entropy; output is low-entropy 4bpp (≈40 palette values).
- Literal bytes are **bit-misaligned** (e.g. output's first 0x0E corresponds to compressed byte
  ~401 — impossible for any fixed-width literal field) → variable-length codes straddling bytes.
- No fixed `(offbits, lenbits, threshold)` reproduces the zero→glyph transition in any config.
- Font-class assets (0, 29, 30) share only a 5-byte prefix (shared initial Huffman state, not a
  header).

---

## 3. Load path & decoder (fully mapped, runtime addresses)

```
orchestrator @0x0601DED0   (r8=archive 0x20200000, r9=loader, r5=VRAM dest)
  → loader @0x06011850     (resolves asset via @0x06011704; computes size)
    → enqueuer @0x0604A238  pushes async {cmd=2, dest, src, size} onto a queue
      → task-based decompressor (a scheduled task — why static "src→dst" tracing stalls)
```
The decoder is an **async streaming pipeline**, not a one-shot function:
1. **0x0604A4D8** — per-call state machine (6 states via `mova @0x0604A524 + jmp`); each
   invocation decodes ONE symbol. Initializes **8 tables** in a loop (r9=0..7) via helper
   @0x0604A5F0 → multiple Huffman trees. Classic LHA `-lh5-`-style shape.
2. **0x0604AD3C** — Huffman symbol decoder. Tables 0x060775F8 / 0x0607763A; per-symbol 8-byte
   descriptor table @ 0x06077638; "last symbol" byte @ 0x060A69CF.
3. **0x060569F8 → 0x060579A0** — packs (symbol + 3 descriptor bytes) into a 16-byte record,
   enqueues into a **7-slot ring @ 0x060776EC** (busy flag 0x060776C8).
4. **a separate async consumer** drains the ring and writes the output pixel bytes (not yet
   located).

The breakpoint @0x0604A4D8 fires during the LANG1 title/boot load (font → VDP2 0x20000, plus
assets 1/5/6/29/30/31 → VDP2 banks 0x22000–0x2C000, asset 2 → VDP1 0x70000).

---

## 4. Three ways to finish (if pursued)

1. **Transcribe the decoder** from disassembly (state machine + 8-table init + symbol→
   descriptor→byte). Deterministic, self-contained, but involved — a full Huffman-LZ — and still
   needs a matching **encoder** to recompress.
2. **Emulate the game's own decompressor.** Run the real pipeline in a small SH-2 interpreter
   (`tools/sh2emu.py` is a start) over the memory snapshot (code + LWRAM source + a VRAM output
   region), validate against the known font output. Guarantees a correct **decoder** without
   understanding the algorithm; still leaves **encode** to solve.
3. **Runtime patch (leverages verbatim LANG1 load).** Skip the compressor: store English tiles
   raw and hook a small SH-2 routine to blit them over the decompressed tiles in VRAM after the
   font loads. This is exactly the **Route 1** approach in `MENU_CHROME.md` / `CLASS_NAMES.md`,
   and is why the codec never had to be cracked for class names.

---

## 5. Open question (decides effort if cracking the codec)

Whether the codec has a **raw/stored mode** (TBD once the state machine is fully read) — if so,
recompression is trivial; if not, a full matching compressor is required.

```
IMG.DAT        : disc LBA 134794; 207-entry BE u32 offset table; assets start 0xC0
loaded to      : LWRAM 0x00200000 (uncached 0x20200000); font asset 0 @ 0x0020033C
known pair     : compressed IMG.DAT[0x33C:0xCF2] (2486 B) ↔ decompressed 8192 B @ VRAM 0x20000
codec type     : stateful streaming Huffman-LZ (LZH/-lh5-family); NOT LZSS
decoder        : state machine 0x0604A4D8; Huffman 0x0604AD3C; ring 0x060776EC (7 slots)
load path      : orchestrator 0x0601DED0 → loader 0x06011850 → enqueuer 0x0604A238 → async task
```
