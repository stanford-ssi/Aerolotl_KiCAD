# Battery PCB — AV bay power, arming and camera board

The battery board for the SSI IREC AV bay: it holds the cells for both flight computers
(each with its own pin-switch arming plug) and a 2S pack that powers an ESP32 and a
RunCam Split 4 camera on the back. Formerly called CamControl.

Open `battery_pcb.kicad_pro` in KiCad 10. The board is a 5.72 in (145.3 mm) round, 2-layer disc
for the AV bay, placed and fully routed.

**Status (v17, 6 Oct 2026):** ERC 0 errors · DRC 0 violations (warnings included) under the strict rules below, with full schematic parity ·
`tools/layoutA/verify_A.py` ALL PASS. Ready to order: see [Ordering](#ordering).
[`LAYOUT_NOTES.md`](LAYOUT_NOTES.md) has the history of every layout decision.

---

## What's on it

| Block | Parts |
|---|---|
| 2S pack for camera + ESP32 | BT1, BT2 in series → 7.4 V nom / 8.4 V max |
| Input protection | F1 2 A polyfuse → SW1 (camera power switch plug) → D3 Schottky reverse-polarity diode → D1 SMBJ12A TVS |
| Buck 8.4 V → 5.0 V | U1 LMR51430 + L1 + FB divider |
| ESP32-DevKitC V4 socket | J1, J2 — 2 × 1×19 female headers |
| Camera harness | J3 — JST GH 5-pin (+5V, GND, RX, TX, VIDEO), on the back |
| Camera mount | H7–H10 — four M2 × 5 mm SMT standoffs on a 25.5 mm square, on the back |
| Status LED | R6 + D2 on GPIO2 |
| Pack voltage telemetry | R4 100k / R5 39k divider + C8 → GPIO34 (`VBAT_SENSE = VIN × 39/139`, ≤ 2.36 V) |
| Test points | TP1 +5V (buck output), TP2 VBAT+ (2S pack, before the fuse), TP3/TP4 GND: 2 mm through-hole pads, open on both sides |
| COTS supply | BT3 → SW2 (COTS pin switch plug) → J5 Micro-Fit to the TeleMetrum |
| SRAD supply | BT4 → SW3 (SRAD pin switch plug) → J6 JST XH to the Aerolotl |

Harness connectors are latching Molex Micro-Fit 3.0 (SW1–SW3, J5) and JST GH (J3), per the
design review. J6 is a JST XH at the team's request to match the Aerolotl harness; it is
friction-fit, so secure the plug in flight.

---

## Three design decisions worth knowing

### 1. The Split 4 has no GPIO shutter line

Its harness is **VCC / GND / Video**. Recording start/stop is done over **UART**
using the RunCam Device Protocol on the TX/RX pads, not a single logic pin.

So the schematic wires **UART2** (GPIO17 TX, GPIO16 RX) to the camera through
100 Ω series resistors. UART0 is left free so you can still program and debug
over USB.

The camera connects to this board through the 5-pin J3 harness only (no
button-pad wiring).

### 2. Everything runs off one 5 V buck

The camera accepts 5–20 V, so 2S could feed it directly — but RunCam explicitly
warns to power it from a regulator rather than a raw battery bus.

Feeding the ESP32 8.4 V directly would also be a problem: the devkit's onboard
AMS1117 would drop 8.4 → 3.3 V and burn about **1.3 W** in a SOT-223. It would
run very hot.

One LMR51430 at 5 V solves both. The ESP32's regulator then only drops 5 → 3.3 V,
and the camera gets a clean supply.

Feedback divider: `Vout = 0.6 × (1 + 100k / 13k7) = 4.98 V`

### 3. COTS and SRAD grounds are deliberately isolated

`COTS_BAT-` and `SRAD_BAT-` are **not** tied to `GND`.

DTEG §6.9.1 requires completely independent recovery systems — separate power
supplies included. Tying the returns together would create a shared failure path
and defeat that. Each of those two cells is its own island: own cell, own switch,
own two-wire output.

Do not "clean this up" by merging the grounds.

---

## Which ESP32

Buy the **Espressif ESP32-DevKitC V4 with a WROOM module: `ESP32-DevKitC-32E`** (or `-32UE` for an
external antenna). The sockets are 2 × 19 pins with the rows 1.0 in (25.4 mm) apart, wired to
Espressif's V4 header table pin for pin.

- **Not the WROVER version (`ESP32-DevKitC-VE`):** it uses GPIO16/17 for its PSRAM, and this board uses
  them for the camera UART.
- **Not a 30-pin (2 × 15) "ESP32 DevKit" clone:** it won't fit the 2 × 19 sockets. The AVBay1 Onshape model
  currently shows a 2 × 15 DevKit; it should be the 38-pin DevKitC.
- It plugs in from the **back**, components facing away from this board, antenna end toward the top
  (the "ANTENNA END" silkscreen).

## ESP32 pin map

| Function | Pin | Net |
|---|---|---|
| 5 V in | J1-19 | `+5V` |
| GND | J1-14, J2-1, J2-7 | `GND` |
| Camera UART TX | J2-11 (GPIO17) | `ESP_TX2` → R7 → `CAM_RX` |
| Camera UART RX | J2-12 (GPIO16) | `ESP_RX2` → R8 → `CAM_TX` |
| Status LED | J2-15 (GPIO2) | `LED_GPIO` → R6 → D2 |
| Pack voltage | J1-5 (GPIO34, ADC1) | `VBAT_SENSE` |

J1 is the devkit's left header (3V3 … 5V) and J2 the right header (GND … CLK),
both counted from the **antenna end**, which faces the top of the board.

Every unused header pin is broken out to a named net (`L06_IO35`, `R09_IO18`, …)
so you can see what's free. Those produce 31 `isolated_pin_label` ERC warnings —
expected and harmless, they're spare breakouts by design.

**GPIO6–11 (`IO6`…`IO11`) are wired to the module's SPI flash. Do not use them.**

---

## Camera mounting

The RunCam Split 4 board (29 × 29 mm, M2 holes on a 25.5 mm square) sits on four Würth
9774050243 M2 × 5 mm SMT standoffs (H7–H10) on the back of this board, next to its J3 harness.
`battery_pcb.pretty/RunCam_Split4_OnStandoffs.kicad_mod` places its 3D outline; it has no pads
and is excluded from the BOM.

Source: [RunCam Split 4 manual](https://www.runcam.com/download/split4k/RC_Split_4k_Manual_EN.pdf)

---

## Open items

1. **The ESP32's Bluetooth is a 2.4 GHz transmitter.** DTEG §4.3.5 forbids
   powering transmitting electronics in the pit area without authorization, and
   2.4 GHz is not in ESRA's Student Band Plan. SW1 exists partly so you can keep
   it off until the pad. Declare this radio in your progress reports.
2. **No SD card module** is on this schematic — you mentioned one for the plate
   but didn't list it in the brief. Easy to add on SPI (GPIO5/18/19/23).
3. **Confirm the camera's logic level.** Most RunCam UART pads are 3.3 V, which
   matches the ESP32 directly. If yours is 5 V, add a level shifter — the 100 Ω
   series resistors are protection, not translation.

Layout-specific items are in [`LAYOUT_NOTES.md`](LAYOUT_NOTES.md).

---

## Design rules

Stricter than the fab's minimums, to leave margin (all in `battery_pcb.kicad_pro`):

| Rule | Value |
|---|---|
| Copper clearance | 0.25 mm signals, 0.3 mm power and ground, 0.4 mm for the isolated COTS/SRAD battery nets |
| Track width (min) | 0.25 mm; pyro paths ≥ 1.0 mm, 2S power ≥ 1.5 mm (checked by `verify_A.py`) |
| Copper to board edge | 0.5 mm |
| Hole clearance / hole to hole | 0.3 mm / 0.5 mm |
| Via | ≥ 0.6 mm pad, 0.3 mm drill (0.15 mm ring); power vias 0.8 / 0.4 mm |
| Silkscreen | 0.15 mm to other silk and to the edge; text ≥ 0.8 mm |

DRC runs with every check as an error (`tools/drc.sh`).

---

## Ordering

Everything to order is in `fab/`:

| File | What it is |
|---|---|
| `fab/battery_pcb_BOM.csv` | Ordering BOM: every soldered part with manufacturer + MPN (paste the MPNs into the DigiKey or Mouser BOM tool), plus the camera standoffs, plug-in modules, cells, cable-side connectors and the PCB. "Order qty" covers 2 boards plus spares. |
| `fab/battery_pcb_gerbers.zip` | Gerbers + drill file. Upload as-is to JLCPCB (or any fab): 2 layers, 1.6 mm FR-4, 1 oz copper. |
| `fab/battery_pcb_schematic.pdf` | The schematic, for review and for soldering. |

`cad/battery_pcb.step` is the board with all parts for CAD.
`cad/avbay1_board_and_pin_switch_stack.step` is the board plus the exact pin-switch stack,
raised 18 mm into the Onshape stack frame; it is what the SSI AVBay1 Onshape document imports.

---

## Rebuilding

The layout is generated by scripts so it can be rebuilt after a change. Close KiCad first
(it rewrites project files when it quits), and use KiCad 10 on macOS (the scripts call its
bundled Python and `kicad-cli`).

```
tools/layoutA/build_A.sh /tmp/new.kicad_pcb   # place, route, labels, fields, refill, DRC, verify
cp /tmp/new.kicad_pcb battery_pcb.kicad_pcb
python3 tools/annotate_mpn.py                 # after changing a part: edit PARTS in it first
python3 tools/make_bom.py                     # rewrites fab/battery_pcb_BOM.csv
```

`tools/layoutA/` starts from `seed_user_1224.kicad_pcb`, the hand-placed version, so hand edits
to `battery_pcb.kicad_pcb` are lost on the next rebuild: make changes in the scripts instead.
`tools/kc.py` holds the shared dimensions (disc size, battery and connector offsets). The one-shot
generators that made the very first versions are archived in `tools/obsolete/`; don't re-run them.
