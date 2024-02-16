import time
from flask import Flask, render_template, request, redirect, jsonify
from wifi import Cell
import configparser
import os
import subprocess
import shutil
import requests
import zipfile
import git

app = Flask(__name__)

# Lese die MQTT-Host-Adresse aus der config.ini-Datei
config = configparser.ConfigParser()
config.read('/home/pi/huawei_bridge_openwb/config.ini')
mqtt_host = config.get('MQTT', 'host')
pv_number = config.get('pvnumber', 'value')
bat_number = config.get('batnumber', 'value')
counter_number = config.get('counternumber', 'value')

# Initialisiere das WLAN-Interface
wifi_interface = 0

# Initialisiere die Variable für den Verbindungsstatus
connection_status = None

# GitHub-Repository-Informationen
repository_url = 'https://github.com/AlexanderMetzger/huawei_openwb_bridge.git'
# Eine Liste von Dateien, die aktualisiert werden sollen
repo_directory = '/home/pi/repo_huaweimqtt'

# Lese den Versionshinweis aus der huaweimqtt.py-Datei
def get_firmware_version():
    try:
        with open('/home/pi/huawei_bridge_openwb/huaweimqtt.py', 'r') as f:
            first_line = f.readline()
            version = first_line.strip().replace("# version ", "")
            return version
    except Exception as e:
        print(f"Fehler beim Auslesen der Firmware-Version: {e}")
        return "Unbekannt"




@app.route('/update_firmware_new', methods=['POST'])
def update_firmware_new():
    if not os.path.exists(repo_directory):
        git.Repo.clone_from(repository_url, repo_directory)
    else:
        # Wenn das Repository bereits existiert, aktualisieren Sie es auf die neueste Version
        repo = git.Repo(repo_directory)
        origin = repo.remote('origin')
        origin.pull()

        # Datei kopieren und ersetzen
        shutil.copy('/home/pi/repo_huaweimqtt/huaweimqtt.py', '/home/pi/huawei_bridge_openwb/huaweimqtt.py')
        shutil.copy('/home/pi/repo_huaweimqtt/huaweimqtt2ndinv.py', '/home/pi/huawei_bridge_openwb/huaweimqtt2ndinv.py')
        # Hier die index.html-Datei kopieren und ersetzen
        shutil.copy('/home/pi/repo_huaweimqtt/index.html', '/home/pi/templates/index.html')
        # Hier die config.ini-Datei kopieren und ersetzen
        # shutil.copy('/home/pi/huawei_bridge_openwb/config.ini', '/home/pi/huawei_bridge_openwb/config.ini')
        # Hier die config.ini-Datei kopieren und ersetzen
        shutil.copy('/home/pi/repo_huaweimqtt/wlan_app.py', '/home/pi/wlan_app.py')
        #subprocess.run(['sudo', 'cp', ('/home/pi/repo_huaweimqtt/huaweimqtt.service', '/lib/systemd/system/huaweimqtt.service'])
        # Berechtigungen zurücksetzen

        try:
            subprocess.run(['sudo', 'cp', '/home/pi/repo_huaweimqtt/huaweimqtt.service', '/lib/systemd/system/huaweimqtt.service'], check=True)
            subprocess.run(['sudo', 'cp', '/home/pi/repo_huaweimqtt/huaweimqtt2ndinv.service', '/lib/systemd/system/huaweimqtt2ndinv.service'], check=True)
        except subprocess.CalledProcessError as e:
            return f"Fehler beim Kopieren der Dienstdatei: {e}"

        os.chown('/home/pi/huawei_bridge_openwb/huaweimqtt.py', os.getuid(), os.getgid())
        os.chmod('/home/pi/huawei_bridge_openwb/huaweimqtt.py', 0o755)
        os.chown('/home/pi/huawei_bridge_openwb/huaweimqtt2ndinv.py', os.getuid(), os.getgid())
        os.chmod('/home/pi/huawei_bridge_openwb/huaweimqtt2ndinv.py', 0o755)
        os.chown('/home/pi/wlan_app.py', os.getuid(), os.getgid())
        os.chmod('/home/pi/wlan_app.py', 0o755)

        try:
            with open('/home/pi/huawei_bridge_openwb/huaweimqtt.py', 'r') as f:
                first_line = f.readline()
                if first_line.startswith('# version'):
                    version_info = first_line.strip().split('vom ')[1]
                    # Speichere die Version im Dateisystem ab oder gib sie auf dem Webinterface aus
                    # Hier kannst du den Code einfügen, um die Version auf dem Webinterface anzuzeigen
        except Exception as e:
            return f"Fehler beim Aktualisieren der Firmware: {e}"

    return "Firmware erfolgreich aktualisiert."



