"""Dump every footprint, pad and net on the board (board-relative mm)."""
import sys, pcbnew, kc
b = kc.load(sys.argv[1] if len(sys.argv) > 1 else "battery_pcb.kicad_pcb")
nets = {}
for f in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    pos = kc.rel(f.GetPosition())
    print("%-4s %-26s %-44s %s (%7.2f,%7.2f) rot %6.1f" % (
        f.GetReference(), f.GetValue()[:26], f.GetFPIDAsString()[:44],
        "B" if f.IsFlipped() else "F", pos[0], pos[1], f.GetOrientationDegrees()))
    for p in f.Pads():
        pp = kc.rel(p.GetPosition()); sz = p.GetSize(pcbnew.F_Cu) if hasattr(p, "GetSize") else None
        try:
            szs = "%.2fx%.2f" % (kc.to_mm(sz.x), kc.to_mm(sz.y))
        except Exception:
            szs = "?"
        n = p.GetNetname()
        print("       pad %-3s (%7.2f,%7.2f) ang %6.1f %-9s %s" % (p.GetNumber(), pp[0], pp[1], p.GetOrientationDegrees(), szs, n))
        nets.setdefault(n, []).append("%s.%s" % (f.GetReference(), p.GetNumber()))
print("\nNETS")
for n in sorted(nets):
    print("  %-40s %s" % (n, " ".join(nets[n])))
print("\nZONES", [(z.GetNetname(), z.GetLayerName(), z.GetAssignedPriority(), z.IsOnLayer(pcbnew.B_Cu)) for z in b.Zones()])
print("TRACKS", len(b.GetTracks()))
ds = b.GetDesignSettings()
print("board thickness", kc.to_mm(ds.GetBoardThickness()), "copper layers", b.GetCopperLayerCount())
