"""Write CamControl net classes + patterns into battery_pcb.kicad_pro (KiCad must be closed)."""
import json, sys, os
PRO = sys.argv[1] if len(sys.argv) > 1 else "battery_pcb.kicad_pro"
# name, track, clearance, via_d, via_drill, priority (lower = wins)
CLASSES = [
    ("Pyro",   1.00, 0.40, 0.80, 0.40, 0),
    ("Power",  1.00, 0.20, 0.80, 0.40, 1),
    ("Signal", 0.30, 0.20, 0.60, 0.30, 2),
]
PATTERNS = {
    # carry real current from the 2S pack
    "Power": ["*/VBAT+", "*/VF", "*/VSW", "*/VIN", "*/+5V", "*/SW", "GND", "Net-(BT1--)"],
    # carry each altimeter's e-match firing current (~10 A for a few ms)
    "Pyro": ["*/COTS_BAT+", "*/COTS_BAT-", "*/COTS_SW", "*/SRAD_BAT+", "*/SRAD_BAT-", "*/SRAD_SW"],
    "Signal": ["*/ESP_TX2", "*/ESP_RX2", "*/CAM_RX", "*/CAM_TX", "*/LED_GPIO", "*/LED_A", "*/VBAT_SENSE", "*/FB", "*/CBOOT"],
}
p = json.load(open(PRO))
ns = p["net_settings"]
default = next(c for c in ns["classes"] if c["name"] == "Default")
default.update({"track_width": 0.30, "clearance": 0.20, "via_diameter": 0.60, "via_drill": 0.30})
out = [default]
for name, tw, cl, vd, vr, pri in CLASSES:
    c = dict(default)
    c.update({"name": name, "track_width": tw, "clearance": cl, "via_diameter": vd, "via_drill": vr, "priority": pri})
    out.append(c)
ns["classes"] = out
ns["netclass_patterns"] = [{"netclass": k, "pattern": pat} for k, pats in PATTERNS.items() for pat in pats]
ds = p["board"]["design_settings"]
ds["track_widths"] = [0.0, 0.25, 0.3, 0.5, 1.0, 1.5, 2.0]
ds["via_dimensions"] = [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.6, "drill": 0.3}, {"diameter": 0.8, "drill": 0.4}]
json.dump(p, open(PRO, "w"), indent=2)
print("net classes:", [(c["name"], c["track_width"], c["clearance"], c["via_diameter"], c["via_drill"], c["priority"]) for c in out])
print("patterns:", len(ns["netclass_patterns"]))
