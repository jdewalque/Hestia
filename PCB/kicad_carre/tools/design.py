"""Single source of truth for the alert-button design: parts, nets, placement.

Each part: ref, lib_id, value, footprint, conn (pin number or pin name -> net),
schematic position (mm), PCB placement (x, y, rotation deg, side 'F'/'B').
PCB origin = top-left corner of the board's bounding box.

Two board variants share the same schematic (environment variable PCB_VARIANT):
  rect (default) : 25 x 35 mm rectangle, project kicad/alert_button
  oval           : 28 x 38 mm ellipse,   project kicad_oval/alert_button_oval
"""
import os

VARIANT = os.environ.get("PCB_VARIANT", "rect")
if VARIANT not in ("rect", "oval"):
    raise SystemExit("PCB_VARIANT must be rect or oval")
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYMLIB = "alert_button"      # project symbol library name (same in both variants)
if VARIANT == "rect":
    PROJECT, OUT_DIR, SHAPE = "alert_button", os.path.join(_ROOT, "kicad"), "rect"
else:
    PROJECT, OUT_DIR, SHAPE = "alert_button_oval", os.path.join(_ROOT, "kicad_oval"), "ellipse"

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
TP10 = "TestPoint:TestPoint_Pad_D1.0mm"

BOARD_W, BOARD_H = 25.0, 35.0
LTE_KEEPOUT_H = 5.0          # top strip without copper pour (LTE antenna side)
WIFI_KEEPOUT_Y = 29.6        # ESP32 antenna zone starts here (keep-out comes with the footprint)

PARTS = []


def part(ref, lib, value, fp, conn, sch, pcb, mpn="", dnp=False):
    PARTS.append(dict(ref=ref, lib=lib, value=value, fp=fp, conn=conn,
                      sch=sch, pcb=pcb, mpn=mpn, dnp=dnp))


def G(n):
    return round(n * 2.54, 2)


# ---------------------------------------------------------------- power / charge
part("TP1", "Connector:TestPoint", "CHG_5V", "TestPoint:TestPoint_Pad_D2.0mm",
     {"1": "VCHG"}, (G(10), G(14)), (3.0, 8.0, 0, "F"))
part("TP2", "Connector:TestPoint", "CHG_GND", "TestPoint:TestPoint_Pad_D2.0mm",
     {"1": "GND"}, (G(14), G(14)), (3.0, 12.0, 0, "F"))
part("D3", "Diode:PESD5V0S1UL", "PESD5V0S1UL", "Diode_SMD:D_SOD-882",
     {"1": "VCHG", "2": "GND"}, (G(22), G(12)), (5.4, 8.0, 0, "F"), mpn="PESD5V0S1UL")
part("D2", "Diode:PMEG2005EJ", "PMEG2005EJ", "Diode_SMD:D_SOD-323F",
     {"1": "VBUS", "2": "VCHG"}, (G(22), G(18)), (4.2, 15.0, 0, "F"), mpn="PMEG2005EJ")
part("U4", "Battery_Management:MCP73832-2-OT", "MCP73832T-2ACI/OT",
     "Package_TO_SOT_SMD:SOT-23-5",
     {"1": "CHG_STAT", "2": "GND", "3": "VBAT", "4": "VBUS", "5": "PROG"},
     (G(38), G(14)), (4.0, 22.4, 0, "B"), mpn="MCP73832T-2ACI/OT")
part("R1", "Device:R", "10k 1%", R0402, {"1": "PROG", "2": "GND"},
     (G(30), G(26)), (1.5, 25.0, 0, "B"))
part("C6", "Device:C", "4.7u 10V", C0603, {"1": "VBUS", "2": "GND"},
     (G(35), G(26)), (4.0, 25.2, 0, "B"))
part("C7", "Device:C", "4.7u 10V", C0603, {"1": "VBAT", "2": "GND"},
     (G(40), G(26)), (7.2, 22.4, 90, "B"))
part("R3", "Device:R", "100k", R0402, {"1": "3V3", "2": "CHG_STAT"},
     (G(45), G(26)), (1.5, 19.8, 0, "B"))
part("TP3", "Connector:TestPoint", "BAT+", "TestPoint:TestPoint_Pad_2.0x2.0mm",
     {"1": "VBAT"}, (G(50), G(14)), (2.0, 27.6, 0, "B"))
