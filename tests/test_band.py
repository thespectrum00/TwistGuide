# Integration test: runs the real band.py loop under desktop MicroPython with fake hardware.
# The fake wrist turns from 0 to 40 degrees over 2 s; the fake phone asks for a 40 degree target.
#   cd firmware && micropython ../tests/test_band.py
import sys
sys.path.insert(0, ".")
import math
import struct
import time

LOG = {"duty": [], "sent": [], "led": []}
T0 = time.ticks_ms()
RUN_MS = 5500
START_MS = 1500        # the wrist stays still while the band measures its gyro offset

def elapsed():
    return time.ticks_diff(time.ticks_ms(), T0)

def wrist_angle(ms):
    if ms < START_MS:
        return 0.0
    return min(40.0, (ms - START_MS) * 0.02)   # 20 degrees per second up to 40

# ---------- fake machine ----------
class Pin:
    IN = 0; OUT = 1; PULL_UP = 2
    def __init__(self, n, mode=None, pull=None):
        self.n = n; self._v = 1
    def value(self, v=None):
        if v is None:
            return self._v
        self._v = 1 if v else 0
        if self.n == 8:
            LOG["led"].append(self._v)

class PWM:
    def __init__(self, pin, freq=0):
        self.pin = pin.n; self.freq = freq
    def duty_u16(self, v=None):
        LOG["duty"].append((elapsed(), self.pin, v))

class I2C:
    def __init__(self, id, scl=None, sda=None, freq=0):
        self.reads = 0
    def writeto_mem(self, a, r, d): pass
    def readfrom_mem(self, a, r, n): return bytes([0x68])
    def scan(self): return [0x68]
    def readfrom_mem_into(self, a, r, buf):
        ms = elapsed()
        if ms > RUN_MS:
            raise KeyboardInterrupt
        th = math.radians(wrist_angle(ms))
        rate = 20.0 if (ms >= START_MS and (ms - START_MS) * 0.02 < 40.0) else 0.0
        frame = struct.pack(">hhhhhhh", 0, int(16384 * math.sin(th)), int(16384 * math.cos(th)),
                            0, int(rate * 32.8), 0, 0)
        for i in range(14):
            buf[i] = frame[i]

class _M: pass
machine = _M(); machine.Pin = Pin; machine.PWM = PWM; machine.I2C = I2C
sys.modules["machine"] = machine

# ---------- fake network ----------
class WLAN:
    def __init__(self, kind): self._on = False
    def active(self, v=None): pass
    def config(self, **kw): LOG["txpower"] = kw.get("txpower")
    def connect(self, ssid, pw): LOG["ssid"] = ssid; self._on = True
    def isconnected(self): return self._on
    def ifconfig(self): return ("192.168.43.50", "255.255.255.0", "192.168.43.1", "192.168.43.1")
    def status(self, what): return -40
network = _M(); network.WLAN = WLAN; network.STA_IF = 0
sys.modules["network"] = network

secrets = _M(); secrets.WIFI_SSID = "test-hotspot"; secrets.WIFI_PASSWORD = "x"
sys.modules["wifi_secrets"] = secrets

# ---------- fake socket ----------
class FakeSock:
    def __init__(self, *a):
        self.inbox = [(b"T,40,3,1", ("192.168.43.1", 5555))]
    def bind(self, addr): LOG["bound"] = addr
    def setblocking(self, v): pass
    def recvfrom(self, n):
        if self.inbox and elapsed() > START_MS + 100:
            return self.inbox.pop(0)
        raise OSError(11)
    def sendto(self, data, addr):
        LOG["sent"].append((elapsed(), bytes(data), addr))
    def close(self): LOG["closed"] = True
socket = _M(); socket.socket = FakeSock; socket.AF_INET = 2; socket.SOCK_DGRAM = 2
sys.modules["socket"] = socket

import config
config.PRINT_STATS = False
config.PRINT_TO_USB = False
import band

try:
    band.run()
except KeyboardInterrupt:
    pass

def check(name, cond):
    if not cond:
        raise AssertionError(name)

motor_pins = list(config.PIN_MOTORS)
# Reconstruct the motor state over time
state = {p: 0 for p in motor_pins}
timeline = []
for ms, pin, v in LOG["duty"]:
    if state[pin] != v:
        state[pin] = v
        timeline.append((ms, tuple(state[p] for p in motor_pins)))

check("wifi joined with low power", LOG.get("ssid") == "test-hotspot" and LOG.get("txpower") == config.TX_POWER_DBM)
check("socket bound on the agreed port", LOG.get("bound") == ("0.0.0.0", config.UDP_PORT))

sent = LOG["sent"]
span = (sent[-1][0] - sent[0][0]) / 1000
rate = (len(sent) - 1) / span
check("sends about 50 messages a second (got %.1f)" % rate, 42 <= rate <= 52)
check("first messages go to the hotspot gateway", sent[0][2] == ("192.168.43.1", config.UDP_PORT))
last = sent[-1][1].decode().strip().split(",")
check("message format", last[0] == "A" and len(last) == 5)
check("final angle about 40 degrees", abs(float(last[2]) - 40.0) < 1.5)
check("reports on-target at the end", last[4] == "1")
early = sent[5][1].decode().strip().split(",")
check("not on-target at the start", early[4] == "0")

single = [(ms, s) for ms, s in timeline if sum(1 for v in s if v) == 1]
order = []
for ms, s in single:
    i = [k for k, v in enumerate(s) if v][0]
    if not order or order[-1] != i:
        order.append(i)
check("motors silent before the phone's command", all(ms >= START_MS + 100 for ms, s in timeline))
check("guiding sweep runs forward round the wrist", order[:4] == [0, 1, 2, 3])
quad = []                               # start time of each all-four-on episode
was_all = False
for ms, st in timeline:
    now_all = all(st)
    if now_all and not was_all:
        quad.append(ms)
    was_all = now_all
check("one arrival click with all four motors", len(quad) == 1)
check("click near the moment the wrist reaches the target zone (37 deg at 3350 ms)", 3250 <= quad[0] <= 3500)
check("motors off after the click and at shutdown", timeline[-1][1] == (0, 0, 0, 0) and all(state[p] == 0 for p in motor_pins))
gaps = [b[0] - a[0] for a, b in zip(single, single[1:])]
check("socket closed and LED off on exit", LOG.get("closed") and LOG["led"][-1] == 1)

print("test_band: all checks passed")
print("  messages sent: %d in %.1f s; sweep order: %s; click at %d ms; final angle %s"
      % (len(sent), span, order[:8], quad[0], last[2]))
