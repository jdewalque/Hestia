"""Routing step 2: import the Freerouting session, complete what the autorouter
left open with a small grid maze router, add ground fills on the outer layers.
Run with KiCad's python.  Usage: route_finish.py [import|fix]
  import : read the .ses, complete signal nets, add the outer ground zones
  fix    : remove tracks and vias flagged in drc.json (kicad-cli), re-route
           them, and link ground copper that the fills could not reach"""
import heapq
import json
import math
import os
import sys

import numpy as np
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design  # noqa: E402

MM, TO = pcbnew.FromMM, pcbnew.ToMM
OX, OY = 100.0, 60.0
base = os.path.join(design.OUT_DIR, design.PROJECT)
RES = 0.05
NX, NY = int(round(design.BOARD_W / RES)), int(round(design.BOARD_H / RES))
LAYERS = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.B_Cu]      # In2 is the ground plane
CLEAR, VIA_D, VIA_DRILL, MARGIN = 0.127, 0.4, 0.2, 0.04
PLANE_Y0 = design.LTE_KEEPOUT_H + 0.6                   # inner plane starts here


def poly_points(item, layer):
    ps = pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(ps, layer, 0, MM(0.005), pcbnew.ERROR_OUTSIDE)
    res = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        res.append([(TO(o.CPoint(k).x) - OX, TO(o.CPoint(k).y) - OY) for k in range(o.PointCount())])
    return res


