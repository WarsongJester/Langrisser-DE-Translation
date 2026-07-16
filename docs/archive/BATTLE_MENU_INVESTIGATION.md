> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> In-battle menu investigation — merged into docs/in_battle_ui/MENU_CHROME.md.
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# Langrisser I — In-Battle Command & System Menus: Investigation

**Target:** translate the in-battle **command menu** (移動 Move / 攻撃 Attack / 魔法 Magic /
治療 Cure / 指令 Command) and the in-battle **system menu** (セーブ Save / ロード Load /
勝利条件 Victory Conditions / ゲーム設定 Game Settings / フェイズ終了 End Phase).

**Conclusion: these two menus are pre-rendered GRAPHICS, not text.** They are not rendered
through FONT.DAT / SJIS like dialogue, names, items, classes, etc. Editing them is a
graphics problem gated by IMG.DAT's compression codec, which is still uncracked.

---

## 1. They are not SJIS text (proven)

Searched FONT.DAT, SCEN.DAT, LANG1.BIN, 0.BIN for the menu words as full-width SJIS:

- 移動 / 設定 / 勝利条件 / 終了 etc. **do** appear in SCEN.DAT — but only as **coincidental
  occurrences inside the battle-tutorial prose** (block 20) and as Saturn save-data error
  messages in LANG1.BIN ("セーブできません", "ゲームをスタート…"). None are the menu labels.
- **フェイズ ("Phase") does not appear as contiguous SJIS anywhere on the disc.** ゲーム設定
  and フェイズ終了 do not exist as whole strings anywhere. If these menus were SJIS text,
  those strings would have to exist. They don't → the menus are not text.

## 2. They live in IMG.DAT (compressed graphics archive)

`LANG1/IMG.DAT` (disc LBA 134794, 514,624 B) is the **compressed asset archive** previously
identified in `BOTTOM_BAR_FONT_NOTES.md` as the home of the bottom-bar font.

- Header = a **207-entry big-endian uint32 offset table**, exactly matching the documented
  table (`[0]=0x33C [1]=0xCF2 [2]=0x178A [3]=0x1DCA …`). The "Low Work RAM 0x00200000"
  archive in the notes **is** IMG.DAT loaded into RAM.
- **Every asset begins with `0xC0`** and shares one codec. Asset 0 (2486 B) = the bottom-bar
  font. The command/system menu graphics are other assets in this same archive.
- Many assets share a verbatim literal run `64 63 7e 10 67 e7 0c 7e` after a 4-byte
  `c0 01 07 <param>` prefix — a common decompressed tile/cell header, confirming these are
  graphics cells.

## 3. The codec is custom (re-confirmed this session)

Independently re-confirmed the prior session's finding that this is **not standard LZSS**:

- Brute-forced ring-buffer LZSS across {MSB/LSB bit order} × {literal polarity} ×
  {12/4 and 8/8 offset/length} × {ring init 0x00/0x20} × {length-add 1/2/3}. Every config
  decompressing asset 0 to ~6 KB (the right size for the ~192-tile 4bpp font) renders as
  **pixel noise**, not glyphs.
- PCX-style `0xC0` RLE → noise.
- Conclusion stands: custom/non-LZSS scheme (or a planar/pre-expansion intermediate).

## 4. Why it can't be cracked blind here, and the deterministic unlock

Cracking a custom codec reliably needs a **matched (compressed → decompressed) pair**. We
have the compressed side (IMG.DAT asset 0 = 2486 B). We need the decompressed side.

The prior notes reference RAM dumps that contain it but they are **not in the current
uploads**:
- **`VDP2DUMP.bin`** — VDP2 VRAM; the decompressed bottom-bar font sits at offset 0x20000.
  This is the single most useful file: aligning compressed-asset-0 against this known output
  reverses the codec exactly.
- A **Low Work RAM dump (0x00200000)** — confirms IMG.DAT is the loaded archive and lets us
  verify asset boundaries.
- (HWRAM dumps `kronos/taylor/freeze.bin` are the 0x06000000 region — they do **not** contain
  the VDP2 font.)

Once the codec is reversed, it unblocks **both** the in-battle menus **and** the bottom-bar
class/name font (the other deferred item), because everything in IMG.DAT shares this codec.

## 5. Alternatives if the dumps aren't available

- **Emulator write-breakpoint** on VDP2 VRAM dest (~0x25E20000) during boot → lands inside
  the decompressor; a short trace gives the format directly (per `BOTTOM_BAR_FONT_NOTES.md`).
- **Renderer-repoint** (avoid the codec): patch the menu-draw code in LANG1.BIN to pull
  labels from FONT.DAT as SJIS. Deep RE, and LANG1 relocates code pointer literals at load,
  so code patches are unreliable — not recommended over cracking the codec.

## 6. Status of prior menu work (clarification)

The earlier `SCEN_menu.dat` / `FONT_menu.DAT` work (16 changed kanji cells) translated
**SCEN.DAT entry-0 UI strings** — a different, text-based menu surface. It did **not** touch
these two in-battle graphic menus, which is why Tim's 2026-06-12 screenshots still show them
in Japanese.
