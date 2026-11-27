# TwistGuide

Turn a virtual dial in phone AR by twisting your wrist.

A small band on the wrist measures how far the forearm twists and sends the angle over Wi-Fi to an Android AR app, where it turns a virtual dial placed in the room. A green needle shows the target, and the app runs and logs simple target trials.



## Status (November 2026)

- **Working:** wrist-twist sensing at 100 Hz, the Wi-Fi link to the phone, the AR dial following the wrist, the on-screen target, and trial logging to CSV.
- **Not done yet:** timed trials with other people, and a measurement of the delay between wrist and screen.
- **Next:** vibration motors around the wrist, so you can feel which way to turn instead of looking at the needle. The pattern is written in the firmware and tested against a simulated band, but the motors aren't fitted yet.

## How it works

| Part | What it does |
|---|---|
| **Band** | ESP32-C3 Super Mini + MPU6050 (gyroscope and accelerometer), a button to set zero, powered by a USB power bank. |
| **Firmware** | MicroPython. A 100 Hz loop combines the gyroscope and accelerometer with a complementary filter (α = 0.98) to get the twist angle. |
| **Link** | Plain-text UDP messages on port 4210 over the phone's Wi-Fi hotspot. The band sends its angle 50 times a second. |
| **App** | Unity 6.3 with AR Foundation and ARCore. Tap to place the dial, set zero, then turn the dial onto the target and tap to confirm. Each trial is saved with time taken, final error and overshoots. |

## Repository layout

```
Assets/      Unity project (scene: WristbandScene)
firmware/    MicroPython code for the band
paper/       LaTeX source for the report
docs/        wiring diagram and parts list
```

## Running it

**Band**
1. Flash MicroPython onto the ESP32-C3 (hold BOOT while plugging in if it keeps reconnecting).
2. Copy the files in `firmware/` to the board (for example with Thonny).
3. Add a `wifi_secrets.py` with your hotspot's name and password. It isn't in the repo.
4. Run `band.run()`. The printed line shows the loop rate and signal strength.

**App**
1. Open the project in Unity 6.3 LTS with Android Build Support.
2. Open `WristbandScene` and Build and Run to an ARCore-supported Android phone.
3. Turn on the phone's hotspot (2.4 GHz) and connect the band to it.
4. In the app: place the dial, wait for "Band connected", set zero, then start.

## Messages

| Direction | Message | Meaning |
|---|---|---|
| Band → phone | `A,<ms>,<deg>,<btn>,<on>` | time, twist angle, button, on target |
| Phone → band | `T,<deg>,<tol>,<hap>` | new target, tolerance, vibration on/off (for later) |
| Phone → band | `S` / `Z` | stop / set zero |

## Author

Adewola Saliu-Aina · wolasaliuaina@gmail.com
