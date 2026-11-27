# Runs every script in firmware/component_tests under desktop MicroPython with fake hardware,
# to catch syntax and logic errors before they reach the board.
#   cd firmware && micropython ../tests/test_component_scripts.py
import sys
import math
import struct
import time
import os

LOG = {"pwm": [], "led": [], "writes": []}
T0 = time.ticks_ms()

class Pin:
    IN = 0; OUT = 1; PULL_UP = 2
    def __init__(self, n, mode=None, pull=None):
        self.n = n; self._v = 1; self.mode = mode
    def value(self, v=None):
        if v is None:
            if self.mode == Pin.IN:                       # fake button: pressed during 300-600 ms
                t = time.ticks_diff(time.ticks_ms(), T0) % 1000
                return 0 if 300 < t < 600 else 1
            return self._v
        self._v = 1 if v else 0
        LOG["led"].append((self.n, self._v))

class PWM:
    def __init__(self, pin, freq=0):
        self.pin = pin.n
    def duty_u16(self, v=None):
        LOG["pwm"].append((self.pin, v))

class I2C:
    def __init__(self, id, scl=None, sda=None, freq=0):
        self.t0 = time.ticks_ms()
    def scan(self): return [0x68, 0x77]
    def writeto_mem(self, a, r, d): LOG["writes"].append((a, r, bytes(d)))
    def readfrom_mem(self, a, r, n): return bytes([0x68])
    def readfrom_mem_into(self, a, r, buf):
        ms = time.ticks_diff(time.ticks_ms(), self.t0)
        deg = 0.0 if ms < 1300 else min(45.0, (ms - 1300) * 0.09)     # still, then twist to 45 degrees
        rate = 90.0 if (ms >= 1300 and deg < 45.0) else 0.0
        th = math.radians(deg)
        frame = struct.pack(">hhhhhhh", 0, int(16384 * math.sin(th)), int(16384 * math.cos(th)),
                            int((25.0 - 36.53) * 340), int(rate * 32.8), 0, 0)
        for i in range(14):
            buf[i] = frame[i]

class _M: pass
machine = _M(); machine.Pin = Pin; machine.PWM = PWM; machine.I2C = I2C
sys.modules["machine"] = machine

class WLAN:
    def __init__(self, kind): self.on = False
    def active(self, v=None): pass
    def config(self, **kw): LOG["txpower"] = kw.get("txpower")
    def connect(self, ssid, pw): LOG["ssid"] = ssid; self.on = True
    def isconnected(self): return self.on
    def ifconfig(self): return ("192.168.43.50", "255.255.255.0", "192.168.43.1", "192.168.43.1")
    def status(self, what): return -41
network = _M(); network.WLAN = WLAN; network.STA_IF = 0
sys.modules["network"] = network

class Capture:
    def __init__(self): self.lines = []
OUT = Capture()
def fake_print(*args, **kw):
    OUT.lines.append(" ".join(str(a) for a in args))

folder = "component_tests"
names = sorted(n for n in os.listdir(folder) if n.endswith(".py"))
results = {}
for name in names:
    src = open(folder + "/" + name).read()
    for d in ("DURATION_S = 10", "DURATION_S = 15", "DURATION_S = 20"):
        src = src.replace(d, "DURATION_S = 3")
    src = src.replace("BLINKS = 10", "BLINKS = 2").replace("ROUNDS = 3", "ROUNDS = 1")
    OUT.lines = []; LOG["pwm"] = []; LOG["led"] = []
    g = {"__name__": "__main__", "print": fake_print}
    exec(src, g)
    results[name] = (list(OUT.lines), list(LOG["pwm"]), list(LOG["led"]))
    print("ran", name, "-", len(OUT.lines), "lines printed")

def check(name, cond):
    if not cond:
        raise AssertionError(name)

lines, pwm, led = results["01_led_blink.py"]
check("blink toggles the LED pin 8", [v for n, v in led if n == 8] == [0, 1, 0, 1])

lines, _, _ = results["02_i2c_scan.py"]
check("scan reports the sensor", any("0x68" in l and "found" in l.lower() for l in lines))

lines, _, _ = results["03_mpu6050_raw.py"]
row = [l for l in lines if l.startswith("accel g:")][0]
check("raw read prints 1 g on z when flat", " 1.00" in row and "temp C: 25.0" in row)
check("raw read wakes the chip", (0x68, 0x6B, b"\x01") in LOG["writes"])

lines, _, _ = results["04_mpu6050_twist_angle.py"]
vals = [float(l.split()[1]) for l in lines if l.startswith("twist:")]
check("twist starts near 0", abs(vals[0]) < 2.0)
check("twist ends near 45 degrees (got %.1f)" % vals[-1], abs(vals[-1] - 45.0) < 2.5)

lines, pwm, _ = results["05_motor_single.py"]
check("single motor uses pin 0 only", all(p == 0 for p, v in pwm))
check("single motor ends off", pwm[-1] == (0, 0))
check("single motor reaches full strength", (0, 65535) in pwm)

lines, pwm, _ = results["06_motor_sweep.py"]
ons = [p for p, v in pwm if v == 52000]
check("sweep forward then backward", ons == [0, 1, 3, 10, 10, 3, 1, 0])
last = {}
for p, v in pwm: last[p] = v
check("sweep leaves all four motors off", all(last[p] == 0 for p in (0, 1, 3, 10)))
check("sweep ends with an all-four click", sum(1 for p, v in pwm if v == 65535) == 4)

lines, _, _ = results["07_button.py"]
check("button reports presses and releases", "pressed" in lines and "released" in lines)

lines, _, _ = results["08_wifi_hotspot.py"]
check("wifi reports both addresses", any("192.168.43.50" in l for l in lines) and any("192.168.43.1" in l for l in lines))
check("wifi sets low transmit power", LOG.get("txpower") == 8.5)

print("test_component_scripts: all checks passed")
