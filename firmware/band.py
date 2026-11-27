# Main program for the haptic wristband.
# Run it from Thonny while testing. When it works, upload main.py so it starts on power-up.
import gc
import socket
import time

import config
import hardware
from haptics import Guide
from protocol import angle_message, parse_command
from twist import TwistFilter


def run():
    led = hardware.make_led()
    motors = hardware.make_motors()
    button = hardware.make_button()
    sensor = hardware.make_sensor()

    print("Hold the band still: measuring gyro offset...")
    sensor.calibrate_gyro(sleep_ms=time.sleep_ms)

    filt = TwistFilter(alpha=config.FILTER_ALPHA)
    guide = Guide(
        n_motors=len(motors),
        strength=config.MOTOR_STRENGTH,
        sweep_dir=config.SWEEP_DIR,
        pulse_ms=config.PULSE_MS,
        far_step_ms=config.FAR_STEP_MS,
        near_step_ms=config.NEAR_STEP_MS,
        far_deg=config.FAR_DEG,
        click_ms=config.CLICK_MS,
        exit_margin=config.EXIT_MARGIN_DEG,
    )
    haptics_on = True

    wlan, phone_ip = hardware.connect_wifi(led)
    sock = None
    if wlan:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", config.UDP_PORT))
        sock.setblocking(False)
    target_ip = getattr(config, "PHONE_IP", None) or phone_ip
    phone_addr = (target_ip, config.UDP_PORT) if (wlan and target_ip) else None
    if phone_addr:
        print("Sending angles to", target_ip)

    period_us = 1000000 // config.SAMPLE_HZ
    last_us = time.ticks_us()
    last_press_ms = time.ticks_ms()
    was_pressed = False
    count = 0
    stats_start = time.ticks_ms()
    stats_loops = 0

    print("Running. Press Stop in Thonny (or Ctrl+C) to end.")
    try:
        while True:
            loop_start = time.ticks_us()
            dt = time.ticks_diff(loop_start, last_us) / 1000000
            last_us = loop_start
            now_ms = time.ticks_ms()

            # 1. Sense and combine
            a_arm, a_side, a_up, rate = hardware.twist_inputs(sensor.read())
            angle = filt.update(a_arm, a_side, a_up, rate, dt)

            # 2. Setup button: a press sets the current position as zero
            pressed = button.value() == 0
            if pressed and not was_pressed and time.ticks_diff(now_ms, last_press_ms) > 250:
                filt.set_zero()
                last_press_ms = now_ms
            was_pressed = pressed

            # 3. Commands from the phone
            if sock:
                try:
                    data, sender = sock.recvfrom(64)
                    phone_addr = (sender[0], config.UDP_PORT)   # reply to whoever spoke last
                    cmd = parse_command(data)
                    if cmd:
                        if cmd[0] == "T":
                            guide.start(cmd[1], cmd[2])
                            haptics_on = cmd[3]
                        elif cmd[0] == "S":
                            guide.stop()
                        elif cmd[0] == "Z":
                            filt.set_zero()
                except OSError:
                    pass                                        # nothing waiting

            # 4. Guide: decide the motor strengths and apply them
            duty = guide.update(now_ms, angle)
            for i in range(len(motors)):
                motors[i].duty_u16(duty[i] if haptics_on else 0)

            # 5. Report
            count += 1
            if count % config.SEND_EVERY == 0:
                msg = angle_message(now_ms, angle, pressed, guide.inside)
                if sock and phone_addr:
                    try:
                        sock.sendto(msg.encode(), phone_addr)
                    except OSError:
                        pass
                if config.PRINT_TO_USB and not config.PRINT_STATS:
                    print(msg, end="")

            # 6. Housekeeping
            gc.collect()
            stats_loops += 1
            if config.PRINT_STATS and time.ticks_diff(now_ms, stats_start) >= 2000:
                hz = stats_loops * 1000 / time.ticks_diff(now_ms, stats_start)
                print("loop rate: %.0f per second   angle: %.1f" % (hz, angle))
                stats_start = now_ms
                stats_loops = 0

            spare = period_us - time.ticks_diff(time.ticks_us(), loop_start)
            if spare > 0:
                time.sleep_us(spare)
    finally:
        hardware.motors_off(motors)
        led.value(1)
        if sock:
            sock.close()
        print("Stopped. Motors off.")


if __name__ == "__main__":
    run()