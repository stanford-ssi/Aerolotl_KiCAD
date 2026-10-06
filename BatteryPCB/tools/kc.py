"""Shared helpers for driving pcbnew from KiCad's bundled Python."""
import pcbnew, math

CX = CY = 150.0          # board centre, mm, page coords
DISC_IN = 5.72                   # board diameter, inches (av-bay disc; was 5.82 until 1 Oct 2026)
R_BOARD = DISC_IN * 25.4 / 2     # 72.644 mm
# room for the full-size pin-switch stack flat on the board (5 Oct 2026): the battery holders move 2 mm toward the
# COTS mount (the most that fits in front of its flange / M4 screws / J6), and the ESP32 sockets + regulator + LED
# slide 2 pins toward the centre so J2's top pins come out from under the stack
BAT_DY = 2.25    # was 3.5 (6 Oct). With the sled holes back at 50 mm the TeleMetrum sled base (edge 4 mm in from the holes,
                 # y = 46.0) and the stack carriers (inner edge 36.88 on the other side) leave 1.15 mm in all: split evenly,
                 # 0.55 mm from BT2/BT3 tab tips to the sled, 0.6 mm from the holder ends to the carriers
ESP_DY = 5.08
# J5/J6 (and their labels) move out 1.5 mm, away from the battery holders
COTS_DY = 1.5
# the COTS mount screw holes stay at the SSI av-bay standard (AVBay1 "sled_hole_y" = 50 mm, 6 Oct 2026); only J5/J6 keep the 1.5 mm
COTS_HOLE_Y = 50.0               # COTS mount screw holes, mm below the disc centre (Onshape: "Screw holes: distance below disc center")
FPLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

mm = pcbnew.FromMM
to_mm = pcbnew.ToMM


def P(x, y):
    """Board-relative mm -> VECTOR2I page coords."""
    return pcbnew.VECTOR2I(mm(CX + x), mm(CY + y))


def rel(v):
    return (round(to_mm(v.x) - CX, 3), round(to_mm(v.y) - CY, 3))


def load(path):
    return pcbnew.LoadBoard(path)


def fp_by_ref(board):
    return {f.GetReference(): f for f in board.GetFootprints()}


def pads_of(fp):
    return {p.GetNumber(): (rel(p.GetPosition()), p.GetNetname()) for p in fp.Pads()}
