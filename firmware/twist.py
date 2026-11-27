# Works out the wrist twist angle from gravity direction and turning speed.
# Pure maths, no hardware: this file can be tested on a computer.
import math


def wrap180(a):
    """Bring an angle into the range -180 to 180 degrees."""
    while a > 180.0:
        a -= 360.0
    while a <= -180.0:
        a += 360.0
    return a


class TwistFilter:
    """Blend gyro (smooth, drifts) with accelerometer (true, jittery).

    a_arm  : acceleration along the forearm, in g
    a_side : acceleration across the wrist, in g
    a_up   : acceleration out of the back of the wrist, in g
    rate   : turning speed about the forearm, in degrees per second
    """

    def __init__(self, alpha=0.98):
        self.alpha = alpha
        self.angle = 0.0     # absolute twist against gravity
        self.zero = 0.0      # set by the setup button
        self.ready = False

    def update(self, a_arm, a_side, a_up, rate, dt):
        across = math.sqrt(a_side * a_side + a_up * a_up)
        total = math.sqrt(a_arm * a_arm + across * across)
        # Trust gravity only when the forearm is roughly level and the hand is not being shaken.
        gravity_ok = across > 0.5 and 0.8 < total < 1.2

        if not self.ready:
            if gravity_ok:
                self.angle = math.degrees(math.atan2(a_side, a_up))
                self.ready = True
            return self.relative()

        predicted = self.angle + rate * dt
        if gravity_ok:
            measured = math.degrees(math.atan2(a_side, a_up))
            predicted += (1.0 - self.alpha) * wrap180(measured - predicted)
        self.angle = wrap180(predicted)
        return self.relative()

    def set_zero(self):
        self.zero = self.angle

    def relative(self):
        """Twist relative to the zero position, -180 to 180 degrees."""
        return wrap180(self.angle - self.zero)
