# hold RGB565 pixels in a framebuf and use DMA to push them out over SPI to the TFT LCD XYZ LMNOPQRSTUV
import framebuf
import board_config as bc
from screen.pio_spi import PIO_SPI
from machine import Pin, mem32
import time
import rp2
import screen.st7789v_definitions as defs


def color565(r, g, b):
    return (r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3


class ST7789V:
    def __init__(
        self,
        cs=bc.DISPLAY_CS_PIN,
        dc=bc.DISPLAY_DC_PIN,
        clk=bc.DISPLAY_SCK_PIN,
        mosi=bc.DISPLAY_DO_PIN,
        backlight=bc.DISPLAY_BL_PIN,
    ):
        #
        self.frame_buf_bytes = bc.SCREEN_HEIGHT * bc.SCREEN_WIDTH * 2
        buf = bytearray(self.frame_buf_bytes)
        self.frame_buf = framebuf.FrameBuffer(
            buf, bc.SCREEN_WIDTH, bc.SCREEN_HEIGHT, framebuf.RGB565
        )
        self.frame_buf.fill(defs.BLACK)

        self.spi = PIO_SPI(sck=clk, mosi=mosi)

        self.cs = Pin(cs, Pin.OUT)
        self.dc = Pin(dc, Pin.OUT)
        self.backlight = Pin(backlight, Pin.OUT)

        self.setup_display()
        self.setup_DMA()
        self.framerate_counter = time.time_ns()
        self.fps = 0
        # draw a frame to kick off the DMA and it will run itself after this
        self.draw_frame()

    def setup_display(self):
        for cmd, data, delay in defs._ST7789_INIT_CMDS:
            self.send_command(cmd)
            self.send_argument(data)
            time.sleep_ms(delay)
        self.backlight.on()

    def setup_DMA(self):
        mem32[bc.DISPLAY_DMA_ABORT_ADDRESS] = (
            0x1  # aborting the channel seems to help restart DMA without a full power cycle
        )
        while mem32[bc.DISPLAY_DMA_ABORT_ADDRESS] != 0:
            continue
        self.dma1 = rp2.DMA()
        self.dma1_ctrl = self.dma1.pack_ctrl(
            size=0,
            inc_write=False,
            irq_quiet=False,
            # chain_to=self.dma2.channel,
            treq_sel=bc.DISPLAY_REQ_SEL,
            bswap=True,
        )

        self.dma1.irq(self.draw_frame)

    # this is attached to an interrupt that fires every time the screen finishes drawing
    # TODO: hook it up to a second DMA channel so it will run without any CPU intervention
    def draw_frame(self, *args):
        self.cs.off()
        # potentially comment this out if you want to eke out a tiny bit more performance
        oldtime = self.framerate_counter
        self.framerate_counter = time.time_ns()
        if not self.framerate_counter == oldtime:
            self.fps = 1_000_000_000 / (self.framerate_counter - oldtime)
        # print(f"{self.fps} fps")
        # Put the next pixel at the beginning of the screen's display RAM
        self.send_command(defs._ST7789_RAMWR)
        self.send_argument(
            b"\x00"
        )  # need to send 1 byte of nothing so the 2 byte colors are offset correctly, LMAO
        self.cs.off()
        self.dma1.config(
            read=self.frame_buf,
            write=self.spi.display_machine,
            count=self.frame_buf_bytes,
            ctrl=self.dma1_ctrl,
            trigger=True,
        )

    def send_command(self, cmd):
        # print(f"Sending {cmd}")
        self.cs.off()
        self.dc.off()
        self.spi.write(cmd)
        self.dc.on()
        self.cs.on()
        # pass

    def send_argument(self, data):
        # print(f"Sending {data}")

        self.cs.off()
        self.dc.on()  # just in case
        self.spi.write(data)
        self.cs.on()

    # # these are just convenience methods so I could test with the same API in the other driver, they basically forward arguments to the framebuf
    # def fill(self, color):
    #     self.frame_buf.fill(color)
    #     # self.frame_buf.text("???", 10, 10, MAGENTA)

    # def fill_circle(self, x, y, r, color):
    #     self.frame_buf.ellipse(x, y, r, r, color, True)

    # def pixel(self, x, y, color):
    #     self.frame_buf.pixel(x, y, color)
