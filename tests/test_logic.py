# Unit tests for the pure-logic files. Run from the firmware folder:
#   micropython ../tests/test_logic.py     (or: python3 ../tests/test_logic.py)
import sys
sys.path.insert(0, ".")
import math
import struct

from twist import TwistFilter, wrap180
from haptics import Guide
from protocol import angle_message, parse_command
from mpu6050 import MPU6050

passed = 0
def check(name, cond):
    global passed
    if not cond:
        raise AssertionError(name)
    passed += 1

# ---- wrap180 ----
check("wrap 190", abs(wrap180(190) - (-170)) < 1e-9)
check("wrap -190", abs(wrap180(-190) - 170) < 1e-9)
check("wrap 180", wrap180(180) == 180)
check("wrap -180", wrap180(-180) == 180)

# ---- TwistFilter: follows a steady rotation, and holds an angle without drifting ----
def feed(f, theta_deg, rate, dt, arm=0.0):
    t = math.radians(theta_deg)
    return f.update(arm, math.sin(t), math.cos(t), rate, dt)

f = TwistFilter(0.98)
dt = 0.01
theta = 0.0
feed(f, theta, 0, dt)
for _ in range(200):                 # rotate at 45 deg/s for 2 s -> 90 deg
    theta += 45 * dt
    out = feed(f, theta, 45, dt)
check("tracks rotation", abs(out - 90) < 1.0)

f = TwistFilter(0.98)                # gyro with a 2 deg/s bias, hand still at 30 deg
feed(f, 30, 0, dt)
for _ in range(1000):
    out = feed(f, 30, 2.0, dt)
check("gravity corrects gyro drift", abs(out - 30) < 1.5)

f = TwistFilter(0.98)                # zero at thumb-up (90 deg), then twist through 180 absolute
feed(f, 90, 0, dt)
f.set_zero()
theta = 90.0
for _ in range(100):
    theta += 100 * dt                # to 190 deg absolute = palm fully up and beyond
    out = feed(f, theta, 100, dt)
check("no wrap jump inside wrist range", abs(out - 100) < 2.0)

f = TwistFilter(0.98)                # forearm pointing straight down: gravity unusable, gyro only
feed(f, 0, 0, dt)
for _ in range(100):
    out = f.update(1.0, 0.0, 0.0, 50, dt)
check("gyro-only when arm is vertical", abs(out - 50) < 1.0)

f = TwistFilter(0.98)
check("not ready until gravity seen", f.update(1.0, 0.0, 0.0, 0, dt) == 0.0 and not f.ready)

# ---- Guide ----
def run_guide(g, angle_fn, ms_total, step=10):
    log = []
    for now in range(0, ms_total, step):
        d = g.update(now, angle_fn(now))
        log.append((now, tuple(d)))
    return log

def active(d):
    return [i for i, v in enumerate(d) if v > 0]

g = Guide(strength=50000)
check("idle = all off", g.update(0, 0.0) == [0, 0, 0, 0])

g.start(50.0, 3.0)                   # target is ahead (positive direction), far away
log = run_guide(g, lambda t: 0.0, 2000)
order = []
for _, d in log:
    a = active(d)
    check("one motor at a time while guiding", len(a) <= 1)
    if a and (not order or order[-1] != a[0]):
        order.append(a[0])
check("sweeps forward 0,1,2,3", order[:5] == [0, 1, 2, 3, 0])
on = sum(1 for _, d in log if active(d))
check("pulse duty about 70/260", 0.2 < on / len(log) < 0.35)

g = Guide(strength=50000)
g.start(-50.0, 3.0)                  # target behind: sweep runs the other way
log = run_guide(g, lambda t: 0.0, 2000)
order = []
for _, d in log:
    a = active(d)
    if a and (not order or order[-1] != a[0]):
        order.append(a[0])
check("sweeps backward 0,3,2,1", order[:4] == [0, 3, 2, 1])

