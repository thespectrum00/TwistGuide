# Messages between the band and the phone. Plain text, one message per packet.
#
# Band to phone, 50 times a second:
#   A,<milliseconds>,<angle in degrees>,<button 0 or 1>,<on target 0 or 1>
#
# Phone to band:
#   T,<target degrees>,<tolerance degrees>,<haptics 0 or 1>   start a trial
#   S                                                          stop guiding
#   Z                                                          set the current wrist position as zero


def angle_message(ms, angle, button, on_target):
    return "A,%d,%.2f,%d,%d\n" % (ms, angle, 1 if button else 0, 1 if on_target else 0)


def parse_command(data):
    """Return ("T", target, tolerance, haptics_on), ("S",), ("Z",) or None if unreadable."""
    try:
        text = data.decode().strip() if isinstance(data, (bytes, bytearray)) else str(data).strip()
        parts = text.split(",")
        cmd = parts[0]
        if cmd == "T":
            haptics_on = True if len(parts) < 4 else parts[3].strip() == "1"
            return ("T", float(parts[1]), float(parts[2]), haptics_on)
        if cmd == "S":
            return ("S",)
        if cmd == "Z":
            return ("Z",)
    except (ValueError, IndexError):
        pass
    return None
