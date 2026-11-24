"""Boitier "Galet" pour la carte ovale 28 x 38 mm : maquette a imprimer en 3D.

Produit dans ce dossier : galet_coque_arriere.stl, galet_face_avant.stl,
gabarit_carte.stl, gabarit_batterie.stl et apercu.png.
Dependances : pip install manifold3d trimesh numpy matplotlib

Repere : x = largeur, y = hauteur (+y = beliere), z = epaisseur
(z = 0 : dos du bijou, z = T : face avant). Cotes en mm.
La carte est montee comme sur le dessin KiCad : depart d'antenne LTE en haut,
pres de la beliere, antenne Wi-Fi du module ESP32 en bas. Le ruban LTE part du
haut a droite et fait les trois quarts du tour.
"""
import math
import os

import numpy as np
import manifold3d as m3
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
N = 160                      # segments par ellipse

# ------------------------------------------------------------------ parametres
OUT_W, OUT_H, T = 35.0, 45.0, 12.0      # exterieur
WALL = 2.0                              # paroi laterale -> cavite 31 x 41
FACE = 1.0                              # epaisseur du dos et de la face avant
PCB_W, PCB_H, PCB_T = 28.0, 38.0, 0.8
PCB_Z = 7.5                             # dessous de la carte
SPLIT_Z = PCB_Z + PCB_T                 # plan de joint = dessus de la carte
LAP_H, LAP_T, FIT = 1.2, 0.9, 0.15      # emboitement face avant / coque
ARC_R, CHAMFER = 3.0, 0.9               # arrondi exterieur (imprimable sans support)
CAV_R = 1.2                             # arrondi interieur
GROOVE_Z0, GROOVE_Z1, GROOVE_D = 2.2, 6.2, 0.4   # logement du ruban d'antenne
GROOVE_GAP = 32.0                       # ouverture sans antenne, en haut
BAT = (20.0, 25.0, 5.0)                 # batterie LP502025
BAT_Y = 1.5                             # centre de la batterie


def pcb(px, py):
    """Coordonnees KiCad de la carte ovale -> repere du boitier."""
    return (px - PCB_W / 2, PCB_H / 2 - py)


# ------------------------------------------------------------------ outils
def loft(levels):
    """Solide par empilement d'ellipses : levels = [(z, demi-axe x, demi-axe y)]."""
    ang = np.linspace(0, 2 * math.pi, N, endpoint=False)
    verts, tris = [], []
    for z, a, b in levels:
        verts += [(a * math.cos(t), b * math.sin(t), z) for t in ang]
    L = len(levels)
    for k in range(L - 1):
        for i in range(N):
            j = (i + 1) % N
            p, q, r, s = k * N + i, k * N + j, (k + 1) * N + i, (k + 1) * N + j
            tris += [(p, q, s), (p, s, r)]
    c0, c1 = len(verts), len(verts) + 1
    verts += [(0, 0, levels[0][0]), (0, 0, levels[-1][0])]
    for i in range(N):
        j = (i + 1) % N
        tris += [(c0, j, i), (c1, (L - 1) * N + i, (L - 1) * N + j)]
    mesh = m3.Mesh(vert_properties=np.array(verts, np.float32), tri_verts=np.array(tris, np.uint32))
    return m3.Manifold(mesh)


def edge_inset(d):
    """Retrait du contour exterieur a la distance d d'une face : chanfrein a
    45 degres puis arc, pour s'imprimer face contre le plateau sans support."""
    arc_h = ARC_R * math.sin(math.pi / 4)
    arc_in = ARC_R * (1 - math.cos(math.pi / 4))
    if d >= CHAMFER + arc_h:
        return 0.0
    if d >= CHAMFER:
        h = CHAMFER + arc_h - d
        return ARC_R - math.sqrt(ARC_R ** 2 - h ** 2)
    return arc_in + (CHAMFER - d)


def cav_inset(d):
    if d >= CAV_R:
        return 0.0
    return CAV_R - math.sqrt(CAV_R ** 2 - (CAV_R - d) ** 2)


def zs(z0, z1, step=0.15):
    n = max(2, int(round((z1 - z0) / step)) + 1)
    return list(np.linspace(z0, z1, n))


def outer(z0=0.0, z1=T):
    return loft([(z, OUT_W / 2 - edge_inset(min(z, T - z)), OUT_H / 2 - edge_inset(min(z, T - z))) for z in zs(z0, z1)])


def cavity(z0=FACE, z1=T - FACE):
    a, b = OUT_W / 2 - WALL, OUT_H / 2 - WALL
    lv = []
    for z in zs(z0, z1):
        i = cav_inset(min(z - FACE, T - FACE - z))
        lv.append((z, a - i, b - i))
    return loft(lv)