g = Guide(strength=50000, sweep_dir=-1)
g.start(50.0, 3.0)
log = run_guide(g, lambda t: 0.0, 1000)
order = []
for _, d in log:
    a = active(d)
    if a and (not order or order[-1] != a[0]):
        order.append(a[0])
check("sweep_dir flips the order", order[:3] == [0, 3, 2])

g = Guide()
check("far tempo", g.step_interval(90) == 260)
g.tol = 3.0
check("near tempo", g.step_interval(3.0) == 110)
check("tempo speeds up as error shrinks", g.step_interval(40) > g.step_interval(20) > g.step_interval(5))

g = Guide(strength=50000)            # approach and arrive
g.start(30.0, 3.0)
log = run_guide(g, lambda t: min(30.0, t * 0.03), 2000)   # reaches 27 deg (edge) at 900 ms
clicks = [now for now, d in log if len(active(d)) == 4]
check("click happens", len(clicks) > 0)
check("click lasts about 60 ms", 50 <= (clicks[-1] - clicks[0] + 10) <= 70)
check("click starts on arrival", 880 <= clicks[0] <= 920)
after = [d for now, d in log if now > clicks[-1]]
check("silent after the click", all(len(active(d)) == 0 for d in after))
check("inside flag set", g.inside)

g = Guide(strength=50000, exit_margin=1.0)   # jitter at the boundary must not re-click
g.start(30.0, 3.0)
g.update(0, 27.5)                    # inside -> click starts
n_clicks = 0
prev4 = False
for now in range(10, 1000, 10):
    ang = 26.8 if (now // 10) % 2 else 27.2   # error 3.2 / 2.8: wobbling across the 3 deg edge
    d = g.update(now, ang)
    is4 = len(active(d)) == 4
    if is4 and not prev4:
        n_clicks += 1
    prev4 = is4
check("no click chatter at the edge", n_clicks <= 1)

g.stop()
check("stop = all off", g.update(5000, 0.0) == [0, 0, 0, 0] and not g.inside)

# ---- protocol ----
check("angle message", angle_message(1234, -12.345, True, False) in ("A,1234,-12.35,1,0\n", "A,1234,-12.34,1,0\n"))
check("parse T", parse_command(b"T,30.5,3,1") == ("T", 30.5, 3.0, True))
check("parse T haptics off", parse_command(b"T,-40,5,0\n") == ("T", -40.0, 5.0, False))
check("parse T default haptics on", parse_command(b"T,10,2") == ("T", 10.0, 2.0, True))
check("parse S", parse_command(b"S") == ("S",))
check("parse Z", parse_command(b"Z\n") == ("Z",))
check("garbage ignored", parse_command(b"T,abc") is None and parse_command(b"") is None and parse_command(b"A,1,2,3,4") is None)

# ---- MPU6050 driver with a fake I2C bus ----
class FakeI2C:
    def __init__(self):
        self.writes = []
        self.frame = struct.pack(">hhhhhhh", 0, 8192, 16384, 0, 328, 0, -656)
    def writeto_mem(self, addr, reg, data):
        self.writes.append((addr, reg, bytes(data)))
    def readfrom_mem(self, addr, reg, n):
        return bytes([0x68])
    def readfrom_mem_into(self, addr, reg, buf):
        for i in range(len(buf)):
            buf[i] = self.frame[i]

bus = FakeI2C()
m = MPU6050(bus)
check("wakes the chip", (0x68, 0x6B, b"\x01") in bus.writes)
check("sets low-pass filter", (0x68, 0x1A, b"\x03") in bus.writes)
ax, ay, az, gx, gy, gz = m.read()
check("accel scaling", abs(ay - 0.5) < 1e-6 and abs(az - 1.0) < 1e-6 and ax == 0)
check("gyro scaling", abs(gx - 10.0) < 1e-3 and abs(gz + 20.0) < 1e-3)
m.calibrate_gyro(samples=10)
ax, ay, az, gx, gy, gz = m.read()
check("gyro bias removed", abs(gx) < 1e-6 and abs(gz) < 1e-6)
check("who_am_i", m.who_am_i() == 0x68)

print("test_logic: all %d checks passed" % passed)
