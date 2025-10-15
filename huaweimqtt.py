# version 1.8 vom 15.10.25
import time
import asyncio
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import configparser
import numpy as np
import json
from huawei_solar import HuaweiSolarBridge



def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Verbunden mit dem Broker")
    else:
        print(f"Verbindung fehlgeschlagen, Rückgabewert={rc}")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Unerwartete Trennung, versuche erneut zu verbinden")
        try_reconnect(client)

def try_reconnect(client):
    max_reconnect_attempts = 3
    current_attempt = 0
    while not client.is_connected() and current_attempt < max_reconnect_attempts:
        try:
            print("Versuche erneut zu verbinden...")
            client.reconnect()
            current_attempt += 1
            time.sleep(2)
        except Exception as e:
            print(f"Fehler beim erneuten Verbinden: {e}")
            break



async def huaweiReadValues(bridge, topic_mapping, mqtthost, mqttclient, registers):

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    # Setzen Sie hier weitere Konfigurationsoptionen für den Client

    client.connect(mqtthost, 1883, 60)



    if bridge is None:
        bridge = await HuaweiSolarBridge.create(host="192.168.200.1", port=6607)
        print("Verbindungsbruecke herstellen")

    while True:
        try:
            register_values = {}
            array_currents_grid = np.array([])
            array_voltages_grid = np.array([])
            array_powers_grid = np.array([])

            for register in registers:
                try:
                    result = await bridge.client.get(register)

                    message = 0 if result[0] in [None, 0] else result[0]
                    mqtttopic = None

                    if register == 'input_power':
                            mqtttopic = f"openWB/set/mqtt/pv/{pvnumber}/get/power"
                            message = result[0] * -1
                          #  print(f"Eingangsleistung: {result[0]}")

                    elif register == 'daily_yield_energy':
                            mqtttopic = f"openWB/set/mqtt/pv/{pvnumber}/get/exported"
                            message = result[0] * 1000
                          #  print(f"Taegliche Ertragsenergie: {result[0]}")

                    elif register == "storage_state_of_capacity":
                            mqtttopic = f"openWB/set/mqtt/bat/{bat_number}/get/soc"
                            message = result[0]

                    elif register == "storage_charge_discharge_power":
                            mqtttopic = f"openWB/set/mqtt/bat/{bat_number}/get/power"
                            message = result[0]

                    elif register == "storage_current_day_charge_capacity":
                            mqtttopic = f"openWB/set/mqtt/bat/{bat_number}/get/imported"
                            message = result[0] * 1000

                    elif register == "storage_current_day_discharge_capacity":
                            mqtttopic = f"openWB/set/mqtt/bat/{bat_number}/get/exported"
                            message = result[0] * 1000

                    elif register == "power_meter_active_power":
                            mqtttopic = f"openWB/set/mqtt/counter/{counter_number}/get/power"
                            message = result[0]  * -1

                    elif register == "grid_frequency":
                            mqtttopic = f"openWB/set/mqtt/counter/{counter_number}/get/frequency"
                            message = result[0]

                    elif register == "grid_accumulated_energy":
                            mqtttopic = f"openWB/set/mqtt/counter/{counter_number}/get/imported"
                            message = result[0] * 1000

                    elif register == "grid_exported_energy":
                            mqtttopic = f"openWB/set/mqtt/counter/{counter_number}/get/exported"
                            message = result[0] * 1000
                        # Handle other registers (in this case, the grid currents)
                        # Append numerical grid currents to the array
                    elif register in ['active_grid_A_current', 'active_grid_B_current', 'active_grid_C_current']:
                            mqtttopic = f"openWB/set/mqtt/counter/{counter_number}/get/currents"
                            array_currents_grid = np.append(array_currents_grid, result[0] * -1)

                    elif register in ['grid_A_voltage', 'grid_B_voltage', 'grid_C_voltage']:
                            mqtttopic = f"openWB/set/mqtt/counter/{counter_number}/get/voltages"
                            array_voltages_grid = np.append(array_voltages_grid, result[0])

                    elif register in ['active_grid_A_power', 'active_grid_B_power', 'active_grid_C_power']:
                            mqtttopic = f"openWB/set/mqtt/ounter/{counter_number}/get/powers"
                            array_powers_grid = np.append(array_powers_grid, result[0] * -1)

                    if mqtttopic:
                            register_values[register] = message
                except:
                        pass

            if array_currents_grid.size > 0:
                mqtttopic = f"openWB/set/mqtt/counter/{counter_number}/get/currents"
                payload_json = json.dumps(array_currents_grid.tolist())  # Convert to JSON string
                publish.single(mqtttopic, payload=payload_json, qos=0, retain=False, hostname=mqtthost, client_id=mqttclient)

            if array_voltages_grid.size > 0:
                mqtttopic = f"openWB/set/mqtt/counter/{counter_number}/get/voltages"
                payload_json = json.dumps(array_voltages_grid.tolist())  # Convert to JSON string
                publish.single(mqtttopic, payload=payload_json, qos=0, retain=False, hostname=mqtthost, client_id=mqttclient)
            if array_powers_grid.size > 0:
                mqtttopic = f"openWB/set/mqtt/counter/{counter_number}/get/powers"
                payload_json = json.dumps(array_powers_grid.tolist())  # Convert to JSON string
                publish.single(mqtttopic, payload=payload_json, qos=0, retain=False, hostname=mqtthost, client_id=mqttclient)

            for register, value in register_values.items():
                mqtttopic = topic_mapping.get(register)
                if mqtttopic:
                    try:
                        publish.single(mqtttopic, payload=value, qos=0, retain=False, hostname=mqtthost,
                                       client_id=mqttclient)
                    except:
                        pass

            await asyncio.sleep(10)

        except KeyboardInterrupt:
            await bridge.stop()
            break

    await bridge.stop()

