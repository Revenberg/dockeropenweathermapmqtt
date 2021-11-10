from pyowm import OWM
from pyowm.utils import config
from pyowm.utils import timestamps

import os
import socket
import binascii
import time
import sys
import json
import paho.mqtt.client as mqtt
import random
import configparser
from datetime import datetime

do_raw_log = os.getenv("LOGGING", "false").lower() == 'true'

pool_frequency = int(os.getenv("POOL_FREQUENCY", "300"))

country = os.getenv('WEATHER_COUNTRY', 'country')
language = os.getenv('WEATHER_LANGUAGE', 'language')

mqttclientid = f'python-mqtt-{random.randint(0, 1000)}'
mqttBroker = os.getenv("MQTT_ADDRESS", "localhost")
mqttPort = int(os.getenv("MQTT_PORT", "1883"))
mqttTopic = os.getenv("MQTT_TOPIC", "reading/weather")

apikey = os.getenv('apikey', '')

if do_raw_log:
    print("running with debug")
    print(mqttBroker)
    print(mqttPort)
    print(mqttTopic)
    print(do_raw_log)
else:
    print("running without debug")

config_dict = config.get_default_config()
config_dict['language'] = language

def getData(client, mqttTopic, config_dict):
    owm = OWM(apikey, config_dict)
    mgr = owm.weather_manager()

    # Here put your city and Country ISO 3166 country codes
    observation = mgr.weather_at_place(country)

    w = observation.weather
    # Weather details from INTERNET

    values = dict()
    values['status'] = w.status         # short version of status (eg. 'Rain')
    values['detailed_status']  = w.detailed_status  # detailed version of status (eg. 'light rain')

    wind  = w.wind()

    values['wind_speed']  = wind ["speed"]
    values['wind_direction_deg']  = wind ["deg"]
    values['humidity']  = w.humidity

    temperature  = w.temperature('celsius')
    values['temp']  = temperature["temp"]
    values['pressure'] = w.pressure['press']

    values['clouds'] = w.clouds #Cloud coverage
    values["sunrise"] = w.sunrise_time()*1000 #Sunrise time (GMT UNIXtime or ISO 8601)
    values["sunset"] = w.sunset_time()*1000 #Sunset time (GMT UNIXtime or ISO 8601)
    values["weather_code"] =  w.weather_code

    values["weather_icon"] = w.weather_icon_name
    values["visibility_distance"] = w.visibility_distance

    location = observation.location.name
    values["location"] = location

    rain = w.rain
    #If there is no data recorded from rain then return 0, otherwise #return the actual data
    if len(rain) == 0:
        values['lastrain'] = float("0")
    else:
        if "3h" in rain:
            values['lastrain'] = rain["3h"]
        if "1h" in rain:
            values['lastrain'] = rain["1h"]

    snow = w.snow
    #If there is no data recorded from rain then return 0, otherwise #return the actual data
    if len(snow) == 0:
        values['lastsnow'] = float("0")
    else:
        if "3h" in snow:
            values['lastsnow'] = snow["3h"]
        if "1h" in snow:
            values['lastsnow'] = snow["1h"]

#       UV index
    s = country.split(",")
    reg = owm.city_id_registry()
    list_of_locations = reg.locations_for(s[0], country=s[1])
    myLocation = list_of_locations[0]

    uvimgr = owm.uvindex_manager()

    uvi = uvimgr.uvindex_around_coords(myLocation.lat, myLocation.lon )
    values['uvi'] = uvi.value

    # Print the data
    if do_raw_log:
        print(values)

    json_body = { k: v for k, v in values.items() }

    if do_raw_log:
        print(f"Send topic `{mqttTopic}`")
        print(f"Send topic `{json_body}`")

    result = client.publish(mqttTopic, json.dumps(json_body))
    # result: [0, 1]
    status = result[0]

    if status == 0:
        if do_raw_log:
            print(f"Send topic `{mqttTopic}`")
    else:
        print(f"Failed to send message to topic {mqttTopic} ")

def connect_mqtt(mqttclientid, mqttBroker, mqttPort ):
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)
    # Set Connecting Client ID
    client = mqtt.Client(mqttclientid)
#    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(mqttBroker, mqttPort)
    return client

client=connect_mqtt(mqttclientid, mqttBroker, mqttPort )
client.loop_start()

try:
    while True:
        getData(client, mqttTopic, config_dict)
        time.sleep(pool_frequency)
except Exception as e:
    print(e)
    pass