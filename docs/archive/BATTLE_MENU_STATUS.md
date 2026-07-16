> ⚠️ **ARCHIVED — superseded.** This file is kept for history only.
> In-battle menu status — merged into docs/in_battle_ui/MENU_CHROME.md.
> The current authoritative reference is **`docs/00_MASTER_REFERENCE.md`** (story/text + build)
> and **`docs/in_battle_ui/`** (class names + menu chrome). Where this file disagrees with
> those, the current docs win.

# In-Battle Menu Translation — Consolidated Status

## What each menu actually is (now confirmed)

The two battle menus use **different rendering systems**, so they're different problems:

### Option menu + save/load system  → SJIS text (tractable)
- Confirmed SJIS strings inside LANG1.BIN, e.g. `セーブできません` ("cannot save",
  file 0x2B4E8) and `データが壊れています` ("data is corrupted", 0x2B4FC), plus `セーブ`.
- These render through the standard SJIS→font path. **LANG1.BIN loads byte-for-byte
  verbatim** at 0x06010000 (verified in both the title and battle dumps), so these
  strings are directly patchable on disc.
- Caveat to confirm: which font the in-battle renderer uses for these (the kanji font in
  VRAM vs FONT.DAT) and whether the menu *items* themselves are standalone SJIS or are
  built differently from the error messages.

### Command menu (移動/攻撃/魔法/治療/指令)  → NOT SJIS (hard)
- None of these kanji exist as SJIS in LANG1.BIN or RAM.
- They are not visible as a clean pre-rendered strip in VDP2 VRAM either.
- => They are either pre-rendered graphics (IMG.DAT codec) or the **custom in-battle text
  system** (the same family as the deferred class names: custom code page → custom font →
  custom renderer). Either way this is the hard path.

## Supporting findings this session
- **IMG.DAT codec** = async *streaming* Huffman-LZ pipeline (Huffman symbol decode →
  record ring → separate consumer). I built a working SH-2 interpreter, but the decode is
  entangled with the game's task/CD runtime, so it can't be run cold from a static snapshot
  without isolating a synchronous entry + stubbing the scheduler. Reusable, but not on the
  critical path for a runtime patch.
- **The engine already renders English** pre-rendered text in its UI ("EXIT" is in VRAM),
  so English menu text will look native.
- **Verbatim LANG1 load** is the key enabler: code and data patches are reliable. This also
  reopens the deferred class-name problem to a code-patch approach.

## The tractable path: runtime VRAM overlay (no codec needed)
Because LANG1 loads verbatim, the cleanest route for the *command* menu is to overwrite the
final pixels after the menu draws, regardless of how it's originally rendered:
1. Locate the command-menu pixels when displayed.
2. Hook the menu-draw routine (it's in LANG1, which I now have in the battle HWRAM dump).
3. Author English bitmaps + inject a small blit hook.

Blocker for step 1: the command menu is **not** in VDP2 VRAM as a strip, which strongly
suggests it's drawn as **VDP1 sprites**. I have VDP2 from the battle moment but not VDP1, so
I can't yet see/locate the command-menu pixels. A **VDP1 VRAM dump with the command menu
open** would settle this and unblock the overlay.

## Recommendation
- **Option menu**: likely translatable by editing SJIS strings in LANG1 — the same class of
  work as the dialogue, and lower risk. Good first target.
- **Command menu**: pursue the runtime VRAM/VDP1 overlay (avoids the codec and custom
  renderer entirely). Needs one more capture (battle VDP1 VRAM) to locate the pixels.
