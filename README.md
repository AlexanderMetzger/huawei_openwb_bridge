# huawei_openwb_bridge

Die Huawei OpenWB Bridge löst das Problem der Huawei Anbindung an die OpenWB. 
Es spiel erst mal keine Rolle ob dies in einem Docker Container oder einem Raspberry Pi oder sonstiger Hardware ausgeführt wird. 
Wichtig ist eine WLAN Verbindung zum Huawei Wechselrichter sowie eine LAN Verbindung im gleichen Netz wie die OpenWB. 
Die Konfiguration erfolgt dann über die config.ini oder die passende GUI in Form der WLAN_App.py diese startet einen Webserver. Der Webserver ermöglicht die WLAN Konfiguration eines Raspberry Pi und das eintragen der MQTT ID's die von der OpenWB vorgegeben werden.
