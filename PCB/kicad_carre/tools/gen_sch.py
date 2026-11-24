"""Generate alert_button.kicad_sym (project symbols) and alert_button.kicad_sch.

Connectivity is by net label: every connected pin gets a short wire stub and a
label carrying the net name.
"""
import copy
import os
import uuid

from sexpr import Sym, parse, dump, find, first
import design

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = design.OUT_DIR
KSYM = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/"
PROJECT = design.PROJECT
SYMLIB = design.SYMLIB
S = Sym


def uid():
    return str(uuid.uuid4())


def font(size=1.27):
    return [S("font"), [S("size"), size, size]]


def effects(size=1.27, justify=None, hide=False):
    e = [S("effects"), font(size)]
    if justify:
        e.append([S("justify")] + [S(j) for j in justify])
    if hide:
        e.append([S("hide"), S("yes")])
    return e


# ------------------------------------------------------------------ project symbols
def prop(name, value, x, y, hide=False):
    return [S("property"), name, value, [S("at"), x, y, 0], effects(hide=hide)]


def pin(etype, x, y, angle, name, number, hide=False, length=2.54):
    p = [S("pin"), S(etype), S("line"), [S("at"), x, y, angle], [S("length"), length]]
    if hide:
        p.append([S("hide"), S("yes")])
    p += [[S("name"), name, effects()], [S("number"), number, effects()]]
    return p


def make_symbol(name, ref, footprint, datasheet, descr, half_w, top, bottom, pins):
    body = [S("symbol"), name + "_0_1",
            [S("rectangle"), [S("start"), -half_w, top], [S("end"), half_w, bottom],
             [S("stroke"), [S("width"), 0.254], [S("type"), S("default")]],
             [S("fill"), [S("type"), S("background")]]]]
    return [S("symbol"), name,
            [S("exclude_from_sim"), S("no")], [S("in_bom"), S("yes")], [S("on_board"), S("yes")],
            prop("Reference", ref, -half_w, top + 1.27),
            prop("Value", name, half_w - 10, top + 1.27),
            prop("Footprint", footprint, 0, 0, hide=True),
            prop("Datasheet", datasheet, 0, 0, hide=True),
            prop("Description", descr, 0, 0, hide=True),
            body,
            [S("symbol"), name + "_1_1"] + pins]


def nrf9151_symbol():
    hw = 22.86
    left = [("VDD", "14", "power_in"), ("ENABLE", "10", "input"),
            ("VDD_GPIO", "65", "power_in"), ("DEC0", "24", "passive"), None,
            ("nRESET", "9", "input"), ("SWDCLK", "3", "input"),
            ("SWDIO", "4", "bidirectional"), None,
            ("SIM_1V8", "19", "power_out"), ("SIM_RST", "16", "output"),
            ("SIM_CLK", "18", "output"), ("SIM_IO", "17", "bidirectional"),
            ("SIM_DET", "26", "passive"), None,
            ("ANT", "35", "passive"), ("AUX", "37", "passive"), ("GPS", "42", "passive"), None,
            ("MAGPIO0", "21", "bidirectional"), ("MAGPIO1", "22", "bidirectional"),
            ("MAGPIO2", "23", "bidirectional"), ("SCLK", "28", "output"),
            ("SDATA", "27", "bidirectional"), ("VIO", "29", "passive"),
            ("COEX0", "52", "bidirectional"), ("COEX1", "53", "bidirectional"),
            ("COEX2", "54", "bidirectional")]
    gpio_pins = [56, 57, 58, 59, 61, 62, 63, 64, 67, 68, 69, 70, 72, 73, 74, 75,
                 77, 78, 79, 80, 2, 5, 6, 8, 11, 12, 44, 45, 47, 48, 49, 50]
    top = 16 * 2.54 + 2.54
    pins = []
    y = top - 2.54
    for item in left:
        if item:
            pins.append(pin(item[2], -hw - 2.54, round(y, 2), 0, item[0], item[1]))
        y -= 2.54
    y = top - 2.54
    for i, num in enumerate(gpio_pins):
        pins.append(pin("bidirectional", hw + 2.54, round(y, 2), 180, "P0.%02d" % i, str(num)))
        y -= 2.54
    bottom = round(y - 0.0, 2)
    gnd = [1, 7, 13, 15, 20, 25, 30, 34, 36, 38, 39, 40, 41, 43, 46, 51, 55, 60, 66, 71, 76] \
        + list(range(105, 114))
    for i, num in enumerate(gnd):
        pins.append(pin("power_in" if i == 0 else "passive", 0, bottom - 2.54, 90,
                        "GND", str(num), hide=(i > 0)))
    for num in [31, 32, 33] + list(range(81, 105)):
        pins.append(pin("no_connect", 5.08, bottom - 2.54, 90, "RESERVED", str(num), hide=True))
    return make_symbol(
        "nRF9151-LACA", "U",
        "Package_LGA:Nordic_nRF9151-LAxx_LGA-80-33EP_12.1x11.1mm_P0.5mm",
        "https://docs.nordicsemi.com/bundle/ps_nrf9151/page/pin.html",
        "LTE-M / NB-IoT / GNSS SiP with Cortex-M33, LGA 12.1x11.1mm",
        hw, top, bottom, pins)


