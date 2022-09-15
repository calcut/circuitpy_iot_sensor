
import supervisor
supervisor.disable_autoreload()

code = '/circuitpy_iot_sensor/iot_sensor.py'
supervisor.set_next_code_file(code, reload_on_success=False)
supervisor.reload()