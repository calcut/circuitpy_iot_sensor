# If CIRCUITPY drive is writable (configured in boot.py) this will update code files over-the-air
from circuitpy_mcu.ota_bootloader import Bootloader
import supervisor

url = 'https://raw.githubusercontent.com/calcut/circuitpy_iot_sensor/main/ota_list.py'
bl = Bootloader(url)

supervisor.reload()