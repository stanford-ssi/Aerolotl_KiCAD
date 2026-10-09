# Battery PCB — layout notes (layout A, 30 Sep 2026; 5.72 in outline 1 Oct 2026)

This board was called CamControl until 6 Oct 2026. The backup files and Onshape tab names below keep the old name; the backups live in the original working copy, not in this repo.

The board now matches the Onshape av-bay CAD: the 5.72 in outline, the three edge cut-outs, two 3/8 in rod holes
120 mm apart, and the two 4.5 mm COTS-mount screw holes. Everything else was re-placed and re-routed to fit around them.
The ESP32 DevKitC now plugs in from the **back** (option A).

| Check | Result |
|---|---|
| DRC | **0 violations**, 0 unconnected |
| Schematic parity | **0** (no schematic changes were needed) |
| `tools/layoutA/verify_A.py` | all 23 checks pass (outline, holes, washers, ESP32 pin order, buck, pyro isolation, widths, zones, labels) |

Pictures: `renders/layoutA_front.png`, `renders/layoutA_back_seen_from_back.png`.

Previous boards and notes:
- `backups/camcontrol_before_layoutA_2130.kicad_pcb` = your 12:24 board.
- `backups/LAYOUT_NOTES_before_layoutA.md` = its notes.
- `backups/camcontrol_v4_layoutA.kicad_pcb` = layout A with SW2/SW3.
- `backups/camcontrol_v5_noARM.kicad_pcb` = layout A without SW2/SW3.
- `backups/camcontrol_v6_pinswitch_holes.kicad_pcb` = v5 + H5/H6, 5.82 in.
- `backups/camcontrol_v7_572in.kicad_pcb` = 5.72 in outline, H5/H6 moved 0.5 mm. The scripts before this change are in `backups/tools_before_572/`.
- `backups/camcontrol_v8_latching_camera.kicad_pcb` = see "Review changes, 5 Oct 2026".
- `backups/camcontrol_v9_pinstack_exact.kicad_pcb` = v8 with the stack raised on 18 mm standoffs (rejected).
- `backups/camcontrol_v10_stack_on_board.kicad_pcb` = cells back 2 mm, ESP32 block in 5.08 mm, stack flat on the board.
- `backups/camcontrol_v11_cots_out_1p5.kicad_pcb` = cells back 3.5 mm in total, COTS mount (H3/H4) and J5/J6 out 1.5 mm (1.8 mm gap between the stack and the holders).
- `backups/camcontrol_v12_routing.kicad_pcb` = this board: v11 with shorter routing (see "Routing clean-up"). The scripts and schematic before it are in `backups/tools_before_connectors/` and `backups/sch_before_connectors/`.
- `backups/supplies_before_noARM.kicad_sch` = the schematic sheet before SW2/SW3 were removed.

## Mechanical (from the CAD)

| | |
|---|---|
| Outline | Ø5.72 in (145.29 mm), changed from 5.82 in on 1 Oct 2026; set once in `tools/kc.py` (`DISC_IN`) |
| Cut-outs | 40 × 14 mm at the bottom (COTS mount); 10 × 6 mm at lower left and lower right |
| Rod holes H1/H2 | 13/32 in (10.32 mm) at (±60, 0): 120 mm centre to centre. No copper or parts within the 3/8 SAE washer (r 10.6) on either side |
| Screw holes H3/H4 | 4.5 mm at (±8.7, +50 mm below centre), 17.4 mm apart, copper keep-out r 4.8 |
| Pin-switch holes H5/H6 | M3 (3.2 mm) at (18.5, −41.88) and (−18.5, −48.88) (KiCad, centre-relative): bolts of the pin-switch stack, which sits flat on the board |
| Kept free | Top centre for the pin-switch stack; bottom centre for the COTS vertical board |

## What moved and why

