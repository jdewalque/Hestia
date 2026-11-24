"""Rendus realistes du pendentif Galet avec Blender (Cycles).

Lancer :  /Applications/Blender.app/Contents/MacOS/Blender -b -P rendu_blender.py -- [hero|face|eclate|tout] [echantillons]
Sorties : rendus/galet_hero.png, galet_face.png, galet_eclate.png et galet.blend

Cotes en mm (les memes que galet.py et que la planche), 1 unite Blender = 1 cm.
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "rendus")
os.makedirs(OUT, exist_ok=True)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
WHAT = argv[0] if argv else "tout"
SAMPLES = int(argv[1]) if len(argv) > 1 else 220

S = 0.1                      # mm -> unites Blender
N = 192                      # segments par ellipse
A, B, T = 17.5, 22.5, 12.0   # demi-axes exterieurs, epaisseur
R_EDGE, DOME = 4.5, 0.45     # arrondi du bord, bombe des faces
WALL, FACE = 2.0, 1.0
PCB_A, PCB_B, PCB_T, PCB_Z = 14.0, 19.0, 0.8, 7.5
SPLIT_Z = PCB_Z + PCB_T


def pcb(px, py):
    return (px - 14.0, 19.0 - py)


BTN, LED, MIC = pcb(14.0, 14.9), pcb(14.0, 8.5), pcb(21.15, 11.2)
CHG = [pcb(3.6, 15.2), pcb(24.4, 15.2)]


# ------------------------------------------------------------------ geometrie
def edge_inset(d):
    if d >= R_EDGE:
        return 0.0
    return R_EDGE - math.sqrt(R_EDGE ** 2 - (R_EDGE - d) ** 2)


def top_z(x, y):
    """Hauteur de la face avant bombee au point (x, y)."""
    rho2 = min(1.0, (x / (A - R_EDGE)) ** 2 + (y / (B - R_EDGE)) ** 2)
    return T + DOME * (1 - rho2)


def pebble_levels(z0=0.0, z1=T, cap0=True, cap1=True):
    lv = []
    if cap0:
        for k in range(1, 9):
            rho = k / 8
            lv.append((-DOME * (1 - rho * rho), (A - R_EDGE) * rho, (B - R_EDGE) * rho))
    n = max(2, int((z1 - z0) / 0.12))
    for i in range(n + 1):
        z = z0 + (z1 - z0) * i / n
        ins = edge_inset(min(z, T - z))
        lv.append((z, A - ins, B - ins))
    if cap1:
        for k in range(7, 0, -1):
            rho = k / 8
            lv.append((T + DOME * (1 - rho * rho), (A - R_EDGE) * rho, (B - R_EDGE) * rho))
    return lv


def cavity_levels(z0=FACE, z1=T - FACE, r=1.2):
    lv = []
    n = max(2, int((z1 - z0) / 0.12))
    for i in range(n + 1):
        z = z0 + (z1 - z0) * i / n
        d = z - FACE if z1 > T - FACE else min(z - FACE, T - FACE - z)
        ins = 0.0 if d >= r else r - math.sqrt(r * r - (r - d) ** 2)
        lv.append((z, A - WALL - ins, B - WALL - ins))
    return lv


def loft(name, levels, cx=0.0, cy=0.0, smooth=True, n=N):
    """Solide ferme par empilement d'ellipses : levels = [(z, demi-axe x, demi-axe y)]."""
    verts, faces = [], []
    for z, a, b in levels:
        for i in range(n):
            t = 2 * math.pi * i / n
            verts.append(((cx + a * math.cos(t)) * S, (cy + b * math.sin(t)) * S, z * S))
    L = len(levels)
    for k in range(L - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i))
    faces.append(tuple(reversed(range(n))))
    faces.append(tuple((L - 1) * n + i for i in range(n)))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    if smooth:
        for p in me.polygons:
            p.use_smooth = len(p.vertices) == 4
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def box(name, cx, cy, sx, sy, z0, z1, bevel=0.0):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((cx + v.co.x * sx) * S, (cy + v.co.y * sy) * S, ((z0 + z1) / 2 + v.co.z * (z1 - z0)) * S))
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel * S, segments=3, affect="EDGES")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def tube(name, pts, radius, cyclic=False, res=24):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius * S
    cu.bevel_resolution = 6
    cu.resolution_u = res
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, (x, y, z) in zip(sp.points, pts):
        p.co = (x * S, y * S, z * S, 1.0)
    sp.use_cyclic_u = cyclic
    sp.use_endpoint_u = not cyclic
    sp.order_u = 4
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def boolean(ob, cutter, op="DIFFERENCE"):
    m = ob.modifiers.new("b", "BOOLEAN")
    m.operation = op
    m.object = cutter
    m.solver = "EXACT"
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    ob.data = me
    cutter.hide_render = True
    cutter.hide_viewport = True
    return ob


