"""Two-panel picture of the copper layers, coloured by what each net does.
usage: layers.py GEOM.json OUT.png   (conda python3 + matplotlib)"""
import sys, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Patch
from matplotlib.lines import Line2D

g = json.load(open(sys.argv[1]))
def short(n): return n.split("/")[-1] if n else ""
GROUPS = [  # (name, test, track colour, pour colour)
    ("GND", lambda s: s == "GND", "#1e8449", "#bfe3cb"),
    ("+5V", lambda s: s == "+5V", "#e67e22", "#f9d3a8"),
    ("Buck input (VIN)", lambda s: s == "VIN", "#b7950b", "#f6e49a"),
    ("2S battery / switch (VBAT+, VF, VSW, series link, SW node)",
     lambda s: s in ("VBAT+", "VF", "VSW", "SW", "CBOOT", "Net-(BT1--)"), "#c0392b", "#f3b8b0"),
    ("COTS altimeter supply", lambda s: s.startswith("COTS"), "#7d3c98", "#dcc6e8"),
    ("SRAD flight-computer supply", lambda s: s.startswith("SRAD"), "#c2185b", "#f4c3d8"),
    ("Signals (UART, LED, sense, FB)", lambda s: True, "#2e6fd8", "#c9dbf7"),
]
def grp(net):
    s = short(net)
    for i, (_, t, _, _) in enumerate(GROUPS):
        if t(s):
            return i
    return len(GROUPS) - 1

fig, axes = plt.subplots(1, 2, figsize=(22, 11.6), dpi=100)
fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.08, wspace=0.03)
LABELS = {
    "F": [(-37.3, -45.6, "series link\nBT1- to BT2+"), (-4.0, 30, "COTS+ up\nto vias"),
          (22.8, 3, "SRAD+\nto SW3"), (10, -31.2, "COTS- to J5"), (8, -49.5, "SRAD- to J6"),
          (38.6, 19.6, "+5V to ESP32"), (-49, 31, "VBAT+ to\nfuse vias"),
          (-26.2, 29.5, "pack GND\n+ vias"), (62.5, -34.5, "no copper\n(antenna)"),
          (0, -64, "GND pour, whole board")],
    "B": [(-4, 36.2, "VF: fuse to power switch"), (8, -17, "COTS+\nto SW2"),
          (45, -3.2, "buck"), (49, 21.5, "+5V to\ncamera"), (62.5, 23, "UART"),
          (30.2, -8, "VBAT\nsense"), (-47.5, 27.8, "F1"), (62.5, -34.5, "no copper\n(antenna)"),
          (28, -41, "COTS/SRAD\nswitch legs"), (0, -64, "GND pour, whole board")],
}
for ax, (L, title) in zip(axes, (("F", "FRONT copper (top side: batteries, ESP32, connectors)"),
                                 ("B", "BACK copper (bottom side: all the small parts)\nseen through the board from the top, like KiCad's default view"))):
    ax.set_xlim(-76, 76); ax.set_ylim(76, -76); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(title, fontsize=13)
    ppm = (22 * 0.49 * 72) / 152.0
    ax.add_patch(Circle((0, 0), 73.5, fc="#fafafa", ec="#444", lw=1.2, zorder=0))
    for z in g["zones"]:
        if z["keepout"]:
            if L in z["layers"]:
                for o in z["outline"]:
                    ax.add_patch(Polygon(o, closed=True, fill=False, ec="#ff00aa", lw=1.4, ls="--", zorder=6))
            continue
        for pl in z["filled"].get(L, []):
            col = GROUPS[grp(z["net"])][3]
            ax.add_patch(Polygon(pl["outline"], closed=True, fc=col, ec="none", zorder=1))
            for h in pl["holes"]:
                ax.add_patch(Polygon(h, closed=True, fc="#fafafa", ec="none", zorder=1.1))
    for t in g["tracks"]:
        if t["layer"] != ("F.Cu" if L == "F" else "B.Cu"):
            continue
        ax.plot([t["a"][0], t["b"][0]], [t["a"][1], t["b"][1]], color=GROUPS[grp(t["net"])][2],
                lw=max(t["w"] * ppm, 0.8), solid_capstyle="round", zorder=3)
    for p in g["pads"]:
        if p["npth"]:
            ax.add_patch(Circle(p["pos"], p["drill"] / 2, fc="black", ec="none", zorder=5)); continue
        if not p[L]:
            continue
        for q in p["poly"]:
            ax.add_patch(Polygon(q, closed=True, fc=GROUPS[grp(p["net"])][2] if p["net"] else "#999",
                                 ec="black", lw=0.3, zorder=4))
        if p["drill"]:
            ax.add_patch(Circle(p["pos"], p["drill"] / 2, fc="white", ec="none", zorder=4.5))
    for v in g["vias"]:
        ax.add_patch(Circle(v["pos"], v["d"] / 2, fc=GROUPS[grp(v["net"])][2], ec="black", lw=0.3, zorder=4.6))
    for x, y, s in LABELS[L]:
        ax.text(x, y, s, fontsize=9, ha="center", va="center", zorder=10,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#666", lw=0.6, alpha=0.9))
handles = [Patch(fc=c2, ec=c1, lw=2, label=n) for n, _, c1, c2 in GROUPS]
handles += [Line2D([0], [0], marker="o", color="w", markerfacecolor="#1e8449", markeredgecolor="k", markersize=7,
                   label="via (GND stitching vias tie the two GND pours together)"),
            Patch(fc="white", ec="#ff00aa", ls="--", label="antenna keepout (no pour)")]
fig.legend(handles=handles, loc="lower center", ncol=5, fontsize=10, frameon=False,
           title="pale fill = copper pour, solid line = trace (drawn at real width)")
fig.suptitle("CamControl copper layers", fontsize=16)
fig.savefig(sys.argv[2], facecolor="white")
print("wrote", sys.argv[2])