def fill_poly(mask, pts):
    """Even-odd fill of one polygon (mm) into a boolean grid; cells whose centre
    is inside, plus every cell touched by a vertex or thin shape centre line."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1 = max(0, int(min(xs) / RES) - 1), min(NX, int(max(xs) / RES) + 2)
    y0, y1 = max(0, int(min(ys) / RES) - 1), min(NY, int(max(ys) / RES) + 2)
    if x0 >= x1 or y0 >= y1:
        return
    gx = (np.arange(x0, x1) + 0.5) * RES
    gy = (np.arange(y0, y1) + 0.5) * RES
    X, Y = np.meshgrid(gx, gy)
    inside = np.zeros(X.shape, bool)
    n = len(pts)
    for i in range(n):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
        if ay == by:
            continue
        cond = (ay > Y) != (by > Y)
        xi = ax + (Y - ay) * (bx - ax) / (by - ay)
        inside ^= cond & (X < xi)
    mask[y0:y1, x0:x1] |= inside


def disk(mask, r):
    """Dilate a boolean grid by a disk of radius r (mm)."""
    k = int(math.ceil(r / RES))
    out = mask.copy()
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            if (dx or dy) and dx * dx + dy * dy <= (r / RES) ** 2 + 1e-9:
                src = mask[max(0, -dy):NY - max(0, dy), max(0, -dx):NX - max(0, dx)]
                out[max(0, dy):NY - max(0, -dy), max(0, dx):NX - max(0, -dx)] |= src
    return out


class Grid:
    def __init__(self, board):
        self.board = board
        self.items = []          # (netname, layer index or None for all, polygons, kind)
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                for li, layer in enumerate(LAYERS):
                    if pad.IsOnLayer(layer):
                        self.items.append((pad.GetNetname(), li, poly_points(pad, layer), "pad"))
                if pad.GetDrillSize().x > 0:
                    c = pad.GetPosition()
                    r = TO(pad.GetDrillSize().x) / 2 + 0.1
                    circ = [(TO(c.x) - OX + r * math.cos(a / 8 * math.pi), TO(c.y) - OY + r * math.sin(a / 8 * math.pi)) for a in range(16)]
                    self.items.append(("<hole>", None, [circ], "hole"))
        for t in board.GetTracks():
            if t.GetClass() == "PCB_VIA":
                self.items.append((t.GetNetname(), None, poly_points(t, pcbnew.F_Cu), "via"))
            else:
                li = LAYERS.index(t.GetLayer()) if t.GetLayer() in LAYERS else None
                if li is not None:
                    self.items.append((t.GetNetname(), li, poly_points(t, t.GetLayer()), "track"))
        # keep-outs for tracks (ESP32 antenna, mic port): all layers
        self.keep = np.zeros((NY, NX), bool)
        zones = list(board.Zones())
        for fp in board.GetFootprints():
            zones += list(fp.Zones())
        for z in zones:
            if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
                o = z.Outline()
                for i in range(o.OutlineCount()):
                    ol = o.Outline(i)
                    fill_poly(self.keep, [(TO(ol.CPoint(k).x) - OX, TO(ol.CPoint(k).y) - OY) for k in range(ol.PointCount())])
        # board edge
        yy, xx = np.mgrid[0:NY, 0:NX]
        px, py = (xx + 0.5) * RES, (yy + 0.5) * RES
        m = 0.3 + 0.2 + MARGIN
        if design.SHAPE == "rect":
            self.edge = (px < m) | (px > design.BOARD_W - m) | (py < m) | (py > design.BOARD_H - m)
        else:
            a, b = design.BOARD_W / 2 - m, design.BOARD_H / 2 - m
            self.edge = ((px - design.BOARD_W / 2) / a) ** 2 + ((py - design.BOARD_H / 2) / b) ** 2 > 1
        self.py = py

    def raster(self, pred):
        g = np.zeros((3, NY, NX), bool)
        for net, li, polys, kind in self.items:
            if pred(net, kind):
                for l in ([li] if li is not None else [0, 1, 2]):
                    for p in polys:
                        fill_poly(g[l], p)
        return g

    def maps(self, net, width, ignore_gnd_vias=False):
        other = self.raster(lambda n, k: n != net and not (ignore_gnd_vias and n == "/GND" and k == "via"))
        own = self.raster(lambda n, k: n == net)
        static = self.keep | self.edge
        blocked = np.stack([disk(other[l], CLEAR + width / 2 + MARGIN) | static for l in range(3)])
        anycu = other[0] | other[1] | other[2]
        pads = self.raster(lambda n, k: k == "pad")
        via_ok = ~(disk(anycu, CLEAR + VIA_D / 2 + MARGIN) | disk(pads[0] | pads[2], VIA_D / 2 + 0.05) | static)
        ownvia = self.raster(lambda n, k: n == net and k == "via")[0]
        return blocked, own, via_ok, ownvia


def components(own, ownvia):
    """Label connected groups of same-net copper (layers joined at vias)."""
    lab = np.zeros(own.shape, np.int32)
    n = 0
    for l in range(3):
        for y, x in zip(*np.nonzero(own[l])):
            if lab[l, y, x]:
                continue
            n += 1
            stack = [(l, y, x)]
            lab[l, y, x] = n
            while stack:
                cl, cy, cx = stack.pop()
                nb = [(cl, cy + 1, cx), (cl, cy - 1, cx), (cl, cy, cx + 1), (cl, cy, cx - 1)]
                if ownvia[cy, cx]:
                    nb += [(k, cy, cx) for k in range(3) if k != cl]
                for q in nb:
                    if 0 <= q[1] < NY and 0 <= q[2] < NX and own[q] and not lab[q]:
                        lab[q] = n
                        stack.append(q)
    return lab, n


MOVES = [(0, 1, 10), (0, -1, 10), (1, 0, 10), (-1, 0, 10), (1, 1, 14), (1, -1, 14), (-1, 1, 14), (-1, -1, 14)]


def dijkstra(blocked, own, via_ok, ownvia, src, is_target, plane_exit=False):
    free = own | ~blocked
    dist = {}
    prev = {}
    heap = []
    for s in src:
        dist[s] = 0
        heapq.heappush(heap, (0, s))
    while heap:
        d, node = heapq.heappop(heap)
        if d > dist.get(node, 1 << 60):
            continue
        l, y, x = node
        if is_target(node):
            path = [node]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            return path[::-1], False
        if plane_exit and via_ok[y, x] and not own[l, y, x] and y * RES > PLANE_Y0:
            path = [node]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            return path[::-1], True
        for dy, dx, c in MOVES:
            ny, nx = y + dy, x + dx
            if not (0 <= ny < NY and 0 <= nx < NX) or not free[l, ny, nx]:
                continue
            if dx and dy and not (free[l, y, nx] and free[l, ny, x]):
                continue
            q = (l, ny, nx)
            nd = d + (1 if own[l, ny, nx] else c)
            if nd < dist.get(q, 1 << 60):
                dist[q] = nd
                prev[q] = node
                heapq.heappush(heap, (nd, q))
        if ownvia[y, x] or via_ok[y, x]:
            for k in range(3):
                if k != l and free[k, y, x] and (ownvia[y, x] or all(free[m, y, x] for m in range(3))):
                    q = (k, y, x)
                    nd = d + (1 if ownvia[y, x] else 200)
                    if nd < dist.get(q, 1 << 60):
                        dist[q] = nd
                        prev[q] = node
                        heapq.heappush(heap, (nd, q))
    return None, False


def emit(board, net, width, path, own, ownvia, end_via):
    ni = board.FindNet(net)

    def pt(y, x):
        return pcbnew.VECTOR2I(MM(OX + (x + 0.5) * RES), MM(OY + (y + 0.5) * RES))

    def via(y, x):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pt(y, x))
        v.SetWidth(pcbnew.F_Cu, MM(VIA_D))
        v.SetDrill(MM(VIA_DRILL))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(ni)
        board.Add(v)

    def seg(l, a, b):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pt(*a))
        t.SetEnd(pt(*b))
        t.SetWidth(MM(width))
        t.SetLayer(LAYERS[l])
        t.SetNet(ni)
        board.Add(t)

    n_seg = n_via = 0
    i = 0
    while i < len(path) - 1:
        (l0, y0, x0), (l1, y1, x1) = path[i], path[i + 1]
        if l0 != l1:
            if not ownvia[y0, x0]:
                via(y0, x0)
                n_via += 1
            i += 1
            continue
        # run of collinear steps on one layer
        d = (y1 - y0, x1 - x0)
        j = i + 1
        while j < len(path) - 1 and path[j + 1][0] == l0 and \
                (path[j + 1][1] - path[j][1], path[j + 1][2] - path[j][2]) == d:
            j += 1
        if not all(own[p] for p in path[i:j + 1]):      # skip runs lying on existing copper
            seg(l0, path[i][1:], path[j][1:])
            n_seg += 1
        i = j
    if end_via:
        via(*path[-1][1:])
        n_via += 1
    return n_seg, n_via


def net_width(board, net):
    cls = board.FindNet(net).GetNetClassName()
    return {"Power": 0.25, "RF": 0.3}.get(cls, 0.127)


def complete_signals(board):
    """Join every non-ground net that is still in several pieces. Returns the
    board (reloaded from disk when ground vias had to be removed)."""
    nets = sorted({p.GetNetname() for fp in board.GetFootprints() for p in fp.Pads()
                   if p.GetNetname() and not p.GetNetname().startswith("unconnected") and p.GetNetname() != "/GND"})
    for net in nets:
        for _ in range(8):
            grid = Grid(board)
            width = net_width(board, net)
            blocked, own, via_ok, ownvia = grid.maps(net, width)
            lab, n = components(own, ownvia)
            if n <= 1:
                break
            src = [tuple(int(v) for v in q) for q in np.argwhere(lab == 1)]
            path, _ = dijkstra(blocked, own, via_ok, ownvia, src, lambda q: lab[q] > 1)
            if path is None:
                # last resort: route through ground vias and remove the ones in the way
                blocked, own, via_ok, ownvia = grid.maps(net, width, ignore_gnd_vias=True)
                path, _ = dijkstra(blocked, own, via_ok, ownvia, src, lambda q: lab[q] > 1)
                if path is None:
                    print("FAILED:", net, "(%d pieces)" % n)
                    break
                print("completed", net, "segments/vias:", emit(board, net, width, path, own, ownvia, False))
                lim = VIA_D / 2 + CLEAR + max(width, VIA_D) / 2 + 2 * MARGIN
                pts = [((x + 0.5) * RES, (y + 0.5) * RES) for _, y, x in path]
                gone = 0
                for t in list(board.GetTracks()):
                    if t.GetClass() == "PCB_VIA" and t.GetNetname() == "/GND":
                        vx, vy = TO(t.GetPosition().x) - OX, TO(t.GetPosition().y) - OY
                        if any((vx - px) ** 2 + (vy - py) ** 2 < lim * lim for px, py in pts):
                            board.Delete(t)
                            gone += 1
                print("removed", gone, "ground vias in the way of", net)
                pcbnew.SaveBoard(base + ".kicad_pcb", board)
                board = pcbnew.LoadBoard(base + ".kicad_pcb")
                continue
            print("completed", net, "segments/vias:", emit(board, net, width, path, own, ownvia, False))
    return board


def add_gnd_zones(board):
    gnd = board.FindNet("/GND")
    for layer, name in [(pcbnew.F_Cu, "GND_F"), (pcbnew.B_Cu, "GND_B")]:
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNetCode(gnd.GetNetCode())
        z.SetZoneName(name)
        z.SetAssignedPriority(0)
        z.SetLocalClearance(MM(0.2))
        z.SetMinThickness(MM(0.15))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        o = z.Outline()
        o.NewOutline()
        for x, y in design.fill_outline():
            o.Append(MM(OX + x), MM(OY + y))
        board.Add(z)


def stitch_ground(board, step=2.0):
    """Ground vias on a grid wherever there is room, to tie the outer fills to the plane."""
    grid = Grid(board)
    blocked, own, via_ok, ownvia = grid.maps("/GND", 0.25)
    near = disk(ownvia, 1.0)
    gnd = board.FindNet("/GND")
    n = 0
    y = PLANE_Y0 + 0.5
    while y < design.BOARD_H:
        x = 1.0
        while x < design.BOARD_W:
            iy, ix = int(y / RES), int(x / RES)
            if via_ok[iy, ix] and not near[iy, ix]:
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pcbnew.VECTOR2I(MM(OX + (ix + 0.5) * RES), MM(OY + (iy + 0.5) * RES)))
                v.SetWidth(pcbnew.F_Cu, MM(VIA_D))
                v.SetDrill(MM(VIA_DRILL))
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetNet(gnd)
                board.Add(v)
                n += 1
            x += step
        y += step
    print("ground stitching vias:", n)


def step_import():
    board = pcbnew.LoadBoard(base + ".kicad_pcb")
    rf = [(t.GetNetname(), pcbnew.VECTOR2I(t.GetStart()), pcbnew.VECTOR2I(t.GetEnd()), t.GetWidth(), t.GetLayer())
          for t in board.GetTracks() if t.IsLocked()]
    if not pcbnew.ImportSpecctraSES(board, base + ".ses"):
        raise SystemExit("SES import failed")
    # keep the hand-routed LTE feed exactly as drawn; widen autorouter neck-downs
    for t in list(board.GetTracks()):
        if t.GetNetname() in ("/RF_LTE", "/RF_M1", "/RF_ANT"):
            board.Delete(t)
        elif t.GetClass() == "PCB_TRACK" and t.GetWidth() < MM(0.1):
            t.SetWidth(MM(0.1))
    for net, a, b, w, layer in rf:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(a); t.SetEnd(b); t.SetWidth(w); t.SetLayer(layer)
        t.SetNet(board.FindNet(net)); t.SetLocked(True)
        board.Add(t)
    pcbnew.SaveBoard(base + ".kicad_pcb", board)
    board = pcbnew.LoadBoard(base + ".kicad_pcb")
    board = complete_signals(board)
    stitch_ground(board)
    add_gnd_zones(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(base + ".kicad_pcb", board)
    print("imported; tracks+vias:", len(board.GetTracks()))


def fill_raster(board):
    """Ground zone fills of the outer layers as a boolean grid per router layer."""
    g = np.zeros((3, NY, NX), bool)
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetNetname() != "/GND" or z.GetLayer() not in (pcbnew.F_Cu, pcbnew.B_Cu):
            continue
        li = LAYERS.index(z.GetLayer())
        ps = z.GetFilledPolysList(z.GetLayer())
        for i in range(ps.OutlineCount()):
            m = np.zeros((NY, NX), bool)
            o = ps.Outline(i)
            fill_poly(m, [(TO(o.CPoint(k).x) - OX, TO(o.CPoint(k).y) - OY) for k in range(o.PointCount())])
            for h in range(ps.HoleCount(i)):
                hm = np.zeros((NY, NX), bool)
                ho = ps.Hole(i, h)
                fill_poly(hm, [(TO(ho.CPoint(k).x) - OX, TO(ho.CPoint(k).y) - OY) for k in range(ho.PointCount())])
                m &= ~hm
            g[li] |= m
    return g


def complete_ground(board):
    """Link every piece of ground copper that has no via to the inner plane."""
    for _ in range(40):
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        grid = Grid(board)
        blocked, own, via_ok, ownvia = grid.maps("/GND", 0.25)
        own = own | fill_raster(board)
        lab, n = components(own, ownvia)
        plane_via = ownvia & (grid.py > PLANE_Y0)
        main = set(int(v) for v in np.unique(lab[0][plane_via])) - {0}
        rest = [k for k in range(1, n + 1) if k not in main]
        if not rest:
            return
        k = rest[0]
        src = [tuple(int(v) for v in q) for q in np.argwhere(lab == k)]
        path, endvia = dijkstra(blocked, own, via_ok, ownvia, src, lambda q: int(lab[q]) in main, plane_exit=True)
        where = "%.2f, %.2f" % ((src[0][2] + 0.5) * RES, (src[0][1] + 0.5) * RES)
        if path is None:
            print("FAILED: ground piece near", where)
            return
        print("ground link near", where, emit(board, "/GND", 0.25, path, own, ownvia, endvia))


def step_fix():
    """Remove what DRC flagged (tracks too close to something, dangling vias),
    then re-complete signals and ground."""
    board = pcbnew.LoadBoard(base + ".kicad_pcb")
    rep = json.load(open(os.path.join(design.OUT_DIR, "drc.json")))
    kill = []
    for v in rep.get("violations", []):
        if v["type"] in ("clearance", "via_dangling", "track_dangling", "hole_clearance", "shorting_items", "tracks_crossing", "copper_edge_clearance"):
            for it in v["items"]:
                if it["description"].startswith(("Track", "Via")):
                    kill.append((it["pos"]["x"], it["pos"]["y"]))
    n = 0
    for t in list(board.GetTracks()):
        if t.IsLocked():
            continue
        pts = [t.GetStart(), t.GetEnd()] if t.GetClass() == "PCB_TRACK" else [t.GetPosition()]
        if any(abs(TO(p.x) - x) < 0.002 and abs(TO(p.y) - y) < 0.002 for p in pts for x, y in kill):
            board.Delete(t)
            n += 1
    print("removed", n, "flagged tracks/vias")
    pcbnew.SaveBoard(base + ".kicad_pcb", board)
    board = pcbnew.LoadBoard(base + ".kicad_pcb")
    board = complete_signals(board)
    complete_ground(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(base + ".kicad_pcb", board)


if __name__ == "__main__":
    {"import": step_import, "fix": step_fix}[sys.argv[1] if len(sys.argv) > 1 else "import"]()