def ellipse(a, b, z0, z1):
    return loft([(z0, a, b), (z1, a, b)])


def box(cx, cy, sx, sy, z0, z1):
    return m3.Manifold.cube([sx, sy, z1 - z0]).translate([cx - sx / 2, cy - sy / 2, z0])


def cyl(cx, cy, d, z0, z1):
    return m3.Manifold.cylinder(z1 - z0, d / 2, d / 2, 48).translate([cx, cy, z0])


def arc_cut_y(a, b, gap):
    """Ordonnee au-dessus de laquelle l'arc d'ellipse centre en haut mesure gap."""
    t, s, dt = math.pi / 2, 0.0, 1e-4
    while s < gap / 2:
        s += math.hypot(a * math.sin(t), b * math.cos(t)) * dt
        t -= dt
    return b * math.sin(t)


# ------------------------------------------------------------------ pieces
CA, CB = OUT_W / 2 - WALL, OUT_H / 2 - WALL          # demi-axes de la cavite

# Appuis de la carte : 4 plots de 2,2 mm poses sur le fond, hors batterie, a des
# endroits sans composant sur la face B ; ils ne touchent pas la paroi pour
# laisser passer le ruban d'antenne.
SUPPORTS = [pcb(7.7, 3.76), pcb(20.3, 3.76), pcb(7.7, 34.24), pcb(20.3, 34.24)]
# Butees de la face avant, a des endroits sans composant sur la face A.
HOLD = [pcb(14.0, 3.0), pcb(5.5, 30.5), pcb(22.5, 30.5)]
# Ouvertures de la face avant.
BTN = pcb(14.0, 14.9)
LED = pcb(14.0, 8.5)
CHG = [pcb(3.6, 15.2), pcb(24.4, 15.2)]
MIC = pcb(21.15, 11.2)


def back_shell():
    s = outer(0, SPLIT_Z + LAP_H) - cavity(FACE, T - FACE)
    # feuillure : au-dessus du plan de joint, il ne reste que la moitie exterieure de la paroi
    s -= ellipse(CA + LAP_T + FIT, CB + LAP_T + FIT, SPLIT_Z, T)
    for x, y in SUPPORTS:
        s += cyl(x, y, 2.2, FACE - 0.2, PCB_Z)
    # logement du ruban d'antenne LTE sur les trois quarts du contour
    ring = ellipse(CA + GROOVE_D, CB + GROOVE_D, GROOVE_Z0, GROOVE_Z1) - ellipse(CA - 0.1, CB - 0.1, GROOVE_Z0 - 1, GROOVE_Z1 + 1)
    ycut = arc_cut_y(CA, CB, GROOVE_GAP)
    s -= ring - box(0, ycut + 25, 60, 50, 0, T)
    # beliere : boucle a plat, dans le plan du dos
    by = OUT_H / 2
    loop = m3.Manifold.hull(cyl(0, by - 1.0, 7.0, 0, 4.0) + cyl(0, by + 4.5, 7.0, 0, 4.0))
    hole = m3.Manifold.hull(cyl(0, by + 2.0, 3.4, -1, 5.0) + cyl(0, by + 4.5, 3.4, -1, 5.0))
    s += (loop - hole) - cavity(FACE, T - FACE) - ellipse(CA + LAP_T + FIT, CB + LAP_T + FIT, SPLIT_Z, T)
    return s


def front_lid():
    top = outer(SPLIT_Z + LAP_H, T)
    tongue = ellipse(CA + LAP_T, CB + LAP_T, SPLIT_Z + 0.1, SPLIT_Z + LAP_H + 0.01)
    s = (top + tongue) - cavity(FACE, T - FACE)
    for x, y in HOLD:
        s += cyl(x, y, 2.2, SPLIT_Z, T - FACE + 0.2)
    s -= cyl(BTN[0], BTN[1], 7.0, SPLIT_Z, T + 1)          # bouton
    s -= cyl(LED[0], LED[1], 2.0, SPLIT_Z, T + 1)          # LED
    for x, y in CHG:
        s -= cyl(x, y, 2.4, SPLIT_Z, T + 1)                # contacts de charge
    s -= cyl(MIC[0], MIC[1], 1.2, SPLIT_Z, T + 1)          # micro
    return s


def pcb_dummy():
    s = ellipse(PCB_W / 2, PCB_H / 2, 0, PCB_T)
    x, y = pcb(14.0, 24.4 + 2.66)                          # module ESP32-C6 (13.2 x 16.6 x 2.4)
    s += box(x, y, 13.2, 16.6, PCB_T, PCB_T + 2.4)
    s += box(BTN[0], BTN[1], 6.2, 6.2, PCB_T, PCB_T + 2.5)  # bouton
    s += cyl(BTN[0], BTN[1], 3.0, PCB_T, PCB_T + 3.4)
    return s


