"""Routing step 1: hand-route the LTE feed on the unrouted board, then export a
Specctra .dsn for Freerouting. Run with KiCad's python, after build.sh."""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design  # noqa: E402

MM = pcbnew.FromMM
OX, OY = 100.0, 60.0
base = os.path.join(design.OUT_DIR, design.PROJECT)

# LTE feed, all on B.Cu, next to the In2 ground plane, 0.3 mm wide.
RF_TRACKS = {
    "rect": {
        "/RF_LTE": [[(15.75, 10.875), (15.75, 9.6)], [(14.76, 9.6), (15.75, 9.6)]],
        "/RF_M1": [[(15.75, 8.59), (15.75, 7.51)], [(14.76, 8.05), (15.75, 8.05)]],
        "/RF_ANT": [[(15.75, 6.49), (15.75, 4.925)], [(14.76, 6.55), (15.75, 6.55)],
                    [(15.75, 5.5), (17.9, 5.5), (19.7, 3.7), (19.7, 3.0)]],
    },
    "oval": {
        "/RF_LTE": [[(14.0, 9.925), (14.0, 8.65)], [(13.01, 8.65), (14.0, 8.65)]],
        "/RF_M1": [[(14.0, 7.64), (14.0, 6.56)], [(13.01, 7.1), (14.0, 7.1)]],
        "/RF_ANT": [[(14.0, 5.54), (14.0, 3.975)], [(13.01, 5.6), (14.0, 5.6)],
                    [(14.0, 4.6), (17.0, 4.6), (17.5, 4.1), (18.1, 3.9)]],
    },
}[design.VARIANT]


def add_rf(board):
    for net, lines in RF_TRACKS.items():
        ni = board.FindNet(net)
        for line in lines:
            for (x0, y0), (x1, y1) in zip(line, line[1:]):
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbnew.VECTOR2I(MM(OX + x0), MM(OY + y0)))
                t.SetEnd(pcbnew.VECTOR2I(MM(OX + x1), MM(OY + y1)))
                t.SetWidth(MM(0.3))
                t.SetLayer(pcbnew.B_Cu)
                t.SetNet(ni)
                t.SetLocked(True)
                board.Add(t)


def patch_dsn(path):
    """KiCad exports the 'no zone fill' antenna area as a full keep-out and the
    ground layer as a signal layer: fix both for the autorouter."""
    L = open(path).read().split("\n")
    out, i = [], 0
    while i < len(L):
        if L[i].startswith('    (keepout "" (polygon'):      # board-level rule area
            depth = L[i].count("(") - L[i].count(")")
            i += 1
            while depth > 0:
                depth += L[i].count("(") - L[i].count(")")
                i += 1
            continue
        out.append(L[i])
        i += 1
    s = "\n".join(out)
    k = s.index("(layer In2.Cu")
    j = s.index("(type signal)", k)
    s = s[:j] + "(type power)" + s[j + len("(type signal)"):]
    open(path, "w").write(s)


def main():
    board = pcbnew.LoadBoard(base + ".kicad_pcb")
    if any(t.GetClass() == "PCB_TRACK" for t in board.GetTracks()):
        raise SystemExit("board already has tracks: run build.sh first to start from the unrouted board")
    add_rf(board)
    # the inner plane must stay out of the antenna strip
    for z in board.Zones():
        if z.GetZoneName() == "GND_PLANE":
            o = z.Outline()
            o.RemoveAllContours()
            o.NewOutline()
            for x, y in design.fill_outline():
                o.Append(MM(OX + x), MM(OY + y))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(base + ".kicad_pcb", board)
    if not pcbnew.ExportSpecctraDSN(board, base + ".dsn"):
        raise SystemExit("DSN export failed")
    patch_dsn(base + ".dsn")
    print("prepared:", base + ".dsn")


main()
