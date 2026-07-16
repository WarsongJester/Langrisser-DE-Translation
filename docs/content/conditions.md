# In-Battle Victory/Defeat Conditions — Translated (Route B)  [v2, post in-game test]

**Patch:** `Langrisser1_EN_44.xdelta` (built on `Langrisser1_EN_43`). Disc size unchanged.
**Shown by:** the in-battle option menu's "Victory Conditions" command.

## Fixed after your screenshots
1. **Headers + "Destroy all enemies" were still Japanese.** They aren't literal entry-6 text —
   they're `{04}{XX}` dictionary codes that expand from **entry 4** (a global table). Now
   translated there:
   - `＊勝利条件` → **＊Victory Conditions** (`{04}{1C}`)
   - `＊敗北条件` → **＊Defeat Conditions** (`{04}{1D}`)
   - `・敵の全滅` → **・Destroy all foes** (`{04}{0D}`, used by 9 scenarios)
   - `・ターンオーバー` → **・Time runs out** (turn-limit loss)
   Verified: all dictionary codes used by any scenario now resolve to English (0 Japanese).
2. **S13 `全指揮官石化`** was a *lose* condition (your side) — corrected from "Petrify all
   foes" to **"All allies petrified"**.
3. **"Ledin  dies" double space** — the `{02}` lord-name insert already carries a trailing
   space, so the leading space was removed → **"Ledin dies"**.
4. Long lines (e.g. "Ledin reaches the stairs / on the top floor") confirmed wrapping correctly
   in-game.

## Coverage
- Entry 6 (per-scenario objectives), all 21 scenarios — 49 lines.
- Entry 4 (global dictionary phrases used by the panel) — Victory/Defeat headers, Destroy all
  foes, Time runs out.
- Names match entry-1 spellings.

## Build/safety
- Route B half-width; reused existing pairs + 4 new glyphs in **blank** font slots.
- SCEN grew to 354 sectors but its ISO allocation reserves **364**, so it still **splices in
  place** — no file shifting, no ISO/PVD edits, disc size identical.
- Mode-1 EDC/ECC recomputed and validated byte-identical; all changes confined to the FONT and
  SCEN ranges; patch reproduces the build byte-for-byte.

## Test
Apply to clean JP `.bin` → rename `Langrisser1_EN_test.bin` → load `.cue` in SSF (PCM OFF) →
battle → option menu → Victory Conditions.

## Still Japanese elsewhere (not conditions; out of scope here)
Entry-4 **place names** (Twin Castle, Raigard Empire, Holy Rod, Dark Rod, Velzeria, …) remain
Japanese — they're not part of the conditions panel. Entry-3 debug/sound-test menu also remains
Japanese (normally inaccessible). Let me know if you want either tackled next.
