"""Plot exported board geometry.  (conda python3 with matplotlib)
usage: plot.py GEOM.json OUT.png --view front|back [--win x0 y0 x1 y1] [--labels] [--px 1400]"""
import sys, json, math, argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
from matplotlib.collections import LineCollection

ap = argparse.ArgumentParser()
ap.add_argument("geom"); ap.add_argument("out")
ap.add_argument("--view", default="front")
ap.add_argument("--win", nargs=4, type=float)
ap.add_argument("--labels", action="store_true")
ap.add_argument("--px", type=int, default=1400)
ap.add_argument("--title", default="")
ap.add_argument("--no-rats", action="store_true")
a = ap.parse_args()
g = json.load(open(a.geom))
back = a.view == "back"
X = (lambda x: -x) if back else (lambda x: x)
me, other = ("B", "F") if back else ("F", "B")

def short(n):
    return n.split("/")[-1] if n else ""

POWER = {"VBAT+", "VF", "VSW", "VIN", "+5V", "SW", "Net-(BT1--)", "CBOOT"}
def color(net):
    s = short(net)
    if not net: return "#9a9a9a"
    if s == "GND": return "#1b7f3b"
    if s in POWER: return "#d62728"
    if s.startswith(("COTS", "SRAD")): return "#8e44ad"
    if s == "FB": return "#e67e22"
    return "#1f5fbf"

win = a.win or [-75, -75, 75, 75]
x0, y0, x1, y1 = win
w_mm = x1 - x0
fig = plt.figure(figsize=(a.px / 100, a.px / 100 * (y1 - y0) / w_mm), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
if back:
    ax.set_xlim(-x1, -x0)
else:
    ax.set_xlim(x0, x1)
ax.set_ylim(y1, y0)
ax.set_aspect("equal"); ax.axis("off")
pt_per_mm = (a.px / 100 * 72) / w_mm

ax.add_patch(Circle((0, 0), 73.5, fill=False, lw=1.2, ec="#555"))
# zones
for z in g["zones"]:
    if z["keepout"]:
        for o in z["outline"]:
            ax.add_patch(Polygon([(X(p[0]), p[1]) for p in o], closed=True, fill=False, ec="#ff00aa", lw=1.2, ls="--"))
        continue
    for lay, polys in z["filled"].items():
        col = "#d62728" if lay == "F" else "#1f5fbf"
        if short(z["net"]) == "GND":
            col = "#e8a3a3" if lay == "F" else "#a9c4ec"
        else:
            col = "#f4c542"
        alpha = (0.55 if lay == me else 0.18)
        for pl in polys:
            ax.add_patch(Polygon([(X(p[0]), p[1]) for p in pl["outline"]], closed=True, fc=col, ec="none", alpha=alpha, zorder=1))
            for h in pl["holes"]:
                ax.add_patch(Polygon([(X(p[0]), p[1]) for p in h], closed=True, fc="white", ec="none", alpha=1, zorder=1.1))
    for o in z["outline"]:
        ax.add_patch(Polygon([(X(p[0]), p[1]) for p in o], closed=True, fill=False, ec="#999", lw=0.5, ls=":", zorder=1.2))
for d in g.get("drawings", []):
    (ax0, ay0), (ax1, ay1) = d["bbox"]
    ax.add_patch(Polygon([(X(ax0), ay0), (X(ax1), ay0), (X(ax1), ay1), (X(ax0), ay1)], closed=True, fill=False,
                         ec="#aaa", lw=0.8, ls="--", zorder=1.3))
# courtyards
for f in g["footprints"]:
    mine = f["side"] == me
    for c in f["court"]:
        ax.add_patch(Polygon([(X(p[0]), p[1]) for p in c], closed=True, fill=False,
                             ec=("#c9a400" if mine else "#cccccc"), lw=(0.8 if mine else 0.5), zorder=2))
# tracks
for t in g["tracks"]:
    lay = "F" if t["layer"] == "F.Cu" else "B"
    col = "#c0392b" if lay == "F" else "#2e6fd8"
    ax.plot([X(t["a"][0]), X(t["b"][0])], [t["a"][1], t["b"][1]], color=col, lw=t["w"] * pt_per_mm,
            solid_capstyle="round", alpha=(0.95 if lay == me else 0.35), zorder=(4 if lay == me else 3))
# pads
for p in g["pads"]:
    if p["npth"]:
        ax.add_patch(Circle((X(p["pos"][0]), p["pos"][1]), p["drill"] / 2, fc="black", ec="none", zorder=6))
        continue
    tht = p["F"] and p["B"]
    on_me = p[me]
    for pl in p["poly"]:
        ax.add_patch(Polygon([(X(q[0]), q[1]) for q in pl], closed=True, fc=color(p["net"]),
                             ec="black" if on_me else "none", lw=0.3,
                             alpha=(0.95 if on_me else 0.22), zorder=(5 if on_me else 2.5)))
    if tht and p["drill"]:
        ax.add_patch(Circle((X(p["pos"][0]), p["pos"][1]), p["drill"] / 2, fc="white", ec="none", zorder=5.5))
    if a.labels and on_me and p["net"]:
        ax.text(X(p["pos"][0]), p["pos"][1], short(p["net"]).replace("Net-(BT1--)", "SER"), fontsize=5.5,
                ha="center", va="center", color="black", zorder=9, clip_on=True)
# vias
for v in g["vias"]:
    ax.add_patch(Circle((X(v["pos"][0]), v["pos"][1]), v["d"] / 2, fc="#555", ec="black", lw=0.3, zorder=7))
    ax.add_patch(Circle((X(v["pos"][0]), v["pos"][1]), v["drill"] / 2, fc="white", ec="none", zorder=7.1))
# ratsnest
rats = [] if a.no_rats else g["ratsnest"]
segs = [[(X(r["a"][0]), r["a"][1]), (X(r["b"][0]), r["b"][1])] for r in rats]
cols = [color(r["net"]) for r in rats]
ax.add_collection(LineCollection(segs, colors=cols, linewidths=0.9, alpha=0.9, zorder=8, linestyles="-"))
# refs
for f in g["footprints"]:
    if f["ref"].startswith("H"):
        continue
    mine = f["side"] == me
    ax.text(X(f["pos"][0]), f["pos"][1], f["ref"], fontsize=(7 if mine else 5), ha="center", va="center",
            color=("#7a3e00" if mine else "#b0b0b0"), weight=("bold" if mine else "normal"), zorder=10, clip_on=True)
ttl = a.title or ("%s view%s" % (a.view.upper(), " (mirrored, as seen from the back)" if back else ""))
ax.text(0.01, 0.99, ttl, transform=ax.transAxes, fontsize=10, va="top", ha="left", color="#222")
fig.savefig(a.out, dpi=100, facecolor="white")
print("wrote", a.out)