- **Batteries (front):** still side by side, but BT2–BT3 and BT3–BT4 are now 4.75 mm apart.
- **ESP32 DevKitC (back):** the same 1×19 through-hole sockets, J1/J2, now mount on the underside.
  - Their pins come up through the two wider battery gaps, and are soldered on the front.
  - The DevKitC plugs in **parts facing down**, antenna end toward the top (`ANTENNA END` / `USB END` on the back silk).
  - Seen from the front, J1 (3V3…5V) is the right column and J2 (GND…CLK) the left, because the module is upside down.
- **Buck:** moved as one block, unchanged layout (TI fig 9-10). It sits between the socket rows on the back, under the DevKitC.
- **Connectors:**
  - J3 camera: left side, above the left rod. R7/R8 are behind it on the back.
  - SW1 CAM PWR: bottom left, next to the fuse.
  - J5 / J6 (COTS / SRAD power out): bottom right, side by side next to the COTS mount.
- **No on-board arming connectors (removed SW2/SW3, also from the schematic).** J5 / J6 carry the cell straight out; each
  arming switch goes inline in the cable to its flight computer: BT3 → J5 → switch → COTS altimeter, BT4 → J6 → switch → SRAD FC.
- **Status LED D2:** back, beside J2-15.

## Copper

- 2 layers.
- GND pour on both sides with stitching vias.
- Local pours: VIN and +5V at the buck, VBAT+ at BT1.
- No-pour area over the ESP32 antenna end.
- COTS/SRAD supplies stay isolated islands (Pyro class, 0.4 mm clearance, 1.0 mm tracks).

| Net | Route |
|---|---|
| Series link | BT1− → BT2+ across the top, front, 3 mm |
| VBAT+ / VF | BT1+ → vias → fuse F1 (back) → SW1 (1.5 mm) |
| VSW | SW1 → under the J2 column → D3 → D1 → buck (back, 1.5 mm) |
| +5V | buck → J1-19 + C9/C10 (back); → front, under the cells → J3 pin 1 (1.0 mm) |
| VBAT_SENSE | R4 → R5/C8 → J1-5 (back) |
| ESP_TX2/RX2 | J2-11/12 → straight left on the back → R7/R8 → J3 |
| COTS | BT3+ → J5-1 (front); BT3− → over the top of J1 pin 1 → via → down the back under BT4 → J5-2 |
| SRAD | BT4+ → J6-1 (front); BT4− → via → down the back under BT4 → J6-2 |

## Check before ordering

1. **Stack height:** done in the CAD. The DevKitC hangs about 14 mm below the board, so "Bottom disc height above
   bay floor" is now 18 mm (2.03 in left above the top nuts).
2. **WiFi:** the antenna faces down, under the cells. Fine for bench setup; expect short range.
3. **USB:** reachable only with the stack out (USB end at the bottom of the DevKitC).
4. **Vibration:** add a zip tie or Kapton tape so the DevKitC can't back out of its sockets.
5. **Assembly order:** solder the socket pins (front, in the battery gaps) before fitting cells.
6. **Bay:**
   - The CAD now assumes a 6.0 in ID, with 5.998 in end discs 7.0 in apart.
   - The sections are 1.5 / 4 / 1.5 in, and the rods are 8.02 in long.
   - The 5.72 in inner discs leave 0.14 in radial clearance.

## Onshape

- `cad/battery_pcb.step`: this board exported from KiCad, with the board centre as the origin. It has every part
  except fuse F1, which has no 3D model. The DevKitC isn't in it.
- Imported into "Switchband Assembly" as tab **camcontrol_power_pcb**, merged into one closed composite part called "CamControl power PCB".
- **AV Bay Stack - REAL PCB** (the stack tab, renamed from "AV Bay Stack v2 (3-8 rods)"): the green placeholder disc is
  removed ("Delete part 1"). The real PCB is brought in ("Derived 1") and raised 18 mm onto the bottom washers
  ("Transform 1"). Its rod holes and cut-outs line up with the stack.