part("TP4", "Connector:TestPoint", "BAT-", "TestPoint:TestPoint_Pad_2.0x2.0mm",
     {"1": "GND"}, (G(54), G(14)), (5.0, 27.6, 0, "B"))

part("U3", "Regulator_Switching:TPS63900", "TPS63900DSKR",
     "Package_SON:WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm",
     {"1": "VBAT", "2": "VBAT", "3": "CFG1", "4": "GND", "5": "GND", "6": "3V3",
      "7": "LX2", "8": "GND", "9": "LX1", "10": "VBAT", "11": "GND"},
     (G(72), G(16)), (20.5, 22.0, 0, "B"), mpn="TPS63900DSKR")
part("L1", "Device:L", "2.2u", "Inductor_SMD:L_Murata_DFE201610P",
     {"1": "LX1", "2": "LX2"}, (G(62), G(30)), (17.2, 22.0, 90, "B"),
     mpn="DFE201612E-2R2M=P2")
part("C3", "Device:C", "10u 6.3V", C0603, {"1": "VBAT", "2": "GND"},
     (G(67), G(30)), (20.5, 19.2, 0, "B"))
part("C4", "Device:C", "22u 6.3V", C0805, {"1": "3V3", "2": "GND"},
     (G(72), G(30)), (20.5, 25.0, 0, "B"))
part("R2", "Device:R", "36.5k 1%", R0402, {"1": "CFG1", "2": "GND"},
     (G(77), G(30)), (23.3, 22.0, 90, "B"))

# ---------------------------------------------------------------- nRF9151
NRF = {
    "14": "VBAT", "10": "VBAT", "65": "3V3", "24": "DEC0",
    "9": "NRESET", "3": "SWDCLK", "4": "SWDIO",
    "19": "SIM_1V8", "16": "SIM_RST", "18": "SIM_CLK", "17": "SIM_IO",
    "35": "RF_LTE", "GND": "GND",
    "56": "ESP_RXD",   # P0.00  nRF UART TX  -> ESP32 IO6 (RX)
    "57": "ESP_TXD",   # P0.01  nRF UART RX  <- ESP32 IO7 (TX)
    "58": "ESP_CTS",   # P0.02  nRF RTS      -> ESP32 IO5 (CTS)
    "59": "ESP_RTS",   # P0.03  nRF CTS      <- ESP32 IO4 (RTS)
    "61": "ESP_EN",    # P0.04
    "62": "MIC_PWR",   # P0.05
    "63": "PDM_CLK",   # P0.06
    "64": "PDM_DATA",  # P0.07
    "67": "BTN",       # P0.08
    "69": "LED_R",     # P0.10
    "70": "LED_G",     # P0.11
    "72": "LED_B",     # P0.12
    "73": "CHG_STAT",  # P0.13
    "45": "DBG_TX",    # P0.27
    "47": "DBG_RX",    # P0.28
}
part("U1", "alert_button:nRF9151-LACA", "nRF9151-LACA",
     "Package_LGA:Nordic_nRF9151-LAxx_LGA-80-33EP_12.1x11.1mm_P0.5mm",
     NRF, (G(40), G(68)), (12.5, 12.6, 0, "B"), mpn="nRF9151-LACA-R7")
part("C1", "Device:C", "47u 6.3V", C0805, {"1": "VBAT", "2": "GND"},
     (G(8), G(44)), (21.5, 8.0, 90, "B"), mpn="GRM21BR60J476ME15")
part("C2", "Device:C", "47u 6.3V", C0805, {"1": "VBAT", "2": "GND"},
     (G(13), G(44)), (23.4, 8.0, 90, "B"), mpn="GRM21BR60J476ME15")
part("C8", "Device:C", "100n", C0402, {"1": "VBAT", "2": "GND"},
     (G(18), G(44)), (21.0, 11.0, 0, "B"))
part("C9", "Device:C", "100n", C0402, {"1": "3V3", "2": "GND"},
     (G(8), G(54)), (21.0, 12.4, 0, "B"))
part("C15", "Device:C", "100n", C0402, {"1": "DEC0", "2": "GND"},
     (G(13), G(54)), (21.0, 13.8, 0, "B"), dnp=True)

