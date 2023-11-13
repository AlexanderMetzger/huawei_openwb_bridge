# version 1.3 vom 20.08.23
import time
import asyncio
import paho.mqtt.publish as publish
import numpy as np
import json
import configparser
from huawei_solar import HuaweiSolarBridge, register_names as rn, register_values as rv

loop = asyncio.new_event_loop()

def read_mqtt_host():
    config = configparser.ConfigParser()
    config.read('/home/pi/huawei_bridge_openwb/config.ini')
    return config['MQTT']['host']

# Function to read the counter / PV / BAT number from the INI file
def read_counter_number():
    config = configparser.ConfigParser()
    config.read('/home/pi/huawei_bridge_openwb/config.ini')
    return config.getint('counternumber', 'value')

def read_bat_number():
    config = configparser.ConfigParser()
    config.read('/home/pi/huawei_bridge_openwb/config.ini')
    return config.getint('batnumber', 'value')

def read_pv_number():
    config = configparser.ConfigParser()
    config.read('/home/pi/huawei_bridge_openwb/config.ini')
    return config.getint('pvnumber', 'value')

# openWB IP:
mqttclient = "PVImporter"

# Dictionary to map register names to MQTT topics
topic_mapping = {
    'input_power': f"openWB/set/pv/{read_pv_number()}/get/power",
    'storage_state_of_capacity': f"openWB/set/bat/{read_bat_number()}/get/soc",
    'grid_accumulated_energy': f"openWB/set/counter/{read_counter_number()}/get/imported",
    'grid_exported_energy': f"openWB/set/counter/{read_counter_number()}/get/exported",
    'storage_charge_discharge_power': f"openWB/set/bat/{read_bat_number()}/get/power",
    'accumulated_yield_energy': f"openWB/set/pv/{read_pv_number()}/get/exported",
    #'daily_yield_energy': f"openWB/set/pv/{read_pv_number()}/get/exported",
    'storage_current_day_charge_capacity': f"openWB/set/bat/{read_bat_number()}/get/imported",
    'storage_current_day_discharge_capacity': f"openWB/set/bat/{read_bat_number()}/get/exported",
    'power_meter_active_power': f"openWB/set/counter/{read_counter_number()}/get/power",
    'grid_frequency': f"openWB/set/counter/{read_counter_number()}/get/frequency",
}

def publish2openWB(mqtttopic, message):
    publish.single(mqtttopic, payload=message, qos=0, retain=False, hostname=mqtthost, client_id=mqttclient)