- **Bottom Board:1:**
  - The PCB replaces the old plate: fastened on the plate's centre and bottom face, then fixed.
  - The old plate, the BLRV board and the 4 old standoffs are **suppressed**, not deleted.

## Pin-switch stack (v10, 5 Oct 2026)

- **What:** two "Double Pin Switch" units from the original CAD. Each is a printed carrier with two microswitches, worked by one pull pin.
  - They are used **exactly as built** (physical parts, nothing trimmed): carrier 45 × 32 × 10 mm, microswitch 20.15 × 15.5 × 6.15 mm, same volumes as the originals.
  - The stack sits **flat on the board** at the top centre (+Y in CAD), across the cells from the COTS mount, with the pin holes facing the airframe wall.
- **What was moved to make room** (`tools/kc.py`):
  - The battery holders moved 2 mm toward the COTS mount (`BAT_DY`). That is the most that fits: their bottom solder tabs now end about 0.6–0.8 mm from the COTS plate flange, and BT4's bottom tab sits next to J6.
  - The ESP32 sockets, regulator block, UART resistors and status LED moved 5.08 mm (two pins) toward the centre (`ESP_DY`), so J2's top pins come out from under the stack. The LED sits 3 mm higher than its pin row, clear of camera standoff H8.
  - The DevKitC antenna end is now about 5 mm further under the cells, so expect slightly shorter WiFi range.
- **Seat:**
  - Upside down (rails down), centred, pin faces 68.88 mm from the centre, corners at 72.46 mm (inside the 72.64 mm disc).
  - The inner rail rests on BT2's and BT3's flat + solder tabs, which stand 0.3 mm proud of the board. The CAD model sits 0.1 mm above them so the clash check stays clean; the result is 0 clashes.
- **Mounting:**
  - Two M3 bolts through both carriers and the board: H5 (18.5, −41.88) and H6 (−18.5, −48.88) (KiCad, centre-relative), with nuts on the back.
  - Use nylon: H5 is over the ESP32 antenna end. A 0.3 mm shim under each bolt boss takes up the tab height if needed.
- **Arming connectors SW2 / SW3** sit right beside the stack (Micro-Fit, centres (29.8, −50) and (41.1, −50)).
- **H3/H4** now use `battery_pcb:MountingHole_4.5mm_COTS_Flange`: front courtyard = the plate flange around the screw (r 3.95), back courtyard = M4 nut and washer (r 4.75).
- **Onshape:** "Pin switch stack 1": rails down, pin X 0, pin face 68.88, PCB top 19.51, PCB 1.51 thick, spacer 0.4 mm. Code copy: `cad/pin_switch_stack.fs`.

## Review changes (5 Oct 2026)

These address Koichi's review.

- **Latching connectors.**
  - J5, J6, SW1, SW2 and SW3 are now Molex Micro-Fit 3.0 43650-0215: 2-pin vertical, positive latch, 5 A.
  - J3 (camera) is now a JST GH BM05B-GHS-TBT: 5-pin vertical, positive lock.
  - KiCad has no Micro-Fit 3D model, so `tools/step_boxes.py` writes a box model from the Molex dimensions (9.65 × 4.37 × 10.15 mm) into `3dmodels/`.
  - The project footprint `battery_pcb:Molex_Micro-Fit_3.0_43650-0215...` uses that model. Mating housing: Molex 43645-0200 with 43030 crimps.
- **Pin-switch connectors (SW2 COTS ARM, SW3 SRAD ARM)** are back, next to the pin-switch stack.
  - The pin switch is in series with each flight computer's battery, so its leads land right beside it.
  - BT3/BT4 are turned so + is at the top. The COTS path is BT3+ → SW2 → down the back → J5-1, with BT3- → J5-2. SRAD is the same with BT4, SW3 and J6.
  - J5/J6 now carry the switched supply. No switch goes in the harness any more.