# ------------------------------------------------------------------ matieres
def principled(name, **kw):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    for k, v in kw.items():
        if k in bsdf.inputs:
            bsdf.inputs[k].default_value = v
    return mat, bsdf


def mat_jade(name="jade", light=False):
    base = (0.16, 0.55, 0.38, 1) if light else (0.035, 0.26, 0.16, 1)
    mat, bsdf = principled(name, Roughness=0.06, IOR=1.52,
                           **{"Subsurface Weight": 1.0, "Subsurface Scale": 0.22,
                              "Subsurface Radius": (0.35, 1.0, 0.6), "Coat Weight": 1.0, "Coat Roughness": 0.03,
                              "Transmission Weight": 0.0 if light else 0.1})
    nt = mat.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.1
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.62
    if "Distortion" in noise.inputs:
        noise.inputs["Distortion"].default_value = 2.4
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.36, base
    cr.elements[1].position, cr.elements[1].color = 0.80, (0.42, 0.80, 0.62, 1) if not light else (0.62, 0.9, 0.78, 1)
    e = cr.elements.new(0.52)
    e.color = (base[0] * 1.9, base[1] * 1.5, base[2] * 1.6, 1)
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def mat_gold():
    return principled("or", **{"Base Color": (0.94, 0.70, 0.30, 1), "Metallic": 1.0, "Roughness": 0.3})[0]


def mat_nacre():
    mat, bsdf = principled("nacre", **{"Base Color": (0.93, 0.93, 0.90, 1), "Roughness": 0.18, "Coat Weight": 1.0,
                                        "Coat Roughness": 0.05, "Subsurface Weight": 0.4, "Subsurface Scale": 0.05,
                                        "Sheen Weight": 0.2})
    nt = mat.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.5
    noise.inputs["Detail"].default_value = 4.0
    if "Distortion" in noise.inputs:
        noise.inputs["Distortion"].default_value = 3.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.3, (0.93, 0.86, 0.88, 1)
    cr.elements[1].position, cr.elements[1].color = 0.7, (0.84, 0.93, 0.90, 1)
    e = cr.elements.new(0.5)
    e.color = (0.96, 0.95, 0.90, 1)
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def mat_simple(name, color, rough=0.5, metal=0.0, **kw):
    return principled(name, **{"Base Color": color, "Roughness": rough, "Metallic": metal}, **kw)[0]