def read_config():
    config = configparser.ConfigParser()
    config.read('/home/pi/huawei_bridge_openwb/config.ini')
    return config

config = read_config()
mqtthost = config['MQTT']['host']
pvnumber = config.getint('pvnumber', 'value')
counter_number = config.getint('counternumber', 'value')
bat_number = config.getint('batnumber', 'value')

# Dictionary MQTT-Topic Mapping
topic_mapping = {
    'input_power': f"openWB/set/mqtt/pv/{pvnumber}/get/power",
    'daily_yield_energy': f"openWB/set/mqtt/pv/{pvnumber}/get/exported",
    'grid_accumulated_energy': f"openWB/set/mqtt/counter/{counter_number}/get/imported",
    'power_meter_active_power': f"openWB/set/mqtt/counter/{counter_number}/get/power",
    'grid_frequency': f"openWB/set/mqtt/counter/{counter_number}/get/frequency",
    'grid_exported_energy': f"openWB/set/mqtt/counter/{counter_number}/get/exported",
    'storage_charge_discharge_power': f"openWB/set/mqtt/bat/{bat_number}/get/power",
    'storage_current_day_charge_capacity': f"openWB/set/mqtt/bat/{bat_number}/get/imported",
    'storage_current_day_discharge_capacity': f"openWB/set/mqtt/bat/{bat_number}/get/exported",
    'storage_state_of_capacity': f"openWB/set/mqtt/bat/{bat_number}/get/soc",
}

# Registernames
registers = ['input_power', 'daily_yield_energy', 'grid_accumulated_energy', 'power_meter_active_power', 'grid_frequency',
'grid_exported_energy', 'storage_charge_discharge_power', 'storage_current_day_charge_capacity', 'storage_current_day_discharge_capacity', 'storage_state_of_capacity',
'active_grid_A_power', 'active_grid_B_power', 'active_grid_C_power', 'grid_A_voltage', 'grid_B_voltage', 'grid_C_voltage', 'active_grid_A_current', 'active_grid_B_current', 'active_grid_C_current',
]

bridge = None
loop = asyncio.get_event_loop()
loop.run_until_complete(huaweiReadValues(bridge, topic_mapping, mqtthost, "PVImporter", registers))
