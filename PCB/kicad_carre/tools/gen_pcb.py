"""Generate alert_button.kicad_pcb: outline, 4 layers, placed footprints with
nets from the schematic netlist, antenna keep-out, inner ground plane (In2).
The board is NOT routed. Run with KiCad's bundled python (needs pcbnew)."""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import parse, find, first  # noqa: E402
import design  # noqa: E402

OUT = design.OUT_DIR
PROJECT = design.PROJECT
FPLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
MM = pcbnew.FromMM
OX, OY = 100.0, 60.0   # board origin on the sheet


def P(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


def read_netlist(path):
    t = parse(open(path).read())
    pad_net = {}
    for n in find(first(t, "nets"), "net"):
        name = first(n, "name")[1]
        for node in find(n, "node"):
            pad_net[(first(node, "ref")[1], first(node, "pin")[1])] = name
    comps = {}
    for c in find(first(t, "components"), "comp"):
        ts = first(c, "tstamps")
        comps[first(c, "ref")[1]] = ts[1] if ts else None
    return pad_net, comps


def board_points(y_max=None, n=180):
    """Board contour as a point list; with y_max, only the part above y_max."""
    W, H = design.BOARD_W, design.BOARD_H
    if design.SHAPE == "rect":
        return [(0, 0), (W, 0), (W, y_max or H), (0, y_max or H)]
    a, b = W / 2, H / 2
    pts = [(a + a * math.sin(2 * math.pi * i / n), b - b * math.cos(2 * math.pi * i / n))
           for i in range(n)]
    if y_max is not None:      # cap above y_max; points run clockwise from the top
        hw = a * math.sqrt(1 - ((y_max - b) / b) ** 2)
        right = [q for q in pts if q[1] < y_max and q[0] >= a]
        left = [q for q in pts if q[1] < y_max and q[0] < a]
        pts = right + [(a + hw, y_max), (a - hw, y_max)] + left
    return pts


def set_outline(zone, pts):
    o = zone.Outline()
    o.NewOutline()
    for x, y in pts:
        o.Append(MM(OX + x), MM(OY + y))


def inside_board(x, y, margin):
    W, H = design.BOARD_W, design.BOARD_H
    if design.SHAPE == "rect":
        return margin <= x <= W - margin and margin <= y <= H - margin
    a, b = W / 2 - margin, H / 2 - margin
    return ((x - W / 2) / a) ** 2 + ((y - H / 2) / b) ** 2 <= 1


def main():
    pad_net, comps = read_netlist(os.path.join(OUT, PROJECT + ".net"))
    board = pcbnew.CreateEmptyBoard()
    board.SetCopperLayerCount(4)

    nets = {}
    for name in sorted(set(pad_net.values())):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni

    W, H = design.BOARD_W, design.BOARD_H
    edge = pcbnew.PCB_SHAPE(board)
    if design.SHAPE == "rect":
        edge.SetShape(pcbnew.SHAPE_T_RECT)
        edge.SetStart(P(0, 0))
        edge.SetEnd(P(W, H))
    else:
        edge.SetShape(pcbnew.SHAPE_T_POLY)
        edge.SetPolyPoints([P(x, y) for x, y in board_points()])
        edge.SetFilled(False)
    edge.SetLayer(pcbnew.Edge_Cuts)
    edge.SetWidth(MM(0.1))
    board.Add(edge)

    outside = set()
    for p in design.PARTS:
        if not p["fp"]:
            continue
        lib, name = p["fp"].split(":")
        fp = pcbnew.FootprintLoad(FPLIB + lib + ".pretty", name)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(p["ref"])
        fp.SetValue(p["value"])
        if comps.get(p["ref"]):
            fp.SetPath(pcbnew.KIID_PATH("/" + comps[p["ref"]]))
        if p["dnp"]:
            fp.SetDNP(True)
        if p["mpn"]:
            fp.SetField("MPN", p["mpn"])
            for f in fp.GetFields():
                if f.GetName() == "MPN":
                    f.SetVisible(False)
        fp.Reference().SetVisible(False)   # dense board: references live on the Fab layers
        fp.Value().SetVisible(False)
        x, y, rot, side = p["pcb"]
        board.Add(fp)
        fp.SetPosition(P(x, y))
        fp.SetOrientationDegrees(rot)
        if side == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        for pad in fp.Pads():
            net = pad_net.get((p["ref"], pad.GetNumber()))
            if net:
                pad.SetNet(nets[net])
            bb = pad.GetBoundingBox()
            for cx in (bb.GetLeft(), bb.GetRight()):
                for cy in (bb.GetTop(), bb.GetBottom()):
                    if not inside_board(pcbnew.ToMM(cx) - OX, pcbnew.ToMM(cy) - OY, 0.3):
                        outside.add(p["ref"])

    # LTE antenna end: no copper pour on any layer (pads and the RF track are allowed)
    ko = pcbnew.ZONE(board)
    ko.SetIsRuleArea(True)
    ko.SetLayerSet(pcbnew.LSET.AllCuMask(4))
    ko.SetDoNotAllowZoneFills(True)
    ko.SetDoNotAllowTracks(False)
    ko.SetDoNotAllowVias(False)
    ko.SetDoNotAllowPads(False)
    ko.SetDoNotAllowFootprints(False)
    ko.SetZoneName("LTE_ANT_NO_POUR")
    set_outline(ko, board_points(design.LTE_KEEPOUT_H))
    board.Add(ko)

    # Inner ground plane on In2: the layer next to face B (nRF9151, LTE feed)
    gnd = pcbnew.ZONE(board)
    gnd.SetLayer(pcbnew.In2_Cu)
    gnd.SetNetCode(nets["/GND"].GetNetCode())
    gnd.SetZoneName("GND_PLANE")
    gnd.SetAssignedPriority(0)
    gnd.SetLocalClearance(MM(0.2))
    set_outline(gnd, board_points())
    board.Add(gnd)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    pcbnew.SaveBoard(os.path.join(OUT, PROJECT + ".kicad_pcb"), board)

    T = pcbnew.ToMM
    for ref, pads in [("U1", ["35", "14", "65", "24", "19", "56"]), ("U2", ["3", "8", "15", "30"])]:
        fp = board.FindFootprintByReference(ref)
        for pad in fp.Pads():
            if pad.GetNumber() in pads:
                pos = pad.GetPosition()
                print(ref, pad.GetNumber(), pad.GetNetname(), "%.2f %.2f" % (T(pos.x) - OX, T(pos.y) - OY))
    if outside:
        print("WARNING: pads closer than 0.3 mm to the board edge:", sorted(outside))
    print("board written:", len(board.GetFootprints()), "footprints")


main()