async def huaweiReadValues(topic_mapping):
    bridge = await HuaweiSolarBridge.create(host="192.168.200.1", port=6607)

    # Register names
    registers_evu = ['grid_frequency', 'power_meter_active_power', 'active_grid_A_power',
    'active_grid_B_power', 'active_grid_C_power', 'grid_A_voltage', 'grid_B_voltage',
    'grid_C_voltage', 'active_grid_A_current', 'active_grid_B_current', 'active_grid_C_current',
    'grid_exported_energy', 'grid_accumulated_energy', 'active_power', 'grid_voltage']
    registers_wr = ['input_power', 'accumulated_yield_energy', 'active_power', 'daily_yield_energy']
    registers_bat = ['storage_state_of_capacity', 'storage_charge_discharge_power', 'storage_current_day_charge_capacity', 'storage_current_day_discharge_capacity']
    registers = registers_evu + registers_wr + registers_bat

    # Main Tasks:
    while True:
        try:
            if not bridge:
                bridge = await HuaweiSolarBridge.create(host="192.168.200.1", port=6607)

            # Dictionary to store the register values
            register_values = {}

            # Initialize an empty NumPy array for grid currents
            array_currents_grid = np.array([])
            # Initialize an empty NumPy array for grid voltages
            array_voltages_grid = np.array([])
            # Initialize an empty NumPy array for grid powers
            array_powers_grid = np.array([])

            for i in registers:
                try:
                    result = await bridge.client.get(i)

                    if result[0] is not None and result[0] != 0:
                        mqtttopic = False

                        if str(i) == "input_power":
                            mqtttopic = f"openWB/set/pv/{read_pv_number()}/get/power"
                            message = result[0] * -1

                        elif str(i) == "storage_state_of_capacity":
                            mqtttopic = f"openWB/set/bat/{read_bat_number()}/get/soc"
                            message = result[0]

                        elif str(i) == "grid_accumulated_energy":
                            mqtttopic = f"openWB/set/counter/{read_counter_number()}/get/imported"
                            message = result[0]

                        elif str(i) == "grid_exported_energy":
                            mqtttopic = f"openWB/set/counter/{read_counter_number()}/get/exported"
                            message = result[0]

                        elif str(i) == "storage_charge_discharge_power":
                            mqtttopic = f"openWB/set/bat/{read_bat_number()}/get/power"
                            message = result[0]

                        elif str(i) == "daily_yield_energy":
                            mqtttopic = f"openWB/set/pv/{read_pv_number()}/get/exported"
                            message = result[0] * 1000

                        elif str(i) == "storage_current_day_charge_capacity":
                            mqtttopic = f"openWB/set/bat/{read_bat_number()}/get/imported"
                            message = result[0] * 1000

                        elif str(i) == "storage_current_day_discharge_capacity":
                            mqtttopic = f"openWB/set/bat/{read_bat_number()}/get/exported"
                            message = result[0] * 1000

                        elif str(i) == "power_meter_active_power":
                            mqtttopic = f"openWB/set/counter/{read_counter_number()}/get/power"
                            message = result[0]  * -1

                        elif str(i) == "grid_frequency":
                            mqtttopic = f"openWB/set/counter/{read_counter_number()}/get/frequency"
                            message = result[0]

                        # Handle other registers (in this case, the grid currents)
                        # Append numerical grid currents to the array
                        elif i in ['active_grid_A_current', 'active_grid_B_current', 'active_grid_C_current']:
                            mqtttopic = f"openWB/set/counter/{read_counter_number()}/get/currents"
                            array_currents_grid = np.append(array_currents_grid, result[0] * -1)

                        # Handle other registers (in this case, the grid voltages)
                        # Append numerical grid voltages to the array
                        elif i in ['grid_A_voltage', 'grid_B_voltage', 'grid_C_voltage']:
                            mqtttopic = f"openWB/set/counter/{read_counter_number()}/get/voltages"
                            array_voltages_grid = np.append(array_voltages_grid, result[0])
                        # Append numerical grid powers to the array
                        elif i in ['active_grid_A_power', 'active_grid_B_power', 'active_grid_C_power']:
                            mqtttopic = f"openWB/set/counter/{read_counter_number()}/get/powers"
                            array_powers_grid = np.append(array_powers_grid, result[0] * -1)

                        if mqtttopic is not False:
                            register_values[i] = message

                except:
                    await bridge.stop()
                    bridge = False
                    pass

            # Publish the values to their respective topics
            for register, value in register_values.items():
                mqtttopic = topic_mapping.get(register)
                if mqtttopic:
                    try:
                        if register == "active_grid_currents":
                            # Publish the current values as an array
                            publish.single(mqtttopic, payload=value, qos=0, retain=False, hostname=mqtthost,
                                           client_id=mqttclient)
                        if register == "active_grid_voltages":
                            # Publish the voltage values as an array
                            publish.single(mqtttopic, payload=value, qos=0, retain=False, hostname=mqtthost,
                                           client_id=mqttclient)
                        if register == "active_grid_powers":
                            # Publish the voltage values as an array
                            publish.single(mqtttopic, payload=value, qos=0, retain=False, hostname=mqtthost,
                                           client_id=mqttclient)

                        else:
                            # Publish other values directly
                            publish.single(mqtttopic, payload=value, qos=0, retain=False, hostname=mqtthost,
                                           client_id=mqttclient)
                    except:
                        pass

            # Publish the grid currents as an array
            if array_currents_grid.size > 0:
                mqtttopic = f"openWB/set/counter/{read_counter_number()}/get/currents"
                payload_json = json.dumps(array_currents_grid.tolist())  # Convert to JSON string
                publish.single(mqtttopic, payload=payload_json, qos=0, retain=False, hostname=mqtthost, client_id=mqttclient)

            if array_voltages_grid.size > 0:
                mqtttopic = f"openWB/set/counter/{read_counter_number()}/get/voltages"
                payload_json = json.dumps(array_voltages_grid.tolist())  # Convert to JSON string
                publish.single(mqtttopic, payload=payload_json, qos=0, retain=False, hostname=mqtthost, client_id=mqttclient)
            if array_powers_grid.size > 0:
                mqtttopic = f"openWB/set/counter/{read_counter_number()}/get/powers"
                payload_json = json.dumps(array_powers_grid.tolist())  # Convert to JSON string
                publish.single(mqtttopic, payload=payload_json, qos=0, retain=False, hostname=mqtthost, client_id=mqttclient)

            time.sleep(10)

        except KeyboardInterrupt:
            await bridge.stop()
            break

    await bridge.stop()

mqtthost = read_mqtt_host()
counternumber = read_counter_number()
batnumber = read_bat_number()
pvnumber = read_pv_number()
loop.run_until_complete(huaweiReadValues(topic_mapping))
