# Obsolete scripts — do not run

These produced the first versions of the schematic and board. The project has
been edited by hand since, and re-running any of them would overwrite that work.

| Script | Why it's here |
|---|---|
| `gen_sch.py` | Generated the original schematic. Re-running replaces `battery_pcb.kicad_sch` and `sheets/`. |
| `gen_pcb.py` | Generated the original board. It placed back-side parts **without mirroring them** (U1 came out pin-reversed). |
| `place_buck.py` | First attempt at buck placement. It had the same mirroring bug and trapped the SW pin behind CIN. |
| `setup_copper.py` | First attempt at zones. It put every zone on F.Cu. |

The current layout pipeline is in `tools/` (see `LAYOUT_NOTES.md`).
