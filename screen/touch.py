import board_config
from machine import Pin, SoftI2C


class Touchscreen:
    def __init__(self):
        self.i2c = SoftI2C(
            scl=Pin(board_config.TOUCH_I2C_SCL), sda=Pin(board_config.TOUCH_I2C_SDA)
        )
        self.x = self.y = self.z = 0
        self.addr = 0x48
        self.z_thr = 30

    def _read(self, cmd):
        buff = self.i2c.readfrom_mem(self.addr, cmd, 2)
        v = (buff[0] << 4) | (buff[1] >> 4)
        return v

    def update(self):
        self.z = self._read(0xE0)
        if self.z > self.z_thr:
            self.x = self._read(0xC0)
            self.y = self._read(0xD0)
            # print(f"touch x={self.x} y={self.y} z={self.z}")
        else:
            self.x = self.y = -1

    def get_one_touch_in_pixels(self, verbose=False):
        # print("getting a touch!")
        while True:
            self.update()
            # can be up to two touches
            if (self.x != -1 and self.x < 4090) or (self.x != -1 and self.y < 4090):
                if verbose:
                    print(f"{self.x}, {self.y}")
                return (self.pixel_x(), self.pixel_y())

    # todo: find a way to calibrate this
    def pixel_x(self):
        return round(0.089428 * self.x - 32.22)

    def pixel_y(self):
        return round(0.066934 * self.y - 17.75)
