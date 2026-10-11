# Battery PCB quotation package — 11 October 2026

Compare 5 fabricated boards with either no assembly or 2 boards assembled on the Bottom side. No purchase has been placed.

## Files to upload

1. `battery-pcb-gerbers.zip`: bare-board fabrication; 2 copper layers, masks, silkscreens, paste, board outline, and separate plated/nonplated Excellon drill files. Includes the current square tie cutouts from the saved board. The Gerber ZIP is the same for both quotes.
2. `BOM-quote.csv`: partial assembly using equivalent Basic capacitors/resistors for a lower-cost quote. Grouped BOM with exact JLC column headers.
3. `CPL-bottom.csv`: 27 Bottom placements, millimetres, normalized rotations. Upload this with the partial BOM. Reference sets match exactly. Coordinates checked against an independent PCB IPC-2581 export within 0.001 mm.
4. `BOM-exact.csv`: optional alternative retaining the schematic's exact manufacturer parts. The original 100 nF 0603 C1591 may require preorder/minimum quantity; do not upload this unintentionally when requesting the lower-cost quote.
5. `assembly-scope.csv`: each exported electrical footprint and whether it is assembled or excluded.
6. `hand-fit-shopping-list.csv`: excluded parts and modules to procure separately; original shopping quantities cover 2 populated boards plus spares. It is not an assembly BOM.

## Included and excluded parts

Assemble C1–C11, D1/D2, F1, J3, L1, Q1, R2–R10 and U1: 27 placements per populated board, 18 unique BOM lines. J3 is the small back-side SMT camera connector.

Exclude all front parts, all battery holders, J5/J6 XT30, SW1–SW3 Micro-Fit, J1/J2 ESP32 sockets, mounting hardware, test-point hardware, batteries, camera and ESP32 module. Gerbers retain all pads for later hand assembly. The three other boards arrive without any components.

## Quote-only substitutions

| References | Original | Proposed part | JLC number |
|---|---|---|---|
| C3 C6 C8 C10 | Samsung CL10B104KB8NNNC | Yageo CC0603KRX7R9BB104, 100 nF 50 V X7R ±10%, 0603 | C14663 |
| R2 R4 R10 | Yageo 100 kΩ | Uni-Royal 0603WAF1003T5E, 100 kΩ ±1%, 0603 | C25803 |
| R3 | Yageo 13 kΩ | Uni-Royal 0603WAF1302T5E, 13 kΩ ±1%, 0603 | C22797 |
| R5 | Yageo 39 kΩ | Uni-Royal 0603WAF3902T5E, 39 kΩ ±1%, 0603 | C23153 |
| R6 R8 | Yageo 1 kΩ | Uni-Royal 0603WAF1001T5E, 1 kΩ ±1%, 0603 | C21190 |
| R7 | Yageo 100 Ω | Uni-Royal 0603WAF1000T5E, 100 Ω ±1%, 0603 | C22775 |

These substitutions are in the quote BOM only, not the schematic. Verify matched part specifications in JLC before deciding to buy.

## Ordering walkthrough

Upload ZIP to JLC. Keep dimensions automatically detected from Gerbers (142.48 × 145.29 mm), FR-4, 2 layers, 1.6 mm, 1 oz copper, 5 boards, green soldermask, white silkscreen, LeadFree HASL and normal build time. Aerospace classification automatically adds a Kelvin-test charge. This same selection must be used for both comparisons.

For PCB-only, leave PCB Assembly off; no BOM/CPL is required. For partial assembly, enable PCB Assembly, Economic, Bottom Side, quantity 2, tooling holes added by JLC, then upload BOM-quote.csv and CPL-bottom.csv. Verify exactly 27 placements on Bottom. Do not add the excluded connectors or holders during matching.

Before paying, inspect the placement preview, especially U1 pin 1, Q1 gate/source/drain, D1 cathode and D2 polarity. Read-only DRC is clean (0 errors, 0 warnings, 0 unconnected). DRC does not verify the untested custom mechanical fits or installed-module height. The detailed earlier review retains those limitations. No automatic manufacturing-validator READY claim was used because its parsed track/net counts were zero.

J5/J6 are hand fitted with male XT30UPB-M, C428721. Cable mates are female XT30U-F, C99102. PCB footprint/cached MPN still have a legacy -F name; do not order female board connectors from that stale metadata.

## Live quote captured 11 October 2026 (USD)

| Option | Board quantity | Assembled quantity | Before shipping/tax |
|---|---:|---:|---:|
| Bare boards | 5 | 0 | $33.51 |
| Partial Bottom assembly | 5 | 2 | $75.10 |
| Added cost of assembly and selected parts | — | 2 | $41.59 |

PCB price: engineering $4.00, boards $10.00, lead-free HASL $1.60, mandatory aerospace 4-wire Kelvin test $17.91.

Partial assembly price: setup $8.24, stencil $1.55, components $9.82, Extended component fees $21.63, SMT assembly $0.35. All 18 part types matched. The quote covers 54 placements across two boards, not five assembled boards. Component costs include JLC purchasing quantities/allowances, which can exceed the installed quantities. Front parts, modules and large connectors must be bought and installed separately under either option.

The initial PCB-only page displayed a default US DHL Express DDP estimate of $31.23; this is not a confirmed assembly shipping quote. Final shipping, tax and discounts depend on checkout. Quoted build time: PCB 2 days plus assembly 1–2 days.


At this quantity, partial assembly costs about $20.80 extra per populated board and avoids placing 54 small parts by hand. If your priority is the lowest cash cost and you can solder these packages, choose bare boards; remember to add your separately purchased SMT parts to that comparison. For assembly, use the optimized BOM, not the full project shopping BOM.

After deciding, use the saved quote for partial assembly, or upload the same Gerber ZIP with Assembly disabled for bare boards. Review the configuration and final shipping price, then complete checkout yourself. After purchase, respond to any JLC engineering questions and review its placement confirmation before production where offered.

## Basic substitutions applied to the design

C1 now uses YAGEO CC0805KRX7R9BB104 (C49678); C4/C5 use Samsung CL21A226MAQNNNE (C45783), with their displayed rating updated from 16 V to 25 V; D2 uses NationStar NCD0805R1 (C84256). Manufacturer, MPN and LCSC fields match between the schematic and saved PCB. Their footprints, locations, rotations and nets are retained. Q1 remains AO3407A. D2's specified operating range is now -30 to +85 C and its brightness differs from the original LED.

These changes reduced Extended part types from ten to seven. The revised live quote is $75.10 (previously $86.52), a $11.42 saving including component-price/minimum-quantity differences. Partial assembly adds $41.59 to the $33.51 PCB-only price. All 18 part types remain confirmed, with 27 back-side placements per assembled board and two boards assembled.

The other Basic passive substitutions listed above remain quote-only. BOM-exact.csv follows the updated schematic part selections; BOM-quote.csv includes the additional quote-only substitutions.
