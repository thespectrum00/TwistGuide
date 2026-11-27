# Decides which motor should buzz, and when.
# Pure logic, no hardware: this file can be tested on a computer.
#
# Outside the target: one motor buzzes at a time, stepping around the wrist in the
# direction you should twist. The steps come faster as you get closer.
# On reaching the target: all four motors give one short click, then stay quiet.

try:
    from time import ticks_diff
except ImportError:          # running on a computer, not on the board
    def ticks_diff(a, b):
        return a - b

from twist import wrap180


class Guide:
    def __init__(self, n_motors=4, strength=52000, sweep_dir=1, pulse_ms=70,
                 far_step_ms=260, near_step_ms=110, far_deg=60.0,
                 click_ms=60, exit_margin=1.0):
        self.n = n_motors
        self.strength = strength
        self.sweep_dir = sweep_dir
        self.pulse_ms = pulse_ms
        self.far_step_ms = far_step_ms
        self.near_step_ms = near_step_ms
        self.far_deg = far_deg
        self.click_ms = click_ms
        self.exit_margin = exit_margin
        self.duty = [0] * n_motors
        self.target = None
        self.tol = 3.0
        self.inside = False
        self._index = 0
        self._step_at = None
        self._click_until = None

    def start(self, target_deg, tolerance_deg):
        self.target = target_deg
        self.tol = tolerance_deg
        self.inside = False
        self._step_at = None
        self._click_until = None

    def stop(self):
        self.target = None
        self.inside = False
        self._all(0)

    def _all(self, value):
        for i in range(self.n):
            self.duty[i] = value

    def step_interval(self, error_size):
        """Milliseconds between steps for a given error, in degrees."""
        if error_size >= self.far_deg:
            return self.far_step_ms
        span = self.far_deg - self.tol
        if span <= 0:
            return self.near_step_ms
        frac = (error_size - self.tol) / span
        if frac < 0:
            frac = 0
        return int(self.near_step_ms + (self.far_step_ms - self.near_step_ms) * frac)

    def update(self, now_ms, angle):
        """Call every loop. Returns the list of motor strengths (0 to 65535)."""
        if self.target is None:
            self._all(0)
            return self.duty

        error = wrap180(self.target - angle)
        size = abs(error)
        limit = self.tol + (self.exit_margin if self.inside else 0.0)

        if size <= limit:
            if not self.inside:
                self.inside = True
                self._click_until = now_ms + self.click_ms
            clicking = self._click_until is not None and ticks_diff(self._click_until, now_ms) > 0
            self._all(65535 if clicking else 0)
            return self.duty

        self.inside = False
        direction = 1 if error > 0 else -1
        if self._step_at is None:
            self._step_at = now_ms
        elif ticks_diff(now_ms, self._step_at) >= self.step_interval(size):
            self._index = (self._index + direction * self.sweep_dir) % self.n
            self._step_at = now_ms

        buzzing = ticks_diff(now_ms, self._step_at) < self.pulse_ms
        self._all(0)
        if buzzing:
            self.duty[self._index] = self.strength
        return self.duty
