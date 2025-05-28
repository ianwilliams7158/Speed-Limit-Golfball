# boot.py
# This script runs automatically on ESP32 boot.
# It sets up necessary paths and then imports main.py.

import gc
import machine
import os

# Mount SD card first (if not already mounted in main.py)
# If your ESP32's SD card reader uses default pins, this is a common setup.
# Adjust pins if necessary for your specific board.
# Most ESP32 dev boards use:
# CMD: GPIO15, CLK: GPIO14, DAT0: GPIO2, CS: GPIO13 (or another suitable GPIO)
try:
    sd_spi = machine.SPI(
        1, # HSPI
        baudrate=10000000,
        polarity=0,
        phase=0,
        sck=machine.Pin(14),
        mosi=machine.Pin(15),
        miso=machine.Pin(2)
    )
    sd_cs = machine.Pin(13, machine.Pin.OUT)
    os.mount(sd_spi, sd_cs, "/sd")
    sys.path.append('/sd') # Add SD card root to MicroPython's path
    print("SD card mounted successfully in boot.py and added to path.")
except Exception as e:
    print(f"Error mounting SD card in boot.py: {e}")
    # Consider adding an LCD message here if the LCD is initialized early enough
    # or if this error is critical to display.

# Garbage collection to free up memory before main app
gc.collect()

# Now import and run main.py from the SD card
# The main.py will handle further setup and the asyncio loop.
try:
    import main
except Exception as e:
    print(f"Error starting main.py: {e}")
    # You might want to display an error on the LCD here if main fails to load.