part("U5", "alert_button:eSIM_MFF2", "eSIM MFF2",
     "Package_DFN_QFN:DFN-8-1EP_6x5mm_P1.27mm_EP2x2mm",
     {"8": "SIM_1V8", "7": "SIM_RST", "6": "SIM_CLK", "3": "SIM_IO", "1": "GND"},
     (G(16), G(74)), (12.0, 23.0, 0, "B"))
part("C12", "Device:C", "100n", C0402, {"1": "SIM_1V8", "2": "GND"},
     (G(8), G(64)), (12.0, 19.6, 0, "B"))

# LTE antenna feed: matching network pads, optional U.FL, feed pad for the
# in-shell antenna and a ground pad next to it.
part("Z1", "Device:R", "DNP", R0402, {"1": "RF_LTE", "2": "GND"},
     (G(8), G(92)), (3.4, 9.0, 0, "B"), dnp=True)
part("Z2", "Device:R", "0R", R0402, {"1": "RF_LTE", "2": "RF_M1"},
     (G(13), G(92)), (4.6, 7.6, 90, "B"))
part("Z3", "Device:R", "DNP", R0402, {"1": "RF_M1", "2": "GND"},
     (G(18), G(92)), (3.4, 6.3, 0, "B"), dnp=True)
part("Z4", "Device:R", "0R", R0402, {"1": "RF_M1", "2": "RF_ANT"},
     (G(23), G(92)), (6.0, 6.3, 0, "B"))
part("Z5", "Device:R", "DNP", R0402, {"1": "RF_ANT", "2": "GND"},
     (G(28), G(92)), (8.6, 6.6, 90, "B"), dnp=True)
part("J1", "Connector:Conn_Coaxial", "U.FL",
     "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical",
     {"1": "RF_ANT", "2": "GND"}, (G(10), G(104)), (11.6, 6.3, 180, "B"),
     mpn="U.FL-R-SMT-1(10)", dnp=True)
part("TP5", "Connector:TestPoint", "ANT_FEED", "TestPoint:TestPoint_Pad_1.5x1.5mm",
     {"1": "RF_ANT"}, (G(18), G(104)), (7.4, 3.6, 0, "B"))
part("TP6", "Connector:TestPoint", "ANT_GND", "TestPoint:TestPoint_Pad_1.5x1.5mm",
     {"1": "GND"}, (G(22), G(104)), (3.0, 3.6, 0, "B"))

# ---------------------------------------------------------------- ESP32-C6
part("U2", "RF_Module:ESP32-C6-MINI-1", "ESP32-C6-MINI-1-N4",
     "RF_Module:ESP32-C6-MINI-1",
     {"3": "3V3", "GND": "GND", "8": "ESP_EN",
      "15": "ESP_RXD", "16": "ESP_TXD", "10": "ESP_CTS", "9": "ESP_RTS",
      "22": "ESP_IO8", "23": "ESP_BOOT", "30": "ESP_RX0", "31": "ESP_TX0"},
     (G(112), G(26)), (12.5, 26.7, 180, "F"), mpn="ESP32-C6-MINI-1-N4")
part("R4", "Device:R", "10k", R0402, {"1": "ESP_EN", "2": "GND"},
     (G(94), G(44)), (22.0, 17.0, 0, "F"))
part("C13", "Device:C", "100n", C0402, {"1": "ESP_EN", "2": "GND"},
     (G(99), G(44)), (22.0, 15.6, 0, "F"))
part("R5", "Device:R", "10k", R0402, {"1": "3V3", "2": "ESP_IO8"},
     (G(104), G(44)), (3.0, 17.0, 0, "F"))
part("R6", "Device:R", "10k", R0402, {"1": "3V3", "2": "ESP_BOOT"},
     (G(109), G(44)), (5.5, 17.0, 0, "F"))
part("C5", "Device:C", "10u 6.3V", C0603, {"1": "3V3", "2": "GND"},
     (G(114), G(44)), (21.6, 20.0, 90, "F"))
part("C10", "Device:C", "100n", C0402, {"1": "3V3", "2": "GND"},
     (G(119), G(44)), (23.3, 20.0, 90, "F"))
