# In-Battle Text (SCEN.DAT entry 0) — Translation Batch 1

**Status:** codec rebuilt & validated (byte-exact round-trip); translations applied to
entry 0 across all 21 blocks and verified on read-back. Encoding/fit caveats below.

## Where this lives
SCEN.DAT **block-section 2, entry 0** = the global in-battle UI/menu blob (148 substrings),
duplicated identically in all 21 blocks. Edited content-keyed (find JP string → replace),
so it's safe to fold into the existing English build without disturbing other text.

## Batch 1 — magic + summon names (clean, no control codes)
| idx | Japanese | English |
|----:|----------|---------|
| 16 | マジックアロー | Magic Arrow |
| 17 | ブラスト | Blast |
| 18 | サンダー | Thunder |
| 19 | ファイアーボール | Fireball |
| 20 | メテオ | Meteor |
| 21 | ブリザード | Blizzard |
| 22 | トルネード | Tornado |
| 23 | ターンアンデッド | Turn Undead |
| 24 | アースクエイク | Earthquake |
| 25/26 | ヒール１ / ヒール２ | Heal 1 / Heal 2 |
| 27/28 | フォースヒール１ / ２ | Force Heal 1 / 2 |
| 29 | スリープ | Sleep |
| 30 | ミュート | Mute |
| 31/32 | プロテクション１ / ２ | Protect 1 / 2 |
| 33/34 | アタック１ / ２ | Attack 1 / 2 |
| 35 | ゾーン | Zone |
| 36 | テレポート | Teleport |
| 37 | レジスト | Resist |
| 38 | チャーム | Charm |
| 39 | クイック | Quick |
| 40 | アゲイン | Again |
| 41 | デクライン | Decline |
| 42 | ストーン | Stone |
| 43 | ヴァルキリー | Valkyrie |
| 44 | ホワイトドラゴン | White Dragon |
| 45 | サラマンダー | Salamander |
| 46 | アイアンゴーレム | Iron Golem |
| 47 | デーモンロード | Demon Lord |
| — | スレイプニル / フェンリル | Sleipnir / Fenrir |

## Batch 2 (next) — save/load + battle messages (contain control codes)
0 どのデータをロード, 1 セーブ, 2 はい, 3 いいえ, 88 セーブし…, plus level-up / class-change /
shop messages (indices 48–89). These carry `{02}` name-inserts, `{08}` newlines, and
`{04}{XX}` dictionary codes that must be preserved around the translated text.

## Two real caveats before this can ship
1. **Width / buffer.** Encoded full-width (Route A), names are wide — "Magic Arrow" = 11
   cells, "Force Heal 1" = 12, "White Dragon" = 12. The narrow battle boxes (and the
   ~8-full-width-char buffer that crashes on overflow) make several of these risky. The
   project's own fix is **Route B half-width packing**, which fits ~2× the letters.
2. **Disc growth.** Full-width English grew SCEN.DAT by ~43 KB (21 sectors), which forces
   a disc rebuild (shift ISO files, patch PVD, re-frame EDC/ECC). Route B keeps it compact.

## To produce the proper (Route B) patch
Need re-uploaded (sandbox reset wiped them): **`MxPlus_ToshibaSat_8x16.ttf`** (half-width
glyph source) and, to avoid FONT slot collisions with the live build, the current build's
**FONT.DAT** (or the shipped `Langrisser1_EN_classes_menu.xdelta`). With those, this batch
re-encodes in Route B and folds straight into the existing English build.

## Artifacts (in outputs)
- `scen_codec.py` — validated SCEN.DAT parse/serialize.
- `translate_battle.py` — content-keyed entry-0 translator (Route A demo encoding).
- `SCEN_battle_en.dat` — SCEN.DAT with batch-1 names applied (full-width; demo/validation).
