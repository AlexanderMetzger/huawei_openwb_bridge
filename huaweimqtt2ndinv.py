# version 1.5 vom 20.11.23
import time
import asyncio
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import configparser
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

                    if mqtttopic:
                            register_values[register] = message
                except:
                        pass

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

# Dictionary MQTT-Topic Mapping
topic_mapping = {
    'input_power': f"openWB/set/mqtt/pv/{pvnumber}/get/power",
    'daily_yield_energy': f"openWB/set/mqtt/pv/{pvnumber}/get/exported",
}

# Registernames
registers = ['input_power', 'daily_yield_energy',]

bridge = None
loop = asyncio.get_event_loop()
loop.run_until_complete(huaweiReadValues(bridge, topic_mapping, mqtthost, "PVImporter", registers))
