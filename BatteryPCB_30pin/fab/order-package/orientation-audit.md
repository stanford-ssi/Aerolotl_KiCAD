# JLC assembly orientation audit — 11 October 2026

Reviewed the 27 selected Bottom placements (18 BOM lines) against fresh KiCad IPC-2581 pad/net exports and the JLC placement preview. All centers and board sides agree with KiCad; coordinate discrepancy is below 0.001 mm. All selected model terminal axes were visually checked. The audit covers included SMT parts, not excluded front parts, ESP32, holders or hand-fit connectors.

## Corrections saved and reuploaded

- Q1 AO3407A / C15155: corrected 180 degrees; final JLC CPL rotation 90 degrees. Gate pin 1 is GND, source pin 2 VIN, drain pin 3 VSW. After reupload the two leads are above and the single lead below, with pin 1 at upper right in Bottom view.
- D2 NCD0805R1 / C84256: corrected 180 degrees; final JLC CPL rotation 180 degrees. Cathode is right, on pad 1 GND; anode is left toward R6, on pad 2 LED_A. JLC minus/plus now match those nets.
- D1 SMBJ12A / C151251: retained 90 degrees. Its cathode is below on VIN, and anode above on GND. JLC minus below and plus above are correct for this unidirectional TVS. The schematic's bidirectional TVS symbol does not convey the selected part's polarity.
- U1 LMR51430XFDDCR / C5219260: retained 90 degrees. All six pin functions agree with the KiCad pad nets; pin 1 is bottom left in Bottom view.
- J3 BM05B-GHS-TBT / C189891: retained 180 degrees. Signal and mounting lead rows match the asymmetric footprint; pin 1 +5V is leftmost in Bottom view.
- C1–C11, R2–R10, L1 and F1 are nonpolar; their model terminal axes match the footprint pads. No rotation corrections required.

The corrected CPL was processed again in JLC, and Q1, D2, D1, U1 and J3 were visually rechecked after import. Screenshots capture the resulting Bottom preview. Both BOM files retain the same reference set as the CPL. No KiCad source footprint was rotated: these are JLC library rotation offsets.

## Practical limits

This verifies preview orientation, not factory placement or full manufacturing readiness. Review JLC's engineering placement confirmation if supplied. U1's separate land-pattern issue remains: the current generic SOT-23-6 has 2.275 mm row separation and 1.325 x 0.60 mm pads; TI's recommended DDC example uses 2.70 mm row separation and 1.10 x 0.60 mm pads. Pin order and rotation match, but resolve that solder/paste compatibility before purchasing assembly. No land-pattern changes were made in this audit.

Quote remains $75.10 before shipping/tax: 5 bare boards, 2 with Bottom assembly, 54 total placements. No order/payment placed.

## Manufacturer and JLC references

- [AO3407A pinout](https://www.aosmd.com/res/datasheets/AO3407A.pdf)
- [TI LMR51430 pinout and DDC package drawing](https://www.ti.com/lit/ds/symlink/lmr51430.pdf)
- [Littelfuse SMBJ data sheet](https://www.littelfuse.com/assetdocs/tvs-diodes-smbj-series-datasheet?assetguid=ba555e99-a12d-4f72-a0b6-86b06c67171e)
- [JST GH dimensions](https://www.jst-mfg.com/product/pdf/eng/eGH.pdf)
- [JLC plus/minus and orientation conventions](https://jlcpcb.com/help/article/pcb-assembly-faqs-part-2)
