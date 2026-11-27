# Pins and tuning values for the haptic wristband (ESP32-C3 Super Mini).
# Wi-Fi name and password live in wifi_secrets.py, which stays out of the repository.

# --- Pins ---
PIN_SDA = 6
PIN_SCL = 7
PIN_MOTORS = (0, 1, 3, 10)   # M1 back of wrist, M2 little-finger side, M3 underside, M4 thumb side
PIN_BUTTON = 5               # setup button to ground (internal pull-up)
PIN_LED = 8                  # onboard LED, inverted: 0 = on

# --- Sensor mounting ---
ARM_AXIS = "x"     # which sensor axis points along the forearm: "x" or "y"
TWIST_SIGN = 1     # set to -1 if twisting clockwise (as you look along your arm) makes the angle go down

# --- Timing ---
SAMPLE_HZ = 100    # sensor reads per second
SEND_EVERY = 2     # send every 2nd sample to the phone, so 50 times a second
FILTER_ALPHA = 0.98

# --- Network ---
UDP_PORT = 4210
# Where to send the angle. None = the hotspot gateway, which is the phone when the band
# joins the phone's hotspot. On a home router, set the phone's own address instead,
# e.g. PHONE_IP = "192.168.100.23" (phone: Settings > Wi-Fi > gear icon > IP address).
PHONE_IP = None
TX_POWER_DBM = 10   # low transmit power: steadier on this board, and the phone is within arm's reach
WIFI_TIMEOUT_S = 15

# --- Haptics (first guesses; tune these on your own wrist) ---
MOTOR_PWM_HZ = 1000
MOTOR_STRENGTH = 52000   # 0 to 65535
SWEEP_DIR = 1            # set to -1 if the circling cue runs the wrong way round
PULSE_MS = 70            # how long each motor buzzes per step
FAR_STEP_MS = 260        # step interval when far from the target
NEAR_STEP_MS = 110       # step interval just outside the target
FAR_DEG = 60.0           # errors at or beyond this use the slowest tempo
CLICK_MS = 60            # arrival click: all four motors together
EXIT_MARGIN_DEG = 1.0    # must leave the target by this much before the guide restarts

# --- Debug ---
PRINT_TO_USB = True      # print angle lines to Thonny's shell
PRINT_STATS = True       # print the achieved loop rate every 2 seconds