part("TP7", "Connector:TestPoint", "ESP_RX0", TP10, {"1": "ESP_RX0"},
     (G(126), G(44)), (2.0, 20.0, 0, "F"))
part("TP8", "Connector:TestPoint", "ESP_TX0", TP10, {"1": "ESP_TX0"},
     (G(130), G(44)), (2.0, 22.0, 0, "F"))
part("TP9", "Connector:TestPoint", "ESP_BOOT", TP10, {"1": "ESP_BOOT"},
     (G(134), G(44)), (2.0, 24.0, 0, "F"))

# ---------------------------------------------------------------- mic, button, LED
part("MK1", "Sensor_Audio:SPH0641LU4H-1", "SPH0641LU4H-1",
     "Sensor_Audio:Knowles_LGA-5_3.5x2.65mm",
     {"5": "MIC_VDD", "3": "GND", "4": "PDM_CLK", "1": "PDM_DATA", "2": "GND"},
     (G(100), G(66)), (20.5, 5.0, 0, "B"), mpn="SPH0641LU4H-1")
part("R10", "Device:R", "100R", R0402, {"1": "MIC_PWR", "2": "MIC_VDD"},
     (G(92), G(80)), (23.6, 4.0, 90, "B"))
part("C14", "Device:C", "1u", C0402, {"1": "MIC_VDD", "2": "GND"},
     (G(97), G(80)), (17.6, 4.2, 90, "B"))
part("C11", "Device:C", "100n", C0402, {"1": "MIC_VDD", "2": "GND"},
     (G(102), G(80)), (17.6, 6.2, 90, "B"))

part("SW1", "Switch:SW_Push", "KSC621J", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC6xxJ",
     {"1": "BTN", "2": "GND"}, (G(122), G(62)), (12.5, 11.0, 0, "F"), mpn="KSC621J LFS")

part("D1", "Device:LED_RGBA", "150080M153000", "LED_SMD:LED_RGB_Wuerth_150080M153000",
     {"1": "LED_RK", "2": "LED_GK", "3": "LED_BK", "4": "VBAT"},
     (G(124), G(76)), (21.5, 8.0, 0, "F"), mpn="150080M153000")
part("R7", "Device:R", "470R", R0402, {"1": "LED_R", "2": "LED_RK"},
     (G(112), G(88)), (20.0, 10.4, 0, "F"))
part("R8", "Device:R", "220R", R0402, {"1": "LED_G", "2": "LED_GK"},
     (G(117), G(88)), (20.0, 11.8, 0, "F"))
part("R9", "Device:R", "220R", R0402, {"1": "LED_B", "2": "LED_BK"},
     (G(122), G(88)), (20.0, 13.2, 0, "F"))

# ---------------------------------------------------------------- debug pads
_dbg = [("TP10", "SWDIO"), ("TP11", "SWDCLK"), ("TP12", "NRESET"), ("TP13", "3V3"),
        ("TP14", "GND"), ("TP15", "DBG_TX"), ("TP16", "DBG_RX")]
for i, (ref, net) in enumerate(_dbg):
    part(ref, "Connector:TestPoint", net, TP10, {"1": net},
         (G(96 + 4 * i), G(98)), (8.0 + 1.8 * i, 28.0, 0, "B"))

# ---------------------------------------------------------------- ERC power flags
for i, net in enumerate(["GND", "VBUS", "MIC_VDD"]):
    part("#FLG0%d" % (i + 1), "power:PWR_FLAG", "PWR_FLAG", "", {"1": net},
         (G(64 + 5 * i), G(108)), None)

TITLES = [
    ("Charge et alimentation 3V3", G(6), G(6)),
    ("nRF9151 : LTE-M + MCU, eSIM, antenne LTE", G(6), G(36)),
    ("ESP32-C6 : scan Wi-Fi + BLE (firmware ESP-AT)", G(90), G(6)),
    ("Micro, bouton, LED", G(90), G(56)),
    ("Pastilles de test", G(90), G(94)),
]