def battery_dummy():
    return box(0, 0, BAT[0], BAT[1], 0, BAT[2])


def save(man, name, flip=False):
    me = man.to_mesh()
    tm = trimesh.Trimesh(vertices=np.asarray(me.vert_properties)[:, :3], faces=np.asarray(me.tri_verts), process=True)
    if flip:                                 # face exterieure contre le plateau
        tm.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [0, 1, 0]))
    tm.apply_translation([0, 0, -tm.bounds[0][2]])
    tm.export(os.path.join(HERE, name))
    print("%-26s etanche=%s volume=%.2f cm3 boite=%s" % (
        name, tm.is_watertight, tm.volume / 1000, np.round(tm.bounds[1] - tm.bounds[0], 2)))
    return tm


def preview(back, lid, pcbd):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(1, 3, figsize=(15, 6.5))
    for man, col in [(back, "#2e7d5b"), (lid, "#c9a24a")]:
        # coupe x = 0 : (y, z) ; coupe y = 0 : (x, z)
        for ring in man.rotate([0, 90, 0]).slice(0).to_polygons():
            r = np.vstack([ring, ring[:1]])
            ax[0].plot(r[:, 1], r[:, 0], color=col, lw=1.2)
        for ring in man.rotate([90, 0, 0]).slice(0).to_polygons():
            r = np.vstack([ring, ring[:1]])
            ax[1].plot(r[:, 0], -r[:, 1], color=col, lw=1.2)
    for a, w in [(ax[0], PCB_H), (ax[1], PCB_W)]:
        a.add_patch(Rectangle((-w / 2, PCB_Z), w, PCB_T, color="#1b4f9c"))
        a.set_aspect("equal"); a.set_ylim(-1, T + 1)
    ax[0].add_patch(Rectangle((BAT_Y - BAT[1] / 2, FACE + 0.2), BAT[1], BAT[2], color="#999999"))
    ax[1].add_patch(Rectangle((-BAT[0] / 2, FACE + 0.2), BAT[0], BAT[2], color="#999999"))
    ax[0].add_patch(Rectangle((pcb(0, 24.4 + 10.96)[1], SPLIT_Z), 16.6, 2.4, color="#444444"))
    ax[0].set_title("Coupe x = 0 (y horizontal, beliere a droite)")
    ax[1].set_title("Coupe y = 0")
    a = ax[2]
    t = np.linspace(0, 2 * math.pi, 200)
    a.plot(OUT_W / 2 * np.cos(t), OUT_H / 2 * np.sin(t), color="#c9a24a")
    a.plot(CA * np.cos(t), CB * np.sin(t), color="#2e7d5b")
    a.plot(PCB_W / 2 * np.cos(t), PCB_H / 2 * np.sin(t), color="#1b4f9c")
    a.add_patch(Rectangle((-BAT[0] / 2, BAT_Y - BAT[1] / 2), BAT[0], BAT[1], fill=False, color="#999999"))
    for (x, y) in SUPPORTS:
        a.fill(x + 1.1 * np.cos(t), y + 1.1 * np.sin(t), color="#2e7d5b")
    for (x, y) in HOLD:
        a.plot(x, y, "o", color="#c9a24a")
    for (x, y), d in [(BTN, 7), (LED, 2), (CHG[0], 2.4), (CHG[1], 2.4), (MIC, 1.2)]:
        a.plot(x + d / 2 * np.cos(t), y + d / 2 * np.sin(t), color="k", lw=0.8)
    a.set_aspect("equal"); a.set_title("Vue de face : ouvertures, appuis, batterie")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "apercu.png"), dpi=110)


if __name__ == "__main__":
    back, lid, pcbd = back_shell(), front_lid(), pcb_dummy()
    save(back, "galet_coque_arriere.stl")
    save(lid, "galet_face_avant.stl", flip=True)
    save(pcbd, "gabarit_carte.stl")
    save(battery_dummy(), "gabarit_batterie.stl")
    inter = back ^ lid
    print("interference coque/face avant : %.3f mm3" % inter.volume())
    print("interference carte/coque : %.3f mm3, carte/face avant : %.3f mm3" % (
        (pcbd.translate([0, 0, PCB_Z]) ^ back).volume(), (pcbd.translate([0, 0, PCB_Z]) ^ lid).volume()))
    bat = battery_dummy().translate([0, BAT_Y, FACE + 0.2])
    print("interference batterie/coque : %.3f mm3" % (bat ^ back).volume())
    preview(back, lid, pcbd)
