import machine
import st7789 # Requires this driver to be present on the device
import framebuf
import math
import utime

# Assume vga2_16x32 is correctly imported and contains font data
# from vga2_16x32 import vga2_16x32_font # This line assumes the font is directly callable

# Define colors
BLACK = st7789.BLACK
WHITE = st7789.WHITE
RED = st7789.RED

class WaveshareLCD:
    def __init__(self, spi_sck, spi_mosi, spi_miso, cs, dc, rst, bl, font):
        # Configure SPI for the display
        self.spi = machine.SPI(
            1, # HSPI on ESP32, typically
            baudrate=60_000_000, # High baudrate for fast drawing
            polarity=0,
            phase=0,
            sck=spi_sck,
            mosi=spi_mosi,
            miso=spi_miso # MISO usually not needed for ST7789 write-only
        )

        self.lcd = st7789.ST7789(
            self.spi,
            240, 240, # Width, Height
            reset=rst,
            cs=cs,
            dc=dc,
            backlight=bl,
            rotation=0 # Adjust rotation if needed (0, 90, 180, 270)
        )
        self.lcd.init()
        self.lcd.fill(BLACK) # Clear screen on boot

        self.font = font # The imported vga2_16x32 module
        self.width = self.lcd.width
        self.height = self.lcd.height
        self.center_x = self.width // 2
        self.center_y = self.height // 2

        print("Waveshare 1.28 LCD initialized.")

    def show_speed_limit(self, speed, unit):
        self.lcd.fill(BLACK) # Clear previous display

        # Draw the red circle outline (speed limit sign)
        # Center: (120, 120), Radius: e.g., 90
        radius = 90
        # Draw circle border
        for r_offset in range(3): # Draw a few rings for a thicker border
            self.lcd.circle(self.center_x, self.center_y, radius - r_offset, RED)

        # Draw inner white circle
        self.lcd.fill_circle(self.center_x, self.center_y, radius - 3, WHITE) # Fill inside the border

        # Display the speed number in black
        speed_str = str(speed)
        # The font character height is 32, width 16. For multiple digits, calculate total width.
        text_width = len(speed_str) * self.font.WIDTH # Assuming font module has WIDTH property
        text_height = self.font.HEIGHT # Assuming font module has HEIGHT property

        # Center the text
        text_x = self.center_x - (text_width // 2)
        text_y = self.center_y - (text_height // 2)

        self.lcd.text(self.font, speed_str, text_x, text_y, BLACK, WHITE) # Text color black, background white

        # Display units (MPH/KPH) below the speed number
        unit_text_y = self.center_y + (text_height // 2) + 5 # A bit below the number
        unit_text_width = len(unit) * 8 # Assuming a smaller default font for units, or use a specific unit font.
                                        # For simplicity, using a small font char width if not using custom.
                                        # If you want to use vga2_16x32 for units, adjust calculations.
                                        # For now, let's just use st7789's default text rendering.
        self.lcd.text(self.font, unit, self.center_x - (len(unit) * self.font.WIDTH // 2), unit_text_y, BLACK, WHITE) # Render unit text within the white circle

    def show_message(self, text):
        self.lcd.fill(BLACK) # Clear screen
        # Simple centering for messages
        text_width = len(text) * self.font.WIDTH
        text_height = self.font.HEIGHT
        x = self.center_x - (text_width // 2)
        y = self.center_y - (text_height // 2)
        self.lcd.text(self.font, text, x, y, WHITE, BLACK) # White text on black background