def esim_symbol():
    hw = 7.62
    pins = [pin("power_in", -hw - 2.54, 3.81, 0, "VCC", "8"),
            pin("input", -hw - 2.54, 1.27, 0, "RST", "7"),
            pin("input", -hw - 2.54, -1.27, 0, "CLK", "6"),
            pin("bidirectional", -hw - 2.54, -3.81, 0, "I/O", "3"),
            pin("power_in", 0, -8.89, 90, "GND", "1")]
    for num in ["2", "4", "5", "9"]:
        pins.append(pin("no_connect", 5.08, -8.89, 90, "NC", num, hide=True))
    return make_symbol(
        "eSIM_MFF2", "U", "Package_DFN_QFN:DFN-8-1EP_6x5mm_P1.27mm_EP2x2mm", "~",
        "Solderable SIM, MFF2 (ETSI TS 102 671), VQFN-8 6x5mm",
        hw, 6.35, -6.35, pins)


def write_project_lib():
    lib = [S("kicad_symbol_lib"), [S("version"), 20241209], [S("generator"), "alert_button_gen"],
           [S("generator_version"), "9.0"], nrf9151_symbol(), esim_symbol()]
    path = os.path.join(OUT, SYMLIB + ".kicad_sym")
    with open(path, "w") as f:
        f.write(dump(lib) + "\n")
    return path


# ------------------------------------------------------------------ library access
_libs = {}


def load_lib(name):
    if name not in _libs:
        path = os.path.join(OUT, name + ".kicad_sym") if name == SYMLIB else KSYM + name + ".kicad_sym"
        _libs[name] = parse(open(path).read())
    return _libs[name]


def get_symbol(lib_id):
    """Return a flattened copy of the library symbol, named with its lib_id."""
    libname, name = lib_id.split(":")
    lib = load_lib(libname)
    syms = {s[1]: s for s in find(lib, "symbol")}
    sym = copy.deepcopy(syms[name])
    ext = first(sym, "extends")
    if ext:
        parent = copy.deepcopy(syms[ext[1]])
        child_props = {p[1]: p for p in find(sym, "property")}
        merged = []
        for e in parent[2:]:
            if isinstance(e, list) and e[0] == "property":
                if e[1] in child_props:
                    merged.append(child_props.pop(e[1]))
                else:
                    merged.append(e)
            elif isinstance(e, list) and e[0] == "symbol":
                e[1] = name + e[1][len(ext[1]):]
                merged.append(e)
            else:
                merged.append(e)
        # child-only properties go before the first unit symbol
        idx = next((i for i, e in enumerate(merged) if isinstance(e, list) and e[0] == "symbol"), len(merged))
        merged[idx:idx] = list(child_props.values())
        sym = [S("symbol"), name] + merged
    sym[1] = lib_id
    return sym


def symbol_pins(sym):
    out = []
    for unit in find(sym, "symbol"):
        for p in find(unit, "pin"):
            at = first(p, "at")
            out.append(dict(type=str(p[1]), x=float(at[1]), y=float(at[2]), a=int(float(at[3])),
                            name=first(p, "name")[1], num=first(p, "number")[1]))
    return out


# ------------------------------------------------------------------ schematic
OUTWARD = {0: (-1, 0, 180), 180: (1, 0, 0), 90: (0, 1, 270), 270: (0, -1, 90)}
JUST = {0: ("left", "bottom"), 90: ("left", "bottom"), 180: ("right", "bottom"), 270: ("right", "bottom")}
STUB = 2.54


def r2(v):
    return round(v + 0.0, 2)