@app.route('/control_services', methods=['POST'])
def control_services():
    try:
        #check the checkbox
        is_secondWR_checked = 'secondWRCheckbox' in request.form

        if is_secondWR_checked:
            subprocess.run(['sudo', 'systemctl', 'stop', 'huaweimqtt.service'])
            subprocess.run(['sudo', 'systemctl', 'disable', 'huaweimqtt.service'])

            subprocess.run(['sudo', 'systemctl', 'start', 'huawei2ndmqtt.service'])
            subprocess.run(['sudo', 'systemctl', 'enable', 'huawei2ndmqtt.service'])
        else:
            subprocess.run(['sudo', 'systemctl', 'stop', 'huawei2ndmqtt.service'])
            subprocess.run(['sudo', 'systemctl', 'disable', 'huawei2ndmqtt.service'])

            subprocess.run(['sudo', 'systemctl', 'start', 'huaweimqtt.service'])
            subprocess.run(['sudo', 'systemctl', 'enable', 'huaweimqtt.service'])

        return redirect('/')
    except Exception as e:
        return f"Fehler beim Steuern der Dienste: {e}"

@app.route('/check_huawei_service_status', methods=['GET'])
def check_huawei_service_status():
    try:
        # Überprüfe den Status des huawei.service-Dienstes
        result = subprocess.run(['sudo', 'systemctl', 'is-enabled', 'huaweimqtt.service'], capture_output=True, text=True, check=True)

        # Gib den Status als JSON zurück
        return jsonify({'status': result.stdout.strip()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500  # Interner Serverfehler


@app.route('/update_firmware', methods=['POST'])
def update_firmware():
    try:
        # Datei herunterladen
        url = 'https://lebensraum-wohnraum.de/huawei_bridge_openwb/huaweimqtt_v1_0.zip'
        response = requests.get(url)

        # Überprüfen, ob der Download erfolgreich war
        if response.status_code == 200:
            # Datei speichern
            with open('/tmp/huaweimqtt_v1_0.zip', 'wb') as f:
                f.write(response.content)

            # Zip-Datei entpacken
            with zipfile.ZipFile('/tmp/huaweimqtt_v1_0.zip', 'r') as zip_ref:
                zip_ref.extractall('/tmp/huaweimqtt_v1_0')

            # Datei kopieren und ersetzen
            shutil.copy('/tmp/huaweimqtt_v1_0/huaweimqtt.py', '/home/pi/huawei_bridge_openwb/huaweimqtt.py')
            # Hier die index.html-Datei kopieren und ersetzen
            shutil.copy('/tmp/huaweimqtt_v1_0/index.html', '/home/pi/templates/index.html')
             # Hier die config.ini-Datei kopieren und ersetzen
            shutil.copy('/tmp/huaweimqtt_v1_0/config.ini', '/home/pi/huawei_bridge_openwb/config.ini')
             # Hier die config.ini-Datei kopieren und ersetzen
            shutil.copy('/tmp/huaweimqtt_v1_0/wlan_app.py', '/home/pi/wlan_app.py')

            # Berechtigungen zurücksetzen
            os.chown('/home/pi/huawei_bridge_openwb/huaweimqtt.py', os.getuid(), os.getgid())
            os.chmod('/home/pi/huawei_bridge_openwb/huaweimqtt.py', 0o755)
            os.chown('/home/pi/wlan_app.py', os.getuid(), os.getgid())
            os.chmod('/home/pi/wlan_app.py', 0o755)
            # Firmware-Version auslesen

            with open('/home/pi/huawei_bridge_openwb/huaweimqtt.py', 'r') as f:
                first_line = f.readline()
                if first_line.startswith('# version'):
                    version_info = first_line.strip().split('vom ')[1]
                    # Speichere die Version im Dateisystem ab oder gib sie auf dem Webinterface aus
                    # Hier kannst du den Code einfügen, um die Version auf dem Webinterface anzuzeigen


        else:
            return f"Fehler beim Aktualisieren der Firmware: Statuscode {response.status_code}"

    except Exception as e:
        return f"Fehler beim Aktualisieren der Firmware: {e}"


@app.route('/restart', methods=['POST'])
def restart():
    try:
        os.system("sudo reboot")
        return "Der Raspberry Pi wird neu gestartet..."
    except Exception as e:
        return f"Fehler beim Neustart des Raspberry Pi: {e}"


def get_wifi_connection_status():
    try:
        result = subprocess.run(['iwconfig', 'wlan0'], capture_output=True, text=True, check=True)
        if "Not-Associated" in result.stdout:
            return "Nicht verbunden"
        else:
            # Extrahiere den Namen des verbundenen WLAN-Netzwerks aus der Ausgabe
            start_index = result.stdout.find('ESSID:') + 7
            end_index = result.stdout.find('"', start_index)
            connected_ssid = result.stdout[start_index:end_index]
            return f"Verbunden mit {connected_ssid}"
    except subprocess.CalledProcessError:
        return "Fehler beim Überprüfen der Verbindung"

def restart_wifi_adapter():
    try:
        # WLAN-Adapter ausschalten
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'down'], check=True)
        # WLAN-Adapter einschalten
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], check=True)
        # Kurze Wartezeit, damit der Adapter sich neu verbinden kann
        time.sleep(5)
    except subprocess.CalledProcessError:
        print("Fehler beim Neustart des WLAN-Adapters")

