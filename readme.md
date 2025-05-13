# Smart Meter Texas scraper
This script logs into the smart meter texas website using selenium (headless browser) to acquire a login token, then uses the token to request latest meter reading.


## History
Originally I had setup the [official home assistant integration](https://www.home-assistant.io/integrations/smart_meter_texas/) for getting the Smart Meter Texas information for my property. However around December/24 or January/25 the integration stopped working and started to throw some weird errors like "Reached ratelimit or brute force protection".

At the [integration github issues](https://github.com/home-assistant/core/issues/138957) I saw a discussion about how they started using Akamai Bot Manager to block programatic access to the data.

Digging deeper, I found the python package ([this project](https://github.com/grahamwetzler/smart-meter-texas)) and also [this project](https://github.com/mrand/smart_meter_texas) that is a bit older and refers to an "official" API.

The problem is that the "official" API demands a SSL certificate and static IP so that they can enable access. As a hobbyist, I don't have time for that, so I looked up on how to programatically access webpage and issue commands. This simple script is the result of that, it uses [selenium](https://www.selenium.dev/) to create a browsing session using Firefox and log into Smart Meter Texas website to acquire a login token. In possesion of said token, it's possible to hit their APIs and request the meter readings.

## Notes
The program currently tries to get the value once every hour, and I've noticed that the APIs aren't that reliable when it comes to updating the meter value. As a result the value might come 1 hour (or more) late. It would be nice to add support to set the value timestamp on the MQTT message and on the Home Assistant sensor to correct for these inconsistencies on the API.

## Requirements
* The script was created to write values to a MQTT broker, so one is required. My goal is to get the data into Home Assistant, and I'm using [Mosquitto MQTT server](https://mosquitto.org/) on a container. This can be installed as an [add-on](https://github.com/home-assistant/addons/blob/174f8e66d0eaa26f01f528beacbde0bd111b711c/mosquitto/DOCS.md) through Home Assistant as well.
* The script uses Firefox as the browser, so it needs to be installed. It should be possible to use Chrome with some tweaks on a couple of the first ~30 lines of code (basically find all references to Firefox and replace with the Chrome equivalent)

## Setting up
* Clone/download the repository.
* Create a "login_information.py" file on the same directory, containing the top secret info to allow to connect. The required variables are below, set the strings to the appropriate information. 
```
mqtt_username = 'mqtt_username'
mqtt_password = 'mqtt_password'
mqtt_server = 'ip_address_or_FQDN'

smart_meter_texas_user = 'smt_user'
smart_meter_texas_pwd = 'smt_pwd'

eesid = 'YOUR_SSID'
meter_number = 'YOUR_NUMBER'
```

* Take a look at the 'config_variables.py' script to check if you'd like to change any of the varaiables.
    * Most relevant one is probably the topic to publish to MQTT, by default is "custom_integration/smart_meter_texas/meter_read"
    * Frequency to (try) to update the meter reading is 1 hour, controlled by variable "smart_meter_texas_refresh_period" (in seconds). I'm not sure shorter periods will work, even with the 1 hour period sometimes I get errors.
    * The variable "smart_meter_texas_login_token_refresh_period" controls how often the program will login the main page. Two hours (7200 seconds) seems a standard time for login token expiration, might experiment with that at some point.

### Running the script directly through python
* Create a virtual environment : https://docs.python.org/3/library/venv.html
* Install dependencies:
```
    pip install -r requirements.txt
```
* Run the script using the nohup (so it runs in the background):
```
    nohup ./.venv/bin/python scrape_smart_meter_texas.py &
```
* Check status - the nohup command will run the program in the background, to check if it's still running it's possible to use ps
```
    ps aux | grep smart_meter_texas
```

### Running the docker container

A docker file is present, allowing the script to be run inside a container. The image can be built using:
```
    docker build -t smart_meter_texas .
```

Due to the bot manager blocking access through the python requests library, it's necessary to add an entry to the hosts file so that the script work. The docker image can be run using the "--add-host" option to point the "www.smartmetertexas.com" address to the appropriate IP address (can be found for example by pinging smartmetertexas.com without the "www").
Example of docker run command:
```
    docker run -d --add-host www.smartmetertexas.com=X.X.X.X --name="smart_meter_texas" -e TZ=America/Houston smart_meter_texas
```

* Monitoring the container
Starting up the script with the "-d" option will run it detached from the console. To check if it's still running, you can run the command below. 
```
    docker ps | grep smart_meter_texas
```

Progress can also be checked on the log files.
```
    docker logs smart_meter_texas
```

## Home assistant configuration
Assuming the [MQTT integration](https://www.home-assistant.io/integrations/mqtt/) is configured, the sensor can be added to home assistant as a MQTT entity. Below is my configuration for reference.
The "unit of measurement", "device_class" and "state_class" sensor attributes are required for Home Assistant to properly recognize the sensor in the [Energy Dashboard](https://www.home-assistant.io/docs/energy/).
```
mqtt:
    sensor:
        - name: "Smart meter read"
          unique_id: "smart_meter_read_f94f4649-f8ed-4df8-aaa2-9755839683cb"
          state_topic: "custom_integration/smart_meter_texas/meter_read"
          unit_of_measurement: "kWh"
          suggested_display_precision: 2
          device_class: "energy"
          state_class: "total_increasing"
```