- **Camera on the back.**
  - The RunCam Split 4 board (29 × 29 mm, M2 holes on a 25.5 mm square) mounts under BT1/BT2 on four Würth 9774050243 M2 × 5 mm SMT standoffs (H7–H10). It sits clear of the ESP32 and the status LED.
  - The standoff footprint is Würth's land pattern without the centre hole, because the holder sits on the other side. Use M2 × 5 screws (max 6 mm).
  - J3 is on the back next to the camera's wire pads. The UART series resistors R7/R8 moved next to the ESP32 pins.
  - `CAM1` is a placement-only footprint that carries a camera block model for the 3D view and Onshape.
- **More cut-outs.** Two extra 12 × 7 mm wire pass-throughs: one at the lower left by the camera harness (KiCad 160°, CAD 200°), and a spare at the upper right (KiCad 330°, CAD 30°).
- **Checks:** DRC 0 (warnings included), schematic parity 0, ERC 0, `verify_A.py` all pass. Pictures: `renders/layoutA_v8_*`, `renders/onshape_v8_*`.
- **Onshape:**
  - The new STEP replaced the old one (blob tab "Update"), so Import 1 and the composite part refreshed. The stack Part Studio picked it up.
  - "PCB outline preview 1" was deleted, since the real board is 5.72 in now.
  - The pin-switch stack still reports 0 clashes.

## Routing clean-up (v12, 6 Oct 2026)

Total copper length went from 761 mm to 650 mm (−111 mm, −15 %). DRC 0, parity 0, `verify_A.py` all pass.

| Change | Saving |
|---|---|
| Camera harness J3 moved from the far left to just past the end of the J2 column, beside the camera's wire-pad edge (the camera board's pads now face right, toward the ESP32) | CAM_RX/TX 134 → 78 mm, +5 V 131 → 89 mm |
| CAM_RX/TX run straight down on the front under BT2 (2 vias each), because the back of that strip holds the status LED and a camera standoff | |
| +5 V to the camera: front L from the regulator vias, past the end of J2, one via at J3-1 | |
| VSW (camera switch → D3): one diagonal right of J3 instead of the old zig-zag | 66 → 64.5 mm |
| J5/J6 turned 180° so pin 1 (switched +) faces the switched line and pin 2 faces the cell's −; their "+ / −" silk swapped to match | COTS 8 mm shorter, no jogs |
| COTS_BAT+ takes the diagonal past H5 | −3.6 mm |

Pin numbers didn't change, so the schematic is unchanged. The J5/J6 latches now face the other way.

**Onshape is in sync with v12:**
- The board STEP was updated in place.
- "AV bay stack 1" screw holes and "COTS mount plate 1" bolt holes are at 51.5 mm below the centre (they were 50).
- The pin-switch stack reports 0 clashes, with its holes matching H5/H6.

## Rebuild

`tools/layoutA/build_A.sh OUT.kicad_pcb` regenerates this board from the seed board
(`tools/layoutA/seed_user_1224.kicad_pcb`). Close KiCad first. It **discards hand edits** to
`battery_pcb.kicad_pcb`, so make changes in the scripts (see README, "Rebuilding").

## v14 — J6 to the Aerolotl is a JST XH (6 Oct 2026)
- J6 (SRAD OUT) changed from Molex Micro-Fit 3.0 to JST XH B2B-XH-A (2.5 mm pitch, vertical) at the user's request to match the Aerolotl harness. XH is friction-fit, not positive-latching.
- Pin 1 = switched SRAD + (x 40), pin 2 = SRAD battery − (x 37.5); route_A reads the J6 pads from the placed footprint.
- v13 (same day): TeleMetrum sled holes back at 50 mm (SSI AVBay1 standard), batteries 2.25 mm offset, sled-base courtyards, 0.25 mm holder courtyard.

