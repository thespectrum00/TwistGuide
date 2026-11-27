# Minimal MPU6050 driver (the motion chip on the GY-87 board).
# Only the accelerometer and gyroscope are used.
import struct

ADDR = 0x68
_PWR_MGMT_1 = 0x6B
_SMPLRT_DIV = 0x19
_CONFIG = 0x1A
_GYRO_CONFIG = 0x1B
_ACCEL_CONFIG = 0x1C
_ACCEL_XOUT_H = 0x3B
_WHO_AM_I = 0x75

_ACCEL_LSB_PER_G = 16384.0      # +/-2 g range
_GYRO_LSB_PER_DPS = 32.8        # +/-1000 degrees per second range


class MPU6050:
    def __init__(self, i2c, addr=ADDR):
        self.i2c = i2c
        self.addr = addr
        self._buf = bytearray(14)
        self.bias = [0.0, 0.0, 0.0]
        self._write(_PWR_MGMT_1, 0x01)     # wake up, use the gyro clock
        self._write(_CONFIG, 0x03)         # built-in low-pass filter, about 44 Hz: rejects motor buzz
        self._write(_SMPLRT_DIV, 0x04)     # 200 samples a second inside the chip
        self._write(_GYRO_CONFIG, 0x10)    # +/-1000 degrees per second
        self._write(_ACCEL_CONFIG, 0x00)   # +/-2 g

    def _write(self, reg, value):
        self.i2c.writeto_mem(self.addr, reg, bytes([value]))

    def who_am_i(self):
        return self.i2c.readfrom_mem(self.addr, _WHO_AM_I, 1)[0]

    def read(self):
        """Return (ax, ay, az) in g and (gx, gy, gz) in degrees per second."""
        self.i2c.readfrom_mem_into(self.addr, _ACCEL_XOUT_H, self._buf)
        ax, ay, az, _t, gx, gy, gz = struct.unpack(">hhhhhhh", self._buf)
        b = self.bias
        return (
            ax / _ACCEL_LSB_PER_G,
            ay / _ACCEL_LSB_PER_G,
            az / _ACCEL_LSB_PER_G,
            gx / _GYRO_LSB_PER_DPS - b[0],
            gy / _GYRO_LSB_PER_DPS - b[1],
            gz / _GYRO_LSB_PER_DPS - b[2],
        )

    def calibrate_gyro(self, samples=200, delay_ms=5, sleep_ms=None):
        """Average the gyro while the band is held still, and remove that offset."""
        self.bias = [0.0, 0.0, 0.0]
        sx = sy = sz = 0.0
        for _ in range(samples):
            _ax, _ay, _az, gx, gy, gz = self.read()
            sx += gx
            sy += gy
            sz += gz
            if sleep_ms:
                sleep_ms(delay_ms)
        self.bias = [sx / samples, sy / samples, sz / samples]
        return self.bias
