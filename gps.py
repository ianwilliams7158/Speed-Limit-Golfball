import uasyncio as asyncio
import machine
import utime

class GPS:
    def __init__(self, uart_id=2, tx_pin=17, rx_pin=16, baudrate=9600):
        self.uart = machine.UART(uart_id, baudrate=baudrate, tx=tx_pin, rx=rx_pin, timeout=100)
        self.latitude = None
        self.longitude = None
        self.has_fix = False
        print(f"GPS UART initialized on UART{uart_id}, TX={tx_pin}, RX={rx_pin}")

    async def update(self):
        """Asynchronously reads NMEA sentences and updates GPS coordinates."""
        print("Starting GPS update task...")
        while True:
            try:
                line = self.uart.readline()
                if line:
                    line = line.decode('utf-8').strip()
                    # print(f"GPS RAW: {line}") # Uncomment for debugging NMEA sentences
                    self._parse_nmea(line)
            except Exception as e:
                print(f"Error reading GPS data: {e}")
            await asyncio.sleep_ms(100) # Read every 100ms for responsiveness

    def _parse_nmea(self, nmea_sentence):
        """Parses a single NMEA sentence (GPGGA for coordinates)."""
        parts = nmea_sentence.split(',')
        if parts[0] == '$GPGGA' and len(parts) >= 10:
            try:
                # Check for GPS fix (part 6: 0=no fix, 1=GPS fix, 2=DGPS fix)
                fix_status = int(parts[6])
                if fix_status >= 1:
                    lat_str = parts[2]
                    lat_dir = parts[3]
                    lon_str = parts[4]
                    lon_dir = parts[5]

                    if lat_str and lon_str:
                        self.latitude = self._convert_nmea_latitude(lat_str, lat_dir)
                        self.longitude = self._convert_nmea_longitude(lon_str, lon_dir)
                        self.has_fix = True
                        # print(f"GPS Fix: Lat={self.latitude:.4f}, Lon={self.longitude:.4f}")
                    else:
                        self.has_fix = False
                        self.latitude = None
                        self.longitude = None
                else:
                    self.has_fix = False
                    self.latitude = None
                    self.longitude = None
            except (ValueError, IndexError) as e:
                # print(f"Error parsing GPGGA sentence: {nmea_sentence} - {e}")
                self.has_fix = False
                self.latitude = None
                self.longitude = None
        elif parts[0] == '$GPRMC' and len(parts) >= 10:
            # GPRMC also provides fix status and coordinates
            # This is an alternative/complementary NMEA sentence
            status = parts[2] # A=Active, V=Void
            if status == 'A':
                lat_str = parts[3]
                lat_dir = parts[4]
                lon_str = parts[5]
                lon_dir = parts[6]

                if lat_str and lon_str:
                    self.latitude = self._convert_nmea_latitude(lat_str, lat_dir)
                    self.longitude = self._convert_nmea_longitude(lon_str, lon_dir)
                    self.has_fix = True
                    # print(f"GPRMC Fix: Lat={self.latitude:.4f}, Lon={self.longitude:.4f}")
                else:
                    self.has_fix = False
                    self.latitude = None
                    self.longitude = None
            else:
                self.has_fix = False
                self.latitude = None
                self.longitude = None


    def _convert_nmea_latitude(self, nmea_lat, direction):
        """Converts NMEA latitude (DDMM.MMMM) to decimal degrees."""
        if not nmea_lat:
            return None
        try:
            dd = float(nmea_lat[0:2])
            mm = float(nmea_lat[2:])
            decimal_degrees = dd + (mm / 60)
            if direction == 'S':
                decimal_degrees *= -1
            return decimal_degrees
        except ValueError:
            return None

    def _convert_nmea_longitude(self, nmea_lon, direction):
        """Converts NMEA longitude (DDDMM.MMMM) to decimal degrees."""
        if not nmea_lon:
            return None
        try:
            ddd = float(nmea_lon[0:3])
            mm = float(nmea_lon[3:])
            decimal_degrees = ddd + (mm / 60)
            if direction == 'W':
                decimal_degrees *= -1
            return decimal_degrees
        except ValueError:
            return None

    def get_coordinates(self):
        """Returns (latitude, longitude) if a fix is available, else (None, None)."""
        if self.has_fix and self.latitude is not None and self.longitude is not None:
            return self.latitude, self.longitude
        return None, None