## v15–v16 — ready to order (6 Oct 2026)
- v15: the back-silk label "ESP32-DevKitC V4 / parts facing down" moved 1.1 mm so it no longer crosses BT3's peg hole (the fab would have cut the letters). No silkscreen text sits over any hole now.
- v16: every symbol carries hidden Manufacturer / MPN fields (`tools/annotate_mpn.py`), and the build copies them onto the footprints (`tools/layoutA/fields_A.py`), so DRC schematic parity stays at 0. F1 is a Littelfuse 1812L200/12DR (2 A hold, 12 V; the 2S pack is 8.4 V max).
- Ordering files in `fab/`: BOM (`tools/make_bom.py`), Gerbers + drill zip, schematic PDF. The tool scripts no longer hard-code paths.
- Geometry is unchanged since v14, so the Onshape models (AVBay1 import) are current. The personal "Switchband Assembly" Onshape doc still holds v12.

## v17 — test points, strict rules, review (6 Oct 2026)
- Test points: TP1 +5V (J1-19, BT3/BT4 gap), TP2 VBAT+ (below BT1's + tab), TP3/TP4 GND. 2 mm through-hole pads in spots open on both sides. Symbols from `tools/add_testpoints.py`, board side in `tools/layoutA`.
- Strict design rules (README, "Design rules"). Fixes they needed: the GND trace under U1 between its pin rows is 0.3 mm (was 0.5), a GND via moved 0.1 mm off R4, VBAT_SENSE now drops onto C8 from above, D3 moved 0.2 mm (silk off D1), TP4's label sits above it (away from a notch).
- R5 47k -> 39k: VBAT_SENSE now tops out at 2.36 V, inside the ESP32 ADC's 11 dB range (2.45 V). Firmware scale: VIN = VBAT_SENSE x 139/39.
- Review: every schematic pin matches its board pad's net (115/115); the LMR51430 symbol is KiCad's library part (GND 1, SW 2, VIN 3, FB 4, EN 5, CB 6; Vref 0.6 V -> 4.98 V out); the ESP32 sockets match Espressif's DevKitC V4 header tables.

## v18 — second review: antenna clearance, stack outline, cut-outs, XT30 (7 Oct 2026)
- **ESP32 antenna.** Espressif asks for at least 15 mm clear around the module's PCB antenna. The DevKitC hangs about 13.4 mm under the board (8.5 mm socket + 2.5 mm header + 1.6 mm devkit + module), antenna toward the top (`kc.ANT`).
  - Back copper: rule area "ESP32 antenna keepout" bans pour, tracks and vias 15 mm to each side of the antenna and 15 mm past its end (it stops at the devkit edge, where the sockets start). It is outlined on the back silk with "ANTENNA KEEP-OUT 15 mm".
  - The old no-pour box only covered part of the antenna; it now covers the whole antenna on the front ("ESP32 antenna: no pour").
  - COTS_SW used to run down the back right beside the antenna. It now leaves SW2 on the front and drops to the back (two 0.8 / 0.4 vias) below the keep-out.
  - Front parts are 15 mm away through the board: the closest is BT3's + tab at 15.0 mm (`verify_A.py` checks every pad in 3D).
  - H5 (pin-switch stack bolt) is right over the antenna: nylon M3 bolt and nut (back silk note).
- **Pin-switch stack outline** on the front silk (45 mm wide, from the holder ends out to the pin faces), labelled "PIN-SWITCH STACK".
- **Two more spare wire pass-throughs** at the upper left, 12 × 7 mm at KiCad 210° and 240° (CAD 150° and 120°). Seven cut-outs in all.
- **J5 / J6 are AMASS XT30UPB-F** (vertical, female on the board = the battery side), 15 mm apart. XT30 pin 1 is minus and pin 2 plus (the housing and KiCad's footprint say so), so the schematic labels on J5/J6 swapped: pin 1 = COTS_BAT− / SRAD_BAT−, pin 2 = COTS_SW / SRAD_SW. KiCad has no XT30 3D model, so `tools/step_boxes.py` makes a box one (`3dmodels/`); the footprint is a project copy pointing at it.
- **Checks:** ERC 0 errors, DRC 0 (strict, with schematic parity), `verify_A.py` all pass (new checks for the antenna, XT30 polarity, cut-outs and the stack outline).
- **Onshape:** the outline changed (two new cut-outs), so the AVBay1 import needs `cad/avbay1_board_and_pin_switch_stack.step` re-uploaded.

## v19 — third review: buck input caps, UVLO, inductor, schematic redraw (8 Oct 2026)
- **Schematic sheets 1–3 redrawn with wires** (`tools/redraw_power_sheets.py`) instead of scattered net labels; every existing symbol keeps its UUID. C1/C2 moved to the buck sheet next to U1.
- **Input caps** (TI LMR51430 datasheet 9.2.2.6: >= 4.7 µF plus 0.1 µF at the pins): C1 is now the 100 nF X7R right at U1's VIN/GND; C2 and the new C11 (10 µF, in the VIN pour below C1/C2) are the bulk.
- **UVLO**: U1 EN was tied to VIN, so the buck ran the 2S pack down to its own 3.58 V UVLO (1.8 V per cell). R9 402k / R10 100k on EN: on above 1.227 × 5.02 = 6.2 V, off below 1.08 × 5.02 = 5.4 V at VIN (pack about 5.7 V, 2.85 V per cell under load). Worst-case EN tolerance: off between 4.8 and 6.1 V, on between 5.5 and 6.8 V at VIN. (412k was the first pick; LCSC has none in stock, so 402k.) EN routes up through a via, over the front, to R9/R10 above C3; R9's VIN comes along the front from the VIN pour via.
- **L1 4.7 → 6.8 µH** (SRN6045TA-6R8M, same footprint): TI's table value for 500 kHz / 5 V out, better for our 0.6–0.83 duty cycle. Isat 5.7 A > the 4.76 A typical current limit.
- **Text fixes**: sheet 3's divider note used the old 47k (now 39k: 2.26 V at a full pack after D3); D3's value said SS34, the part is B340B.
- **Reviewed, no change**: D1 SMBJ12A (a TVS standoff must sit above the 8.4 V full pack; it clamps below 20 V and everything on VIN is rated >= 25 V); D3 drop (~0.35 V / 0.2 W at the ~0.6 A load); F1 2 A (real load is under 0.7 A); output caps 2 × 22 µF + 100 nF (TI table: 2 × 22 µF).
- Layout: two front no-pour areas remove thin GND slivers (between the socket pins, and by the lower-left notch). C11's silk reference is hidden (no room; it stays on the fab layer).
- **Checks:** ERC 0 errors, DRC 0 (strict, schematic parity), `verify_A.py` all pass (new: UVLO divider and input-cap nets).
- **BOM sourcing (8 Oct 2026)**: every soldered part has a checked LCSC number in `fab/battery_pcb_BOM.csv` (LCSC # column), except the Keystone 1042 holders (DigiKey 36-1042-ND) and the Wurth 9774050243R standoffs (DigiKey 732-7097-1-ND). LCSC has no Sullins PPTC191LFBN-RC stock, so J1/J2 list HCTL PM254-1-19-Z-8.5 (C2897382), same 8.5 mm height. `fab/battery_pcb_JLCPCB_BOM.csv` + `_CPL.csv` are for JLCPCB assembly if wanted.

## v20 — hand-assembly pass (8 Oct 2026)
- The GND pours now meet every pad through thermal spokes (0.5 mm, 0.4 gap), SMD pads included, so the 0603 parts, U1's GND pin and BT2's minus tab can be hand-soldered without the plane sinking the iron's heat. The small VIN / +5V / VBAT+ pours keep solid SMD joints.
- Layout review beyond DRC: buck loop (C1 100 nF ~2.4 mm from U1 VIN; GND return via the 0.3–0.8 mm trace under U1), bootstrap path, FB away from SW, power widths, vias per power net, holder/socket clearances, silk polarity marks, keep-outs under the rod washers and sled screws: no changes needed. Assembly order matters (README, "Hand assembly").
