# Arrival checks. In Thonny's shell, type:   import checks
# then run them one at a time, for example:  checks.blink()
import time

import config
import hardware


def blink(times=10):
    """1. The board is alive: the onboard LED blinks."""
    led = hardware.make_led()
    for _ in range(times):
        led.value(0)
        time.sleep_ms(200)
        led.value(1)
        time.sleep_ms(200)
    print("Blink done.")


def scan():
    """2. The sensor answers: expect 0x68 in the list."""
    found = hardware.make_i2c().scan()
    print("Devices found:", [hex(a) for a in found])
    if 0x68 in found:
        print("MPU6050 found at 0x68.")
    else:
        print("0x68 is missing: check power, ground, SDA to pin %d, SCL to pin %d."
              % (config.PIN_SDA, config.PIN_SCL))


def sensor(seconds=10):
    """3. The sensor reads sensibly: lay it flat and 'up' should read about 1.0."""
    from twist import TwistFilter
    s = hardware.make_sensor()
    print("Chip ID:", hex(s.who_am_i()), "(0x68 is the genuine part; clones may differ)")
    f = TwistFilter(config.FILTER_ALPHA)
    end = time.ticks_add(time.ticks_ms(), seconds * 1000)
    last = time.ticks_us()
    n = 0
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        now = time.ticks_us()
        dt = time.ticks_diff(now, last) / 1000000
        last = now
        reading = s.read()
        a_arm, a_side, a_up, rate = hardware.twist_inputs(reading)
        angle = f.update(a_arm, a_side, a_up, rate, dt)
        n += 1
        if n % 20 == 0:
            print("arm %.2f  side %.2f  up %.2f   twist %.1f" % (a_arm, a_side, a_up, angle))
        time.sleep_ms(10)


def motor(index=0, seconds=1.0):
    """4. One motor buzzes. index 0 to 3 = M1 to M4."""
    motors = hardware.make_motors()
    try:
        motors[index].duty_u16(config.MOTOR_STRENGTH)
        time.sleep(seconds)
    finally:
        hardware.motors_off(motors)
    print("Motor", index + 1, "done.")


def sweep(rounds=3, step_ms=200):
    """5. All four buzz in order M1, M2, M3, M4: check they go round the wrist."""
    motors = hardware.make_motors()
    try:
        for _ in range(rounds):
            for m in motors:
                m.duty_u16(config.MOTOR_STRENGTH)
                time.sleep_ms(config.PULSE_MS)
                m.duty_u16(0)
                time.sleep_ms(step_ms - config.PULSE_MS)
    finally:
        hardware.motors_off(motors)
    print("Sweep done.")


def wifi():
    """6. The board joins your phone's hotspot."""
    wlan, phone_ip = hardware.connect_wifi(hardware.make_led())
    if wlan:
        try:
            print("Signal strength:", wlan.status("rssi"), "dBm")
        except Exception:
            pass
    return phone_ip


def button(seconds=10):
    """7. The setup button registers presses."""
    b = hardware.make_button()
    print("Press the button a few times...")
    end = time.ticks_add(time.ticks_ms(), seconds * 1000)
    was = False
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        now = b.value() == 0
        if now and not was:
            print("pressed")
        was = now
        time.sleep_ms(20)
    print("Button check done.")