NOTES = [
    ("Z1..Z5 : reseau d'adaptation LTE, valeurs a regler au VNA.\n"
     "TP5 = point d'alimentation de l'antenne dans la coque, TP6 = masse.\n"
     "J1 (U.FL) non monte : mesure ou antenne externe.", G(28), G(100)),
    ("U3 : SEL = haut, CFG1 = 36.5k, CFG2 = 0R -> 3.3 V sans limite de courant\n"
     "(datasheet TPS63900, tableau 7-2).\n"
     "U4 : 10k sur PROG -> charge 100 mA.", G(46), G(38)),
    ("C15 (DEC0) non monte :\na confirmer (schema de\nreference Nordic).", G(17), G(51)),
]


# ---------------------------------------------------------------- PCB placement
# Authoritative placement table (overrides the tuples given above).
# ref: (x mm, y mm, rotation deg, side). Coordinates are as seen from the top
# (face A = F = user side, face B = B = battery side).
PLACEMENT = {
    # ---- face A (user side)
    "U2": (12.5, 24.0, 180, "F"),
    "SW1": (12.5, 10.5, 0, "F"),
    "TP1": (2.6, 8.0, 0, "F"), "TP2": (2.6, 12.0, 0, "F"),
    "D3": (5.6, 8.0, 90, "F"), "D2": (5.9, 12.0, 90, "F"),
    "R7": (21.0, 10.4, 0, "F"), "R8": (21.0, 11.6, 0, "F"), "R9": (21.0, 12.8, 0, "F"),
    "D1": (21.6, 15.2, 0, "F"),
    "TP9": (5.3, 16.9, 0, "F"), "R6": (7.6, 16.9, 90, "F"), "R5": (9.3, 16.9, 90, "F"),
    "R4": (21.6, 21.2, 0, "F"), "C13": (21.6, 22.6, 0, "F"),
    "C5": (21.5, 26.0, 90, "F"), "C10": (23.4, 26.0, 90, "F"),
    "TP7": (2.5, 23.6, 0, "F"), "TP8": (2.5, 25.8, 0, "F"),
    # ---- face B (battery side)
    "U1": (13.5, 16.0, 180, "B"),
    "Z2": (15.75, 9.1, 90, "B"), "Z4": (15.75, 7.0, 90, "B"),
    "Z1": (14.25, 9.6, 0, "B"), "Z3": (14.25, 8.05, 0, "B"), "Z5": (14.25, 6.55, 0, "B"),
    "J1": (15.75, 3.4, 90, "B"), "TP5": (19.7, 3.0, 0, "B"), "TP6": (22.5, 3.0, 0, "B"),
    "MK1": (22.4, 7.6, 0, "B"),
    "C14": (21.0, 10.3, 0, "B"), "C11": (23.2, 10.3, 0, "B"), "R10": (21.0, 11.5, 0, "B"),
    "TP10": (21.0, 13.2, 0, "B"), "TP11": (23.2, 13.2, 0, "B"),
    "TP12": (21.0, 15.4, 0, "B"), "TP13": (23.2, 15.4, 0, "B"),
    "TP14": (21.0, 17.6, 0, "B"), "TP15": (23.2, 17.6, 0, "B"),
    "TP16": (21.0, 19.8, 0, "B"),
    "C15": (10.5, 9.4, 0, "B"),
    "C1": (2.0, 13.4, 90, "B"), "C2": (4.3, 13.4, 90, "B"), "C8": (6.3, 12.3, 90, "B"),
    "TP3": (2.0, 17.6, 0, "B"), "TP4": (2.0, 20.7, 0, "B"),
    "U4": (2.4, 24.0, 0, "B"), "C6": (2.0, 27.0, 0, "B"), "C7": (5.3, 27.0, 0, "B"),
    "R1": (5.6, 23.0, 90, "B"), "R3": (5.6, 25.1, 90, "B"),
    "U5": (11.2, 25.0, 0, "B"), "C12": (11.2, 28.45, 0, "B"),
    "C9": (16.6, 22.6, 0, "B"), "L1": (16.6, 24.6, 90, "B"),
    "U3": (19.9, 24.0, 0, "B"), "R2": (23.0, 24.0, 90, "B"),
    "C3": (19.0, 27.0, 0, "B"), "C4": (22.8, 27.0, 0, "B"),
}