def connect_to_wifi(ssid, password):
    # Erstelle eine temporäre wpa_supplicant-Konfigurationsdatei
    config = f'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\n\nnetwork={{\n    ssid="{ssid}"\n    psk="{password}"\n}}\n'
    subprocess.run(['wpa_passphrase', ssid, password], input=config, text=True, check=True)

    # Überprüfe, ob die alte Datei bereits existiert
    if os.path.exists('/etc/wpa_supplicant/wpa_supplicant.conf'):
        # Benenne die alte Datei um, um ein Backup zu erstellen
        shutil.move('/etc/wpa_supplicant/wpa_supplicant.conf', '/etc/wpa_supplicant/wpa_supplicant.conf.bak')

    # Verschiebe die wpa_supplicant.conf-Datei
    try:
        shutil.move('/home/pi/huawei_bridge_openwb/wpa_supplicant.conf', '/etc/wpa_supplicant/')
    except FileNotFoundError:
        # Die Datei existiert nicht, erstelle sie mit dem Inhalt
        with open('/home/pi/huawei_bridge_openwb/wpa_supplicant.conf', 'w') as f:
            f.write(config)
        # Verschiebe die wpa_supplicant.conf-Datei erneut
        shutil.move('/home/pi/huawei_bridge_openwb/wpa_supplicant.conf', '/etc/wpa_supplicant/')

    # Deaktiviere und aktiviere das WLAN-Interface
    try:
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'down'], check=True)
        subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], check=True)

        # Kurze Wartezeit, damit der Adapter sich neu verbinden kann
        time.sleep(5)
    # Führe die zusätzlichen Befehle aus
        subprocess.run(['sudo', 'killall', 'wpa_supplicant'], check=True)
        subprocess.run(['sudo', 'wpa_supplicant', '-B', '-i', 'wlan0', '-c', '/etc/wpa_supplicant/wpa_supplicant.conf'], check=True)
        subprocess.run(['sudo', 'dhclient', 'wlan0'], check=True)

        # Kurze Wartezeit, damit der Adapter sich neu verbinden kann
        time.sleep(10)

        # Überprüfe den WLAN-Verbindungsstatus
        result = subprocess.run(['iwconfig', 'wlan0'], capture_output=True, text=True, check=True)
        if "Not-Associated" in result.stdout:
            print("Verbindung fehlgeschlagen.")
            return False
        else:
            # Extrahiere den Namen des verbundenen WLAN-Netzwerks aus der Ausgabe
            start_index = result.stdout.find('ESSID:') + 7
            end_index = result.stdout.find('"', start_index)
            connected_ssid = result.stdout[start_index:end_index]
            print(f"Verbunden mit {connected_ssid}.")
            return True

    except subprocess.CalledProcessError:
        print("Fehler beim Verbinden.")
        return False


@app.route('/')
def index():
    networks = Cell.all('wlan0')  # 'wlan0' kann sich je nach deiner Raspberry Pi-Konfiguration ändern

    # Überprüfe den aktuellen WLAN-Verbindungsstatus
    global connection_status
    connection_status = get_wifi_connection_status()

    # Versionshinweis auslesen
    firmware_version = get_firmware_version()

    return render_template('index.html', networks=networks, mqtt_host=mqtt_host,
    connection_status=connection_status, firmware_version=firmware_version, pv_number=pv_number,
    bat_number=bat_number, counter_number=counter_number)

