
---

## Post-toolkit builds (June 16 -> July 16, superseding the table above)

The table above reflects the project as of the June 16 toolkit snapshot (current build then:
`EN_45`). Work continued past that point; see `docs/sessions/` for the full narrative of each
build below.

| Patch | Base | Contents |
|-------|------|----------|
| `Langrisser1_EN_46_full.xdelta` | EN_45 | + in-battle command ring & Order submenu translated, "Undease"->"Undead" typo fix. See `docs/sessions/2026-07-03_menu_ring_handoff.md`. |
| `Langrisser1_EN_menu_ring_full.xdelta` | clean JP | Menus-only build (command ring + Order submenu, no story text) -- useful for isolated menu testing. |
| `Langrisser1_EN_55_full.xdelta` | EN_46 (via EN_51-54) | + on-map deployment menu translated (Hire Troops / Equipment / Position / Sortie, Commanders panel header) + a chain of bottom-bar/status-screen fixes. See `docs/sessions/2026-07-08_en51-55_deployment_menu.md` and `2026-07-08_en55_notes.md`. |
| **`Langrisser1_EN_63_full.xdelta`** | EN_54 (rebased) + kana clamp | **Current build.** Fixes a load/new-game crash (MasterSH2 PC=2) found in EN_55-62 on hardware-accurate emulators (SSF/Kronos). Rebased onto the SSF-proven EN_54 content plus an independently-proven kana/lowercase clamp on the 16x16 class-name renderer, relocated off a display-window struct it was corrupting in EN_62. Trades away EN_55's deployment-menu tile labels/sub-screen title bars, which are slated to be rebuilt on the EN_54-safe (HWRAM-only, no FONT-VRAM) pattern. See `docs/sessions/2026-07-16_en63_crash_investigation.md`. |

### Superseded, pre-toolkit (kept in `patches/superseded/` for history only)

- `Langrisser1_EN_dialogue.xdelta` (June 10) -- early dialogue-only patch, predates EN_44.
- `Langrisser1_EN_hw_scn1.xdelta` (June 7) -- Route B half-width proof-of-concept, Scenario 1 only.

Both are fully superseded by `Langrisser1_EN_44.xdelta` onward and are not needed to reproduce
the current build.
