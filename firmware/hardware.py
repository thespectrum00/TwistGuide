# Sets up the board's pins. Shared by band.py and checks.py.
from machine import Pin, I2C, PWM
import config
from mpu6050 import MPU6050


def make_i2c():
    return I2C(0, scl=Pin(config.PIN_SCL), sda=Pin(config.PIN_SDA), freq=400000)


def make_sensor(i2c=None):
    return MPU6050(i2c or make_i2c())


def make_motors():
    motors = []
    for pin in config.PIN_MOTORS:
        pwm = PWM(Pin(pin), freq=config.MOTOR_PWM_HZ)
        pwm.duty_u16(0)
        motors.append(pwm)
    return motors


def motors_off(motors):
    for m in motors:
        m.duty_u16(0)


def make_button():
    return Pin(config.PIN_BUTTON, Pin.IN, Pin.PULL_UP)   # pressed reads 0


def make_led():
    led = Pin(config.PIN_LED, Pin.OUT)
    led.value(1)                                         # inverted: 1 = off
    return led


def twist_inputs(reading):
    """Pick the right sensor axes for how the board is mounted.

    Returns (a_arm, a_side, a_up, rate) for TwistFilter.update().
    """
    ax, ay, az, gx, gy, gz = reading
    s = config.TWIST_SIGN
    if config.ARM_AXIS == "x":
        return ax, s * ay, az, s * gx
    return ay, s * -ax, az, s * gy


def connect_wifi(led=None):
    """Join the phone's hotspot. Returns (wlan, phone_ip), or (None, None) if it fails."""
    import network
    import time
    try:
        import wifi_secrets
    except ImportError:
        print("No wifi_secrets.py found: running without Wi-Fi.")
        return None, None

    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    wlan.active(True)
    try:
        wlan.config(txpower=config.TX_POWER_DBM)
    except Exception as e:                # older firmware may not support this setting
        print("Could not set transmit power:", e)
    wlan.connect(wifi_secrets.WIFI_SSID, wifi_secrets.WIFI_PASSWORD)

    start = time.ticks_ms()
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > config.WIFI_TIMEOUT_S * 1000:
            print("Wi-Fi did not connect: running without it.")
            wlan.active(False)
            return None, None
        if led:
            led.value(not led.value())
        time.sleep_ms(200)

    ip, _mask, gateway, _dns = wlan.ifconfig()
    print("Wi-Fi connected. Band:", ip, " Phone (hotspot gateway):", gateway)
    if led:
        led.value(0)                      # solid on = connected
    return wlan, gateway