@app.route('/connect', methods=['POST'])
def connect():
    global connection_status  # Greife auf die globale Variable zu

    ssid = request.form['ssid']
    password = request.form['password']

    if connect_to_wifi(ssid, password):
        # Verbindung erfolgreich hergestellt
        connection_status = f"Verbunden mit {ssid}"
    else:
        # Verbindung fehlgeschlagen
        connection_status = "Fehler beim Verbinden"

    restart_wifi_adapter()

    return redirect('/')

@app.route('/save_config', methods=['POST'])
def save_config():
    try:
        new_mqtt_host = request.form['mqtt_host']
        new_pv_value = request.form['pv_number']
        new_counter_value = request.form['counter_number']
        new_bat_value = request.form['bat_number']

        # Update the values in the config.ini file
        config.set('MQTT', 'host', new_mqtt_host)
        config.set('pvnumber', 'value', new_pv_value)
        config.set('counternumber', 'value', new_counter_value)
        config.set('batnumber', 'value', new_bat_value)

        with open('/home/pi/huawei_bridge_openwb/config.ini', 'w') as configfile:
            config.write(configfile)

        # Read the updated values from the file
        config.read('/home/pi/huawei_bridge_openwb/config.ini')
        global mqtt_host, pv_number, counter_number, bat_number
        mqtt_host = config.get('MQTT', 'host')
        pv_number = config.get('pvnumber', 'value')
        counter_number = config.get('counternumber', 'value')
        bat_number = config.get('batnumber', 'value')

        return redirect('/')

    except Exception as e:
        return f"Fehler beim Speichern der Konfiguration: {e}"


"""
@app.route('/update_mqtt_config', methods=['POST'])
def update_mqtt_config():
    new_mqtt_host = request.form['mqtt_host']

    # Aktualisiere die MQTT-Host-Adresse in der config.ini-Datei
    config.set('MQTT', 'host', new_mqtt_host)
    with open('/home/pi/huawei_bridge_openwb/config.ini', 'w') as configfile:
        config.write(configfile)

    # Lese die aktualisierte MQTT-Host-Adresse erneut aus der Datei
    config.read('/home/pi/huawei_bridge_openwb/config.ini')
    global mqtt_host
    mqtt_host = config.get('MQTT', 'host')

    return redirect('/')

@app.route('/update_pv_config', methods=['POST'])
def update_pv_config():
    new_pv_value = request.form['pv_number']

    # Aktualisiere den Wert in der config.ini-Datei
    config.set('pvnumber', 'value', new_pv_value)
    with open('/home/pi/huawei_bridge_openwb/config.ini', 'w') as configfile:
        config.write(configfile)

    # Lese den aktualisierten Wert erneut aus der Datei
    config.read('/home/pi/huawei_bridge_openwb/config.ini')
    global pv_number  # Hier sollte es "pv_number" statt "pvnumber_value" sein
    pv_number = config.get('pvnumber', 'value')

    return redirect('/')

@app.route('/update_counter_config', methods=['POST'])
def update_counter_config():
    new_counter_value = request.form['counter_number']

    # Aktualisiere den Wert in der config.ini-Datei
    config.set('counternumber', 'value', new_counter_value)
    with open('/home/pi/huawei_bridge_openwb/config.ini', 'w') as configfile:
        config.write(configfile)

    # Lese den aktualisierten Wert erneut aus der Datei
    config.read('/home/pi/huawei_bridge_openwb/config.ini')
    global counter_number  # Hier sollte es "pv_number" statt "pvnumber_value" sein
    counter_number = config.get('counternumber', 'value')

    return redirect('/')

@app.route('/update_bat_config', methods=['POST'])
def update_bat_config():
    new_bat_value = request.form['bat_number']

    # Aktualisiere den Wert in der config.ini-Datei
    config.set('batnumber', 'value', new_bat_value)
    with open('/home/pi/huawei_bridge_openwb/config.ini', 'w') as configfile:
        config.write(configfile)

    # Lese den aktualisierten Wert erneut aus der Datei
    config.read('/home/pi/huawei_bridge_openwb/config.ini')
    global bat_number  # Hier sollte es "pv_number" statt "pvnumber_value" sein
    bat_number = config.get('batnumber', 'value')

    return redirect('/')

"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)
    print("Die Anwendung wird gestartet...")
