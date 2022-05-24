import time
import alarm
from circuitpy_mcu.mcu import Mcu
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

__version__ = "0.0.0-auto.0"
# __repo__ = "https://github.com/calcut/circuitpy-septic_tank"
# __filename__ = "septic_tank.py"

# Set AIO = True to use Wifi and Adafruit IO connection
# secrets.py file needs to be setup appropriately
# AIO = True
AIO = False

def main():

    # Optional list of expected I2C devices and addresses
    # Maybe useful for automatic configuration in future
    i2c_dict = {
        '0x0B' : 'Battery Monitor LC709203', # Built into ESP32S2 feather 
        '0x40' : 'Temp/Humidity HTU31D',
        '0x41' : 'Temp/Humidity HTU31D',
        # '0x68' : 'Realtime Clock PCF8523', # On Adalogger Featherwing
        # '0x72' : 'Sparkfun LCD Display',
        # '0x77' : 'Temp/Humidity/Pressure BME280' # Built into some ESP32S2 feathers 
    }

    # instantiate the MCU helper class to set up the system
    mcu = Mcu()

    # Choose minimum logging level to process
    mcu.log.setLevel(logging.INFO) #i.e. ignore DEBUG messages

    # Check what devices are present on the i2c bus
    # mcu.i2c_identify(i2c_dict)

    # instantiate i2c devices
    try:
        htu1 = adafruit_htu31d.HTU31D(mcu.i2c, address=0x40)
        htu1.heater = False
        mcu.log.info(f'found HTU31D at 0x40')

    except Exception as e:
        mcu.log_exception(e)
        mcu.pixel[0] = mcu.pixel.RED

    try:
        htu2 = adafruit_htu31d.HTU31D(mcu.i2c, address=0x41)
        htu2.heater = False
        mcu.log.info(f'found HTU31D at 0x41')

    except Exception as e:
        mcu.log_exception(e)
        mcu.pixel[0] = mcu.pixel.RED
    # mcu.attach_sdcard()
    # mcu.archive_file('log.txt')
    # mcu.archive_file('data.txt')
    soil_sensor = analogio.AnalogIn(board.A0)
    battery_monitor = LC709203F(mcu.i2c)
    battery_monitor.pack_size = PackSize.MAH1000

    if AIO:
        mcu.wifi_connect()
        mcu.aio_setup(log_feed=None)

    def deepsleep(duration):
        # Create a an alarm that will trigger 20 seconds from now.
        time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + duration)
        mcu.log.warning(f'about to deep sleep for {duration}s')
        mcu.i2c_power_off()
        # Exit the program, and then deep sleep until the alarm wakes us.
        alarm.exit_and_deep_sleep_until_alarms(time_alarm)

    def publish_feeds():
        # AIO limits to 30 data points per minute in the free version
        # Set publish interval accordingly
        feeds = {}
        if mcu.aio_connected:
            feeds['greenhouse.temperature'] = round(htu1.temperature, 2)
            feeds['greenhouse.humidity'] = round(htu1.relative_humidity, 2)
            feeds['greenhouse.soil'] = 100* soil_sensor.value // 65536
            feeds['outside.temperature'] = round(htu2.temperature, 2)
            feeds['outside.humidity'] = round(htu2.relative_humidity, 2)
            mcu.aio_send(feeds)


    while True:
        print(f'{battery_monitor.cell_percent=}')
        print(f'{battery_monitor.cell_voltage=}')
        print(f'{100* soil_sensor.value // 65536}')
        time.sleep(1)
        mcu.watchdog.feed()
    mcu.aio_receive()

    publish_feeds()
    deepsleep(900)   #15 minutes

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('Code Stopped by Keyboard Interrupt')
        # May want to add code to stop gracefully here 
        # e.g. turn off relays or pumps
        
    except WatchDogTimeout:
        print('Code Stopped by WatchDog Timeout!')
        # supervisor.reload()
        # NB, sometimes soft reset is not enough! need to do hard reset here
        print('Performing hard reset in 15s')
        time.sleep(15)
        microcontroller.reset()

    except Exception as e:
        print(f'Code stopped by unhandled exception:')
        print(traceback.format_exception(None, e, e.__traceback__))
        # Can we log here?
        print('Performing a hard reset in 15s')
        time.sleep(15) #Make sure this is shorter than watchdog timeout
        # supervisor.reload()
        microcontroller.reset()