# Oval variant: 28 x 38 mm ellipse, centre (14, 19). Same faces as the rectangle.
PLACEMENT_OVAL = {
    # ---- face A (user side)
    "U2": (14.0, 24.4, 180, "F"),
    "SW1": (14.0, 14.9, 0, "F"),
    "TP1": (3.6, 15.2, 0, "F"), "TP2": (24.4, 15.2, 0, "F"),
    "D3": (3.9, 12.3, 0, "F"), "D2": (7.3, 15.2, 90, "F"),
    "D1": (14.0, 8.5, 0, "F"),
    "R7": (10.5, 7.6, 0, "F"), "R8": (10.5, 8.8, 0, "F"), "R9": (10.5, 10.0, 0, "F"),
    "R5": (2.6, 23.0, 90, "F"), "R6": (2.6, 25.1, 90, "F"),
    "TP7": (4.6, 22.0, 0, "F"), "TP8": (4.6, 24.2, 0, "F"), "TP9": (4.6, 26.4, 0, "F"),
    "R4": (22.4, 21.6, 0, "F"), "C13": (22.4, 23.0, 0, "F"),
    "C5": (22.3, 26.4, 90, "F"), "C10": (24.2, 26.4, 90, "F"),
    # ---- face B (battery side)
    "U1": (11.75, 15.05, 180, "B"),
    "Z2": (14.0, 8.15, 90, "B"), "Z4": (14.0, 6.05, 90, "B"),
    "Z1": (12.5, 8.65, 0, "B"), "Z3": (12.5, 7.1, 0, "B"), "Z5": (12.5, 5.6, 0, "B"),
    "J1": (14.0, 2.45, 90, "B"), "TP5": (18.1, 3.9, 0, "B"), "TP6": (21.0, 6.2, 0, "B"),
    "C15": (8.75, 8.45, 0, "B"),
    "MK1": (21.2, 10.5, 0, "B"),
    "C14": (21.2, 13.3, 0, "B"), "C11": (23.4, 13.3, 0, "B"), "R10": (21.2, 14.5, 0, "B"),
    "TP10": (20.2, 16.4, 0, "B"), "TP11": (22.4, 16.4, 0, "B"), "TP12": (24.6, 16.4, 0, "B"),
    "TP13": (20.2, 18.6, 0, "B"), "TP14": (22.4, 18.6, 0, "B"),
    "TP15": (20.2, 20.8, 0, "B"), "TP16": (22.4, 20.8, 0, "B"),
    "C8": (4.2, 11.6, 90, "B"), "C2": (4.2, 15.0, 90, "B"), "C1": (2.0, 16.0, 90, "B"),
    "TP3": (2.2, 19.7, 0, "B"), "TP4": (25.7, 19.6, 0, "B"),
    "U4": (4.0, 24.0, 0, "B"), "R1": (7.2, 23.0, 90, "B"), "R3": (7.2, 25.1, 90, "B"),
    "C6": (3.6, 27.0, 0, "B"), "C7": (6.9, 27.0, 0, "B"),
    "U5": (12.45, 25.0, 0, "B"), "C12": (12.45, 28.45, 0, "B"),
    "C9": (17.6, 22.6, 0, "B"), "L1": (17.6, 24.6, 90, "B"),
    "U3": (20.9, 24.0, 0, "B"), "R2": (24.0, 24.0, 90, "B"),
    "C3": (20.0, 27.0, 0, "B"), "C4": (23.8, 27.0, 0, "B"),
}
if VARIANT == "oval":
    BOARD_W, BOARD_H = 28.0, 38.0
    PLACEMENT = PLACEMENT_OVAL

for _p in PARTS:
    if _p["fp"]:
        _p["pcb"] = PLACEMENT[_p["ref"]]


def fill_outline(n=180):
    """Contour of the board area that may carry copper pours: everything below
    the LTE antenna strip (y >= LTE_KEEPOUT_H)."""
    import math
    W, H, K = BOARD_W, BOARD_H, LTE_KEEPOUT_H
    if SHAPE == "rect":
        return [(0, K), (W, K), (W, H), (0, H)]
    a, b = W / 2, H / 2
    p0 = math.acos((b - K) / b)
    return [(a + a * math.sin(p), b - b * math.cos(p))
            for p in (p0 + (2 * math.pi - 2 * p0) * i / n for i in range(n + 1))]
