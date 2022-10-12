import notecard
from notecard import hub
import notecard_pseudo_sensor

from circuitpy_mcu.mcu import Mcu
import time


mcu = Mcu()

# nCard = notecard.OpenI2C(mcu.i2c, 0, 0)
nCard = notecard.OpenI2C(mcu.i2c, 0, 0, debug=True)
sensor = notecard_pseudo_sensor.NotecardPseudoSensor(nCard)

productUID = "com.gmail.calum.cuthill:test1"
rsp = hub.set(nCard, productUID, mode="continuous", sync=True, host="-")

print(rsp) # {}

# Construct a JSON Object to add a Note to the Notecard
# req = {"req": "note.add"}
# req["body"] = {"temp": 99.9}

# rsp = nCard.Transaction(req)
# print(rsp)

while True:
    temp = sensor.temp()
    humidity = sensor.humidity()
    print("\nTemperature: %0.1f C" % temp)
    print("Humidity: %0.1f %%" % humidity)
    req = {"req": "note.add"}
    req["file"] = "sensors.qo"
    req["sync"] = True
    req["body"] = { "temp": temp, "humidity": humidity}
    rsp = nCard.Transaction(req)
    print(rsp)

    time.sleep(15)