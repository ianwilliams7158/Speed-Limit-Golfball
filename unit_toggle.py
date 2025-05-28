import machine
import utime
import uasyncio as asyncio
import xpt2046 # Requires this driver to be present on the device

class UnitToggle:
    def __init__(self, touch_cs_pin, touch_irq_pin, spi_sck, spi_mosi, spi_miso, spi_bus=None):
        self._toggle_status = False # True if unit needs to be toggled

        # Touch screen initialization (XPT2046)
        # The XPT2046 often shares the SPI bus with the display
        # You might need to create a dedicated SPI instance for it if the LCD's SPI isn't suitable,
        # or if the XPT2046 library requires its own instance.
        # For simplicity, assuming it can share or is configured separately.
        # Ensure the correct pins for XPT2046 are used here.

        if spi_bus:
            # If an existing SPI bus is passed (e.g., from LCD init)
            self.touch_spi = spi_bus
        else:
            # Otherwise, create a new SPI instance for touch
            self.touch_spi = machine.SPI(
                # Use a different SPI bus ID if the LCD uses 1 (HSPI)
                # Or ensure CS lines are correctly handled if sharing bus 1
                2, # VSPI on ESP32, typically
                baudrate=1_000_000, # Lower baudrate for touch
                polarity=0,
                phase=0,
                sck=spi_sck,
                mosi=spi_mosi,
                miso=spi_miso
            )

        self.touch_cs = machine.Pin(touch_cs_pin, machine.Pin.OUT)
        self.touch_irq = machine.Pin(touch_irq_pin, machine.Pin.IN, machine.Pin.PULL_UP) # IRQ pin for touch detection

        self.xpt = xpt2046.XPT2046(self.touch_spi, self.touch_cs, self.touch_irq)

        # Calibration values (adjust these for your specific touch screen)
        # These are highly dependent on your display and XPT2046 setup.
        # You'll likely need to run a calibration script to get these.
        # Example: x_min=300, x_max=3900, y_min=240, y_max=3800
        # self.xpt.calibrate(x_min, x_max, y_min, y_max)
        print("XPT2046 touch controller initialized.")

        self.last_touch_time = 0
        self.debounce_ms = 300 # Milliseconds for debouncing touch

    async def monitor_touch_async(self):
        """Asynchronously monitors touch input and sets toggle status."""
        print("Starting touch monitoring task...")
        while True:
            current_time = utime.ticks_ms()
            # The XPT2046 IRQ pin goes low when touched.
            # However, the xpt2046 driver often provides `is_pressed` or `get_touch`
            # For simplicity, we poll its state.
            if self.xpt.is_pressed: # Check if touch is detected
                if utime.ticks_diff(current_time, self.last_touch_time) > self.debounce_ms:
                    self._toggle_status = True
                    self.last_touch_time = current_time
                    # print("Touch detected!") # For debugging
            await asyncio.sleep_ms(50) # Poll every 50ms for responsiveness

    def get_toggle_status(self):
        """Returns True if a toggle event occurred since last check, then resets."""
        return_status = self._toggle_status
        # The main_loop will reset this after checking.
        # No, the main_loop should reset this *after* it processes the toggle.
        return return_status

    def reset_toggle_status(self):
        self._toggle_status = False