def mat_ground():
    mat, bsdf = principled("sol", **{"Base Color": (0.50, 0.47, 0.43, 1), "Roughness": 0.62})
    nt = mat.node_tree
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 18.0
    noise.inputs["Detail"].default_value = 8.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def assign(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return ob


# ------------------------------------------------------------------ pieces
def bail_points(z=6.0):
    """Boucle de la beliere : deux jambes dans la coque, demi-cercle en haut."""
    pts = [(-2.6, 19.5, z), (-2.6, 22.0, z), (-2.6, 25.5, z)]
    for k in range(1, 8):
        a = math.pi - math.pi * k / 8
        pts.append((2.6 * math.cos(a), 26.0 + 2.6 * math.sin(a), z))
    pts += [(2.6, 25.5, z), (2.6, 22.0, z), (2.6, 19.5, z)]
    return pts


def crescent(name, z_off=0.02):
    """Croissant de nacre incruste, en bas a droite de la face avant."""
    th0, th1, n, m = math.radians(-100), math.radians(42), 70, 6
    verts, faces = [], []
    for i in range(n + 1):
        th = th0 + (th1 - th0) * i / n
        ox, oy = 12.7 * math.cos(th), 17.7 * math.sin(th)
        w = 3.4 * math.sin(math.pi * i / n) ** 0.9
        d = math.hypot(ox, oy)
        for j in range(m + 1):
            f = 1 - (w / d) * j / m
            x, y = ox * f, oy * f
            verts.append((x * S, y * S, (top_z(x, y) + z_off) * S))
    for i in range(n):
        for j in range(m):
            p = i * (m + 1) + j
            faces.append((p, p + m + 1, p + m + 2, p + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    sol = ob.modifiers.new("ep", "SOLIDIFY")
    sol.thickness = 0.12 * S
    sol.offset = 1
    return ob


def front_details(parent_objs, mats, dz=0.0):
    """Bouton, contacts de charge, micro, croissant : ce qui se voit sur la face avant."""
    objs = []
    bz = top_z(*BTN)
    btn = loft("bouton", [(bz - 1.0, 4.4, 4.4), (bz + 0.10, 4.4, 4.4), (bz + 0.26, 4.25, 4.25), (bz + 0.36, 3.9, 3.9),
                          (bz + 0.42, 3.2, 3.2), (bz + 0.46, 2.0, 2.0), (bz + 0.47, 0.6, 0.6)], BTN[0], BTN[1], n=96)
    objs.append(assign(btn, mats["jade"]))
    ring = loft("gorge", [(bz - 0.5, 4.75, 4.75), (bz + 0.02, 4.75, 4.75)], BTN[0], BTN[1], n=96)
    objs.append(assign(ring, mats["noir"]))
    for i, (x, y) in enumerate(CHG):
        z = top_z(x, y)
        st = loft("contact%d" % i, [(z - 0.8, 1.1, 1.1), (z + 0.08, 1.1, 1.1), (z + 0.16, 0.95, 0.95), (z + 0.2, 0.5, 0.5)], x, y, n=48)
        objs.append(assign(st, mats["or"]))
    z = top_z(*MIC)
    mic = loft("micro", [(z - 0.3, 0.5, 0.5), (z + 0.015, 0.5, 0.5)], MIC[0], MIC[1], n=32)
    objs.append(assign(mic, mats["noir"]))
    objs.append(assign(crescent("croissant"), mats["nacre"]))
    for o in objs:
        o.location.z += dz * S
    return objs


def build_pendant(mats, with_cord=True):
    body = assign(loft("galet", pebble_levels()), mats["jade"])
    bail = tube("beliere", bail_points(), 0.95)
    bail.data.materials.append(mats["jade"])
    rim = tube("lisere", [((A - 0.05) * math.cos(2 * math.pi * i / 96), (B - 0.05) * math.sin(2 * math.pi * i / 96), 7.6)
                          for i in range(96)], 0.33, cyclic=True, res=6)
    rim.data.materials.append(mats["or"])
    objs = [body, bail, rim] + front_details([body], mats)
    if with_cord:
        cord = tube("cordon", [(-48, 100, 9), (-27, 66, 9), (-10, 41, 8.6), (-1.8, 29.6, 7.6), (0, 26.9, 6.0),
                               (1.8, 29.6, 4.4), (10, 41, 3.4), (27, 66, 3), (48, 100, 3)], 0.75)
        cord.data.materials.append(mats["cuir"])
        objs.append(cord)
    return objs


def build_exploded(mats):
    """Vue eclatee : face avant, carte, batterie, coque arriere avec le ruban d'antenne."""
    gap_lid, gap_pcb, gap_bat, gap_rib = 46.0, 29.0, 15.0, 8.0
    # coque arriere
    back = loft("coque", pebble_levels(0, SPLIT_Z, True, False))
    back = boolean(back, loft("cav", cavity_levels(FACE, T), smooth=False))
    assign(back, mats["jade"])
    es = back.modifiers.new("es", "EDGE_SPLIT")
    es.split_angle = math.radians(40)
    for x, y in [pcb(7.7, 3.76), pcb(20.3, 3.76), pcb(7.7, 34.24), pcb(20.3, 34.24)]:
        assign(loft("plot", [(FACE - 0.1, 1.1, 1.1), (PCB_Z, 1.1, 1.1)], x, y, n=32), mats["jade"])
    bail = tube("beliere", bail_points(), 0.95)
    bail.data.materials.append(mats["jade"])
    # ruban d'antenne LTE sur la paroi interieure : du haut a droite au milieu du flanc gauche
    a, b = A - WALL - 0.12, B - WALL - 0.12
    t0 = math.acos(5.0 / a)
    t1 = math.atan2(1.26 / b, -15.27 / a) - 2 * math.pi
    verts, faces, n = [], [], 160
    for i in range(n + 1):
        t = t0 + (t1 - t0) * i / n
        for z in (2.4, 6.4):
            verts.append((a * math.cos(t) * S, b * math.sin(t) * S, (z + gap_rib) * S))
    for i in range(n):
        faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    me = bpy.data.meshes.new("ruban")
    me.from_pydata(verts, [], faces)
    rib = bpy.data.objects.new("ruban", me)
    bpy.context.scene.collection.objects.link(rib)
    sol = rib.modifiers.new("ep", "SOLIDIFY")
    sol.thickness = 0.15 * S
    assign(rib, mats["cuivre"])
    # batterie
    bat = assign(box("batterie", 0, 1.5, 20, 25, FACE + 0.2 + gap_bat, FACE + 5.2 + gap_bat, bevel=0.8), mats["batterie"])
    assign(box("etiquette", 0, 1.5, 14, 19, FACE + 5.2 + gap_bat, FACE + 5.23 + gap_bat), mats["jaune"])
    # carte
    z = PCB_Z + gap_pcb
    assign(loft("carte", [(z, PCB_A, PCB_B), (z + PCB_T, PCB_A, PCB_B)], smooth=False), mats["carte"])
    mx, my = pcb(14.0, 24.4 + 2.66)
    assign(box("module", mx, my + 2.7, 13.2, 11.2, z + PCB_T, z + PCB_T + 2.4, bevel=0.25), mats["blindage"])
    assign(box("module_ant", mx, my - 5.6, 13.2, 5.4, z + PCB_T, z + PCB_T + 0.8), mats["noir"])
    assign(box("sw", BTN[0], BTN[1], 6.2, 6.2, z + PCB_T, z + PCB_T + 2.5, bevel=0.3), mats["blindage"])
    assign(loft("poussoir", [(z + PCB_T + 2.5, 1.5, 1.5), (z + PCB_T + 3.4, 1.5, 1.5)], BTN[0], BTN[1], n=32), mats["noir"])
    assign(box("led", LED[0], LED[1], 2.0, 1.25, z + PCB_T, z + PCB_T + 0.7), mats["blanc"])
    for x, y in CHG:
        assign(loft("pastille", [(z + PCB_T, 1.0, 1.0), (z + PCB_T + 0.05, 1.0, 1.0)], x, y, n=32), mats["or"])
    assign(box("nrf", -2.25, 3.95, 12.1, 11.1, z - 1.05, z, bevel=0.15), mats["noir"])
    # face avant
    lid = loft("face", pebble_levels(SPLIT_Z, T, False, True))
    lid = boolean(lid, loft("cav2", cavity_levels(FACE, T - FACE), smooth=False))
    assign(lid, mats["jade"])
    es = lid.modifiers.new("es", "EDGE_SPLIT")
    es.split_angle = math.radians(40)
    lid.location.z += gap_lid * S
    rim = tube("lisere", [((A - 0.05) * math.cos(2 * math.pi * i / 96), (B - 0.05) * math.sin(2 * math.pi * i / 96), SPLIT_Z + 0.5 + gap_lid)
                          for i in range(96)], 0.33, cyclic=True, res=6)
    rim.data.materials.append(mats["or"])
    front_details([lid], mats, dz=gap_lid)


# ------------------------------------------------------------------ scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as e:
        print("GPU indisponible, rendu CPU :", e)
    sc.render.resolution_x, sc.render.resolution_y = 1800, 1350
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.look = "AgX - Medium High Contrast" if hasattr(sc.view_settings, "look") else sc.view_settings.look
    return sc


def world(sc, hdri="studio.exr", strength=0.9, rot=0.0):
    w = bpy.data.worlds.new("monde")
    w.use_nodes = True
    sc.world = w
    nt = w.node_tree
    bg = nt.nodes["Background"]
    bg.inputs["Strength"].default_value = strength
    res = os.path.join(os.path.dirname(bpy.app.binary_path), "..", "Resources")
    path = None
    for root, _, files in os.walk(res):
        if hdri in files and "world" in root:
            path = os.path.join(root, hdri)
            break
    if path:
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(path)
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (0, 0, rot)
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])


def area(name, loc, size, power, target=(0, 0, 0.6), color=(1, 1, 1), size_y=None):
    li = bpy.data.lights.new(name, "AREA")
    li.size = size
    if size_y:
        li.shape = "RECTANGLE"
        li.size_y = size_y
    li.energy = power
    li.color = color
    ob = bpy.data.objects.new(name, li)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def camera(sc, loc, target, lens=85, fstop=None, ortho=None):
    cam = bpy.data.cameras.new("cam")
    cam.lens = lens
    cam.clip_start = 0.01
    ob = bpy.data.objects.new("cam", cam)
    sc.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if ortho:
        cam.type = "ORTHO"
        cam.ortho_scale = ortho
    if fstop:
        cam.dof.use_dof = True
        cam.dof.focus_distance = (Vector(target) - Vector(loc)).length
        cam.dof.aperture_fstop = fstop
    sc.camera = ob
    return ob


def ground(mats, z=0.0, size=60):
    me = bpy.data.meshes.new("sol")
    me.from_pydata([(-size, -size, z), (size, -size, z), (size, size, z), (-size, size, z)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("sol", me)
    bpy.context.scene.collection.objects.link(ob)
    return assign(ob, mats["sol"])


def materials():
    return {
        "jade": mat_jade(), "jade_clair": mat_jade("jade_clair", light=True), "or": mat_gold(), "nacre": mat_nacre(),
        "sol": mat_ground(),
        "noir": mat_simple("noir", (0.012, 0.014, 0.013, 1), 0.45),
        "cuir": mat_simple("cuir", (0.09, 0.045, 0.025, 1), 0.7),
        "cuivre": mat_simple("cuivre", (0.95, 0.52, 0.30, 1), 0.28, 1.0),
        "carte": mat_simple("carte", (0.012, 0.014, 0.02, 1), 0.3, **{"Coat Weight": 0.6}),
        "blindage": mat_simple("blindage", (0.78, 0.78, 0.76, 1), 0.32, 1.0),
        "batterie": mat_simple("batterie", (0.72, 0.73, 0.75, 1), 0.38, 1.0),
        "jaune": mat_simple("jaune", (0.85, 0.62, 0.10, 1), 0.5),
        "blanc": mat_simple("blanc", (0.9, 0.9, 0.85, 1), 0.4),
        "argent": mat_simple("argent", (0.62, 0.62, 0.60, 1), 0.5, 0.7),
        "laiton": mat_simple("laiton", (0.72, 0.52, 0.20, 1), 0.5, 0.7),
    }


def render(sc, name):
    sc.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print("rendu ecrit :", sc.render.filepath)


def scene_hero():
    sc = reset()
    mats = materials()
    world(sc, "studio.exr", 0.45, rot=3.4)
    objs = build_pendant(mats)
    pivot = bpy.data.objects.new("pivot", None)
    sc.collection.objects.link(pivot)
    for o in objs:
        o.parent = pivot
    pivot.rotation_euler = (math.radians(90), 0, math.radians(-14))     # debout, face vers la camera, leger trois quarts
    # fond
    me = bpy.data.meshes.new("fond")
    me.from_pydata([(-80, 4.5, -60), (80, 4.5, -60), (80, 4.5, 60), (-80, 4.5, 60)], [], [(0, 1, 2, 3)])
    fond = bpy.data.objects.new("fond", me)
    sc.collection.objects.link(fond)
    assign(fond, mat_simple("fond", (0.022, 0.028, 0.034, 1), 0.85))
    area("cle", (-11.0, -7.0, 4.0), 1.4, 650, (0, 0, 0.3), (1.0, 0.96, 0.9), size_y=9.0)
    area("contre", (8.0, -4.0, -2.0), 4.0, 260, (0, 0, 0.3), (0.85, 0.93, 1.0))
    area("liseré", (5.0, 3.0, 6.0), 3.0, 500, (0, 0, 1.0))
    sc.render.resolution_x, sc.render.resolution_y = 1500, 1900
    camera(sc, (2.0, -25.0, 1.4), (0.0, 0.0, 0.95), lens=100, fstop=11)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "galet.blend"))
    render(sc, "galet_hero.png")


def scene_face():
    sc = reset()
    mats = materials()
    world(sc, "studio.exr", 1.3, rot=0.4)
    ground(mats)
    for o in build_pendant(mats, with_cord=False):
        o.location.x -= 1.9
    # piece de 2 euros : 25,75 mm de diametre, 2,2 mm d'epaisseur
    assign(loft("piece_ext", [(0, 12.5, 12.5), (0.25, 12.875, 12.875), (1.95, 12.875, 12.875), (2.2, 12.5, 12.5)], 26.0, -6.0, n=128), mats["argent"])
    assign(loft("piece_int", [(2.0, 9.2, 9.2), (2.24, 9.2, 9.2)], 26.0, -6.0, n=128), mats["laiton"])
    area("cle", (-14.0, 9.0, 6.0), 4.0, 1500, (0, 0, 0.6), (1.0, 0.97, 0.92))
    area("rasant", (13.0, -10.0, 5.0), 4.0, 700, (0.5, 0, 0.6))
    camera(sc, (0.5, -1.4, 24.0), (0.5, 0.3, 0.0), lens=85)
    render(sc, "galet_face.png")


def scene_exploded():
    sc = reset()
    mats = materials()
    world(sc, "studio.exr", 0.8, rot=2.2)
    ground(mats)
    build_exploded(mats)
    area("cle", (-5.5, -5.0, 9.0), 5.0, 520, (0, 0, 2.2), (1.0, 0.97, 0.92))
    area("contre", (6.5, 2.0, 5.0), 4.0, 260, (0, 0, 2.0), (0.9, 0.95, 1.0))
    sc.render.resolution_x, sc.render.resolution_y = 1350, 1800
    camera(sc, (12.0, -17.0, 14.5), (0.0, 0.35, 3.05), lens=78)
    render(sc, "galet_eclate.png")


if WHAT in ("hero", "tout"):
    scene_hero()
if WHAT in ("face", "tout"):
    scene_face()
if WHAT in ("eclate", "tout"):
    scene_exploded()
