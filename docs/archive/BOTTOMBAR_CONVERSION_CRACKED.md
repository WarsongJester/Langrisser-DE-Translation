> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> Intermediate class-name state: bottom-bar conversion cracked, 16×16 panel still crashing. Both later solved.
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# Bottom-Bar Class/Name Renderer — Conversion CRACKED

Cracked via live debugger read-breakpoint on the Lord class string (CPU 0x0607181C),
which landed in the renderer; code then read directly from extracted/LANG1.BIN.

## Renderer
- Per-character loop: CPU **0x0601C002–0x0601C08E** (file 0x1C002).
- Reads class string (class-name pool, e.g. Lord @ file 0x6181C) AND character names.
- Character-NAME pointer table: CPU **0x06072314** (file 0x62314) -> name strings @ 0x06072028+
  (half-width katakana: ﾚﾃﾞｨﾝ=Ledin, ｸﾘｽ=Chris, ｼﾞｪｼｶ=Jessica, ﾅｰﾑ=Narm, ﾃｲﾗｰ=Taylor,
  ﾎｰｷﾝｸﾞ=Hawking…). Names are editable LANG1 katakana strings.
- Glyph-draw fn ptr = r11 = const @ 0x0601C0B4.

## Byte -> glyph-index conversion (EXACT)
Specials first, then range formulas:
- byte == 0x20 (space)      -> glyph 64
- byte == 0xA5 (･)          -> glyph 32
- byte == 0xB0 (ｰ long vow) -> glyph 110
- byte == 0xDE (ﾞ dakuten)  -> glyph 112  (combining)
- byte == 0xDF (ﾟ handak.)  -> glyph 113  (combining)
- byte == 0x47              -> glyph 143  (special-cased == 'G')
- byte  > 176 (0xB0)        -> glyph = byte - 112      [SAFE high-byte region]
- byte 58..176             -> glyph = byte - 53
- byte <= 57               -> glyph = byte - 30
Threshold consts: 0x601C0A4=0xDE, A6=0xDF, A8=0x8F(143), AA=0xB0(176), AC=0xA5(165).
Verified: ﾃｽﾄ(C3 BD C4)->83,77,84; ﾛｰﾄﾞ(DB B0 C4 DE)->107,110,84,+dakuten.

## Half-width font glyph-index -> char (VRAM 0x20000, rendered hwfont_byindex.png)
Latin present (scattered):
  A=1  T=2  D=3  F=4  P=6  H=8/9   B=31   S=44  Z=45  C=46  M=47
  T=138 U=139 R=140 N=141 G=143    S=154 C=155 E=156 N=157 A=158 R=159 I=160 O=161
Missing entirely: J K L Q V W X Y + lowercase.

## Reachability (KEY)
glyph index = byte - 112 for byte 0xB1..0xFF  => indices 65..143 reachable by SAFE high bytes.
  Latin in 65..143: T(0xFA) U(0xFB) R(0xFC) N(0xFD) G(0xFF).
Lower Latin (A B C D F H @ idx<=27; B S Z C M @ idx 31..47) reachable only via low/mid bytes
  (bottom-bar-safe, but those low bytes likely CRASH the separate 16x16 detail-panel renderer).
Letters at idx >143 (E=156, I=160, O=161, SCENARIO set) are UNREACHABLE by any single byte
  (byte caps at 0xFF -> glyph 143) without patching the conversion code.

## Consequence for English class names
- Conversion fully solved; pipeline proven (LANG1 edit -> splice -> disc -> in-game).
- Bottom-bar font gaps (no J K L Q V W X Y) + ceiling (E/I/O unreachable) block most class
  names as-is. Full English needs: (a) extend/patch the conversion to reach idx 144-175
  (E/I/O), and/or (b) add missing letters to blank font slots (font is in VRAM 0x20000 from a
  compressed source — locate/edit source or runtime-inject), and (c) crack the 16x16 detail-
  panel renderer (separate conversion) if English is wanted there too.
- Validation test built: Lord -> "GRUNT" via safe high bytes FF FC FB FD FA
  (Langrisser1_classgrunt.xdelta) — confirms conversion in-game and whether the 16x16 panel
  shares it.

---

# 16×16 detail-panel renderer — analyzed (GRUNT crash)

GRUNT test result: bottom bar showed "GRUNT" (conversion CONFIRMED in-game). Opening the
unit/commander detail panel CRASHED (MasterSH2 "Unknown code 0200", PC=00000002, link
≈0x0602B094 — adjacent to the crash trampoline at file 0x1B080 the old notes flagged).

The detail panel is a SEPARATE renderer, NOT arithmetic:
- Char loop: CPU 0x0602B150 (file 0x1B150). Reads class byte, computes byte+2, calls
  0x06029F4C, then draws via 0x06029F9C.
- 0x06029F4C (file 0x19F4C): walks a STRING TABLE and returns the (byte+1)-th null-
  terminated entry. Table base via accessor 0x06015040(arg=2) — a runtime-loaded block.
- Valid katakana bytes (0xA1–0xDF) -> real table entries (no crash; テスト rendered fine).
  Out-of-range bytes (GRUNT 0xFA–0xFF, or ASCII) -> scan runs past the table end ->
  garbage pointer -> jump to 0x00000002 -> crash.

## Consequence
- Bottom bar and detail panel read the SAME class string but use UNRELATED conversions.
  The only codes safe on BOTH are the katakana band 0xA1–0xDF (which render katakana, not
  Latin). There is NO code that is Latin on the bar AND in-range on the panel.
- Therefore shippable English class/unit names require:
  (1) patch the 16×16 panel renderer so non-katakana codes don't crash (ideally re-point it
      to an arithmetic byte->FONT.DAT-glyph path; FONT.DAT has every letter and is editable),
      AND
  (2) fill the bottom-bar VRAM font's letter gaps (J K L Q V W X Y missing; E/I/O at glyph
      idx >143 unreachable without a conversion-code tweak).
- Both are deep RE/graphics tasks. The story translation is complete; this in-battle UI text
  is the long-deferred hard frontier. Pipeline + debugger workflow now proven, bottom bar
  fully cracked, all strings/renderers located — substantial groundwork done.

## If continuing: next debugger capture
On a NON-crashing build (original ﾛｰﾄﾞ, or the classtest テスト build): read-breakpoint the
class string (0x0607181C), open the detail panel, capture the hit whose PC is in 0x0602Bxxx
(the panel renderer, NOT 0x0601C0xx which is the bottom bar). Then trace 0x06029F9C (string
-> glyph draw) and the 0x06015040(2) table to design the patch.
