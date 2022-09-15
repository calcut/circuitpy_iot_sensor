import time
import alarm
from circuitpy_mcu.mcu import Mcu
from circuitpy_mcu.ota_bootloader import reset, enable_watchdog

import adafruit_htu31d
import analogio
import board
from adafruit_lc709203f import LC709203F, PackSize

# scheduling and event/error handling libs
from watchdog import WatchDogTimeout
import supervisor
import microcontroller
import adafruit_logging as logging
import traceback

__version__ = "1.0.0-rc1"
__repo__ = "https://github.com/calcut/circuitpy-iot_sensor"
__filename__ = "iot_sensor.py"

# Set AIO = True to use Wifi and Adafruit IO connection
# secrets.py file needs to be setup appropriately
AIO = True
# AIO = False
AIO_GROUP = 'greenhouse'

def main():

    # Optional list of expected I2C devices and addresses
    # Maybe useful for automatic configuration in future
    i2c_dict = {
        '0x0B' : 'Battery Monitor LC709203', # Built into ESP32S2 feather 
        '0x40' : 'Temp/Humidity HTU31D',
        '0x41' : 'Temp/Humidity HTU31D',
    }

    # instantiate the MCU helper class to set up the system
    mcu = Mcu()

    # Choose minimum logging level to process
    mcu.log.setLevel(logging.DEBUG) #i.e. ignore DEBUG messages

    # instantiate i2c devices
    try:
        htu1 = adafruit_htu31d.HTU31D(mcu.i2c, address=0x40)
        htu1.heater = False
        mcu.log.info(f'found HTU31D at 0x40')

    except Exception as e:
        mcu.handle_exception(e)
        mcu.pixel[0] = mcu.pixel.RED

    try:
        htu2 = adafruit_htu31d.HTU31D(mcu.i2c, address=0x41)
        htu2.heater = False
        mcu.log.info(f'found HTU31D at 0x41')

    except Exception as e:
        mcu.handle_exception(e)
        mcu.pixel[0] = mcu.pixel.RED
    
    
    soil_sensor = analogio.AnalogIn(board.A0)
    battery_monitor = LC709203F(mcu.i2c)
    battery_monitor.pack_size = PackSize.MAH1000

    if AIO:
        mcu.wifi.connect()
        mcu.aio_setup(aio_group=f'{AIO_GROUP}-{mcu.id}')
        mcu.aio.log.setLevel(logging.DEBUG) #i.e. ignore DEBUG messages

    def deepsleep(duration):
        # Create a an alarm that will trigger 20 seconds from now.
        time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + duration)
        mcu.log.warning(f'about to deep sleep for {duration}s')
        mcu.i2c_power_off()
        mcu.led.value = False
        # Exit the program, and then deep sleep until the alarm wakes us.
        alarm.exit_and_deep_sleep_until_alarms(time_alarm)


    while True:
        mcu.watchdog_feed()
        
        feeds = {}
        feeds['battery-voltage'] = round(battery_monitor.cell_voltage, 3)
        feeds['battery-percent'] = round(battery_monitor.cell_percent, 3)
        feeds['inside-temperature'] = round(htu1.temperature, 2)
        feeds['inside-humidity'] = round(htu1.relative_humidity, 2)
        feeds['soil'] = 100* soil_sensor.value // 65536
        feeds['outside-temperature'] = round(htu2.temperature, 2)
        feeds['outside-humidity'] = round(htu2.relative_humidity, 2)
        if AIO:
            mcu.aio.get('ota')
            mcu.aio_sync(data_dict=feeds, publish_interval=30)
            for feed_id in mcu.aio.updated_feeds.keys():
                payload = mcu.aio.updated_feeds.pop(feed_id)
                print(f'parsing {feed_id=} {payload=}')

                if feed_id == 'ota':
                    if payload != __version__:
                        mcu.log.warning('New OTA Version, updating now')
                        code = '/circuitpy_iot_sensor/get_ota.py'
                        supervisor.set_next_code_file(code, reload_on_success=False)
                        supervisor.reload()
                    else:
                        deepsleep(10) #15 minutes
            time.sleep(1)
    

if __name__ == "__main__":
    try:
        enable_watchdog(timeout=60)
        main()
    except KeyboardInterrupt:
        print('Code Stopped by Keyboard Interrupt')

    except Exception as e:
        print(f'Code stopped by unhandled exception:')
        reset(e)