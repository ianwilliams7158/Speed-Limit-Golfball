import uasyncio as asyncio
import machine
import os
import json
import math
import sys

# Import custom modules
import gps
import waveshare_lcd
import unit_toggle
import vga2_16x32 # This needs to be correctly implemented for font data

# --- Hardware Pin Definitions (Adjust these based on your wiring!) ---
# LCD SPI Pins (Waveshare 1.28 Round LCD)
LCD_SCK = machine.Pin(18) # Example: Adjust if different
LCD_MOSI = machine.Pin(19) # Example: Adjust if different
LCD_MISO = machine.Pin(23) # MISO might not be used for ST7789, but define if needed
LCD_CS = machine.Pin(5)   # Chip Select
LCD_DC = machine.Pin(16)  # Data/Command
LCD_RST = machine.Pin(20) # Reset Pin (check your board's actual available pins)
LCD_BL = machine.Pin(4)   # Backlight Pin (optional, but good to have)

# Touch I2C Pins (XPT2046 on Waveshare 1.28 Round LCD)
TOUCH_SDA = machine.Pin(21) # Example: Adjust if different
TOUCH_SCL = machine.Pin(22) # Example: Adjust if different
TOUCH_CS = machine.Pin(15)  # Touch Chip Select (often different from LCD CS)
TOUCH_IRQ = machine.Pin(27) # Touch Interrupt Pin (optional, but good for efficiency)

# GPS UART Pins (e.g., NEO-8M)
GPS_TX = machine.Pin(17) # ESP32 TX connected to GPS RX
GPS_RX = machine.Pin(16) # ESP32 RX connected to GPS TX
GPS_UART_ID = 2          # Use UART2

# --- Constants ---
SPEED_LIMIT_FILE = 'speed_limits.json'
UPDATE_INTERVAL_MS = 2000 # 2-second update cycle
MAX_DISTANCE_METERS = 150 # Max distance to consider a speed limit zone

# --- Global Variables ---
speed_limits_data = None
current_unit_is_mph = True # True for MPH, False for KPH

# --- Haversine Formula for Distance Calculation ---
# https://en.wikipedia.org/wiki/Haversine_formula
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000 # Radius of Earth in meters

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance

# --- Main Application Logic ---
async def main_loop():
    global current_unit_is_mph, speed_limits_data

    print("Initializing components...")

    # Initialize LCD
    lcd = waveshare_lcd.WaveshareLCD(
        spi_sck=LCD_SCK, spi_mosi=LCD_MOSI, spi_miso=LCD_MISO,
        cs=LCD_CS, dc=LCD_DC, rst=LCD_RST, bl=LCD_BL,
        font=vga2_16x32 # Pass the font module
    )
    lcd.show_message("Booting...")
    await asyncio.sleep_ms(500)

    # Initialize GPS
    gps_module = gps.GPS(uart_id=GPS_UART_ID, tx_pin=GPS_TX, rx_pin=GPS_RX)
    asyncio.create_task(gps_module.update()) # Start async GPS reading

    # Initialize Touch Unit Toggle
    # The XPT2046 driver often needs SPI, but the Waveshare module usually handles this internally for touch
    # and provides a way to get touch coordinates. unit_toggle needs to interpret these.
    # We'll assume unit_toggle.py handles the XPT2046 setup via the LCD's I2C or SPI interface for touch.
    touch_toggle = unit_toggle.UnitToggle(
        touch_cs_pin=TOUCH_CS, touch_irq_pin=TOUCH_IRQ,
        spi_sck=LCD_SCK, spi_mosi=LCD_MOSI, spi_miso=LCD_MISO, # Often touch shares SPI bus with LCD
        spi_bus=lcd.spi # Pass the initialized SPI bus if available, or create a new one
    )
    # Start async touch monitoring
    asyncio.create_task(touch_toggle.monitor_touch_async())

    # Load speed limits data
    print(f"Attempting to load {SPEED_LIMIT_FILE}...")
    try:
        with open(SPEED_LIMIT_FILE, 'r') as f:
            speed_limits_data = json.load(f)
        print(f"Successfully loaded {len(speed_limits_data['features'])} speed limit zones.")
    except OSError as e:
        print(f"Error loading {SPEED_LIMIT_FILE}: {e}")
        lcd.show_message("SD Error!")
        sys.exit() # Halt if essential data cannot be loaded
    except json.JSONDecodeError as e:
        print(f"Error parsing {SPEED_LIMIT_FILE}: {e}")
        lcd.show_message("JSON Error!")
        sys.exit()

    print("Starting main application loop...")
    lcd.show_message("Waiting for GPS...")

    while True:
        # Check for unit toggle
        if touch_toggle.get_toggle_status():
            current_unit_is_mph = not current_unit_is_mph
            print(f"Unit toggled to: {'MPH' if current_unit_is_mph else 'KPH'}")
            touch_toggle.reset_toggle_status() # Reset after handling

        lat, lon = gps_module.get_coordinates()

        if lat is not None and lon is not None:
            closest_speed_limit = None
            min_distance = float('inf')

            for feature in speed_limits_data['features']:
                zone_coords = feature['geometry']['coordinates']
                zone_lon, zone_lat = zone_coords[0], zone_coords[1] # GeoJSON is [lon, lat]

                distance = haversine_distance(lat, lon, zone_lat, zone_lon)

                if distance <= MAX_DISTANCE_METERS and distance < min_distance:
                    min_distance = distance
                    closest_speed_limit = feature['properties']['speed_mph']

            if closest_speed_limit is not None:
                display_speed = closest_speed_limit
                display_unit = "MPH"
                if not current_unit_is_mph:
                    display_speed = round(closest_speed_limit * 1.60934) # Convert MPH to KPH
                    display_unit = "KPH"
                lcd.show_speed_limit(display_speed, display_unit)
                print(f"GPS: ({lat:.4f}, {lon:.4f}), Nearest limit: {closest_speed_limit} MPH ({min_distance:.2f}m)")
            else:
                lcd.show_message("No limit found")
                print(f"GPS: ({lat:.4f}, {lon:.4f}), No speed limit found within {MAX_DISTANCE_METERS}m.")
        else:
            lcd.show_message("Waiting for GPS...")
            print("No GPS fix yet.")

        await asyncio.sleep_ms(UPDATE_INTERVAL_MS)

# --- Start the application ---
if __name__ == '__main__':
    try:
        # Mount SD card (assuming it's connected to default ESP32 pins, check your board)
        # Typically, ESP32 SD card reader pins are:
        # CMD (MOSI): GPIO15
        # CLK (SCK): GPIO14
        # DAT0 (MISO): GPIO2
        # CS: GPIO13 (or another suitable GPIO)
        sd_spi = machine.SPI(
            1, # HSPI on ESP32
            baudrate=10000000,
            polarity=0,
            phase=0,
            sck=machine.Pin(14),
            mosi=machine.Pin(15),
            miso=machine.Pin(2)
        )
        sd_cs = machine.Pin(13, machine.Pin.OUT) # Example CS pin, adjust as needed

        os.mount(sd_spi, sd_cs, "/sd")
        os.chdir("/sd") # Change current directory to SD card root
        print("SD card mounted successfully.")
    except Exception as e:
        print(f"Error mounting SD card: {e}")
        # If SD card fails, the system might not be able to load speed_limits.json
        # You might want to display an error on LCD if possible here too.
        # However, LCD init needs to happen before this.
        # For this example, we assume LCD can show "SD Error!" later.

    asyncio.run(main_loop())