def build():
    write_project_lib()
    root_uuid = uid()
    lib_symbols = [S("lib_symbols")]
    seen = {}
    items = []
    stubs_done = set()

    for p in design.PARTS:
        if p["lib"] not in seen:
            seen[p["lib"]] = get_symbol(p["lib"])
            lib_symbols.append(seen[p["lib"]])
        sym = seen[p["lib"]]
        pins = symbol_pins(sym)
        X, Y = p["sch"]
        conn = p["conn"]
        ys = [pp["y"] for pp in pins] or [0]
        xs = [pp["x"] for pp in pins] or [0]
        is_power = p["ref"].startswith("#")
        no_bom = is_power or p["ref"].startswith("TP")
        two_pin_vertical = len(pins) <= 2 and max(xs) - min(xs) < 0.1

        if two_pin_vertical or len(pins) == 1:
            ref_at, val_at, just = (X + 2.54, Y - 1.27), (X + 2.54, Y + 1.27), ("left",)
        elif len(pins) <= 4 and max(ys) - min(ys) < 11:
            ref_at, val_at, just = (X, Y - max(ys) - 5.08), (X, Y - min(ys) + 5.08), None
        else:
            ref_at, val_at, just = (X, Y - max(ys) - 3.81), (X, Y - min(ys) + 3.81), None

        inst = [S("symbol"), [S("lib_id"), p["lib"]], [S("at"), X, Y, 0], [S("unit"), 1],
                [S("exclude_from_sim"), S("no")],
                [S("in_bom"), S("no" if no_bom else "yes")],
                [S("on_board"), S("no" if is_power else "yes")],
                [S("dnp"), S("yes" if p["dnp"] else "no")], [S("uuid"), uid()],
                [S("property"), "Reference", p["ref"], [S("at"), r2(ref_at[0]), r2(ref_at[1]), 0],
                 effects(justify=just, hide=is_power)],
                [S("property"), "Value", p["value"], [S("at"), r2(val_at[0]), r2(val_at[1]), 0],
                 effects(justify=just, hide=is_power)],
                [S("property"), "Footprint", p["fp"], [S("at"), X, Y, 0], effects(hide=True)],
                [S("property"), "Datasheet", "~", [S("at"), X, Y, 0], effects(hide=True)]]
        if p["mpn"]:
            inst.append([S("property"), "MPN", p["mpn"], [S("at"), X, Y, 0], effects(hide=True)])
        for pp in pins:
            inst.append([S("pin"), pp["num"], [S("uuid"), uid()]])
        inst.append([S("instances"), [S("project"), PROJECT,
                     [S("path"), "/" + root_uuid, [S("reference"), p["ref"]], [S("unit"), 1]]]])
        items.append(inst)

        used = set()
        for pp in pins:
            net = None
            if pp["num"] in conn:
                net = conn[pp["num"]]; used.add(pp["num"])
            elif pp["name"] in conn:
                net = conn[pp["name"]]; used.add(pp["name"])
            px, py = r2(X + pp["x"]), r2(Y - pp["y"])
            if net is None:
                if pp["type"] != "no_connect" and (px, py) not in stubs_done:
                    stubs_done.add((px, py))
                    items.append([S("no_connect"), [S("at"), px, py], [S("uuid"), uid()]])
                continue
            if (px, py) in stubs_done:
                continue
            stubs_done.add((px, py))
            dx, dy, ang = OUTWARD[pp["a"]]
            ex, ey = r2(px + dx * STUB), r2(py + dy * STUB)
            items.append([S("wire"), [S("pts"), [S("xy"), px, py], [S("xy"), ex, ey]],
                          [S("stroke"), [S("width"), 0], [S("type"), S("default")]],
                          [S("uuid"), uid()]])
            items.append([S("label"), net, [S("at"), ex, ey, ang],
                          effects(justify=JUST[ang]), [S("uuid"), uid()]])
        missing = set(conn) - used
        if missing:
            raise SystemExit("%s: unknown pins %s" % (p["ref"], sorted(missing)))

    for text, x, y in design.TITLES:
        items.append([S("text"), text, [S("exclude_from_sim"), S("no")], [S("at"), x, y, 0],
                      effects(size=2.5, justify=("left", "bottom")), [S("uuid"), uid()]])
    for text, x, y in design.NOTES:
        items.append([S("text"), text.replace("\n", "\\n"), [S("exclude_from_sim"), S("no")],
                      [S("at"), x, y, 0], effects(justify=("left", "top")), [S("uuid"), uid()]])

    sch = [S("kicad_sch"), [S("version"), 20250114], [S("generator"), "alert_button_gen"],
           [S("generator_version"), "9.0"], [S("uuid"), root_uuid], [S("paper"), "A3"],
           [S("title_block"), [S("title"), "Bouton d'alerte LTE-M"], [S("rev"), "A"],
            [S("comment"), 1, "nRF9151 + ESP32-C6, coque resine, antenne LTE dans la coque"],
            [S("comment"), 2, "Carte : " + ("ovale 28 x 38 mm" if design.VARIANT == "oval" else "rectangle 25 x 35 mm")]],
           lib_symbols] + items + [
           [S("sheet_instances"), [S("path"), "/", [S("page"), "1"]]],
           [S("embedded_fonts"), S("no")]]
    with open(os.path.join(OUT, PROJECT + ".kicad_sch"), "w") as f:
        f.write(dump(sch) + "\n")

    with open(os.path.join(OUT, "sym-lib-table"), "w") as f:
        f.write('(sym_lib_table\n\t(version 7)\n\t(lib (name "%s")(type "KiCad")'
                '(uri "${KIPRJMOD}/%s.kicad_sym")(options "")(descr "Project symbols"))\n)\n'
                % (SYMLIB, SYMLIB))
    print("schematic written:", len(design.PARTS), "parts")


if __name__ == "__main__":
    build()
