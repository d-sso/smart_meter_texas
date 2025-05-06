from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver import FirefoxOptions
import requests
import time
import json
import logging
import datetime
import paho.mqtt.client as mqtt
import config_variables
import dns.resolver

logger = logging.getLogger(__name__)

def get_local_storage_item(driver, key):
    return driver.execute_script(f"return window.localStorage.getItem('{key}');")

class smt_handler:
    def __init__(self, ESIID:str, MeterNumber:str, logger):
        self.ESIID = ESIID
        self.MeterNumber = MeterNumber
        self.logger = logger
        self.token = ""
        self.token_last_obtained = datetime.datetime(1970,1,1)
        self.cookies = None
        pass

    def request_dns():
        try:
            # Use the DNS resolver to get the IP address of the domain
            answers = dns.resolver.resolve(config_variables.smart_meter_texas_domain, 'A')
            for rdata in answers:
                ip_address = rdata.address
                logger.info(f"Resolved IP address: {ip_address}")
                return True
        except Exception as e:
            logger.error(f"DNS resolution failed: {e}")
            return False

    def login(self, username:str, pwd:str):
        try:
            options = FirefoxOptions()
            options.add_argument("--headless")

            browser = webdriver.Firefox(options=options)

            self.logger.debug('Loading main page')
            browser.get(config_variables.smart_meter_texas_webpage)

            self.logger.debug('Logging in')
            wait = WebDriverWait(browser, config_variables.smart_meter_texas_sleep_timer_timeout_page_load)
            #browser.get_screenshot_as_file("BeforeLogin.png")
            wait.until(EC.element_to_be_clickable((By.ID, "userid"))).send_keys(username)
            wait.until(EC.element_to_be_clickable((By.ID, "password"))).send_keys(pwd)
            #browser.get_screenshot_as_file("AfterType.png")
            wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="loginform"]/div[8]/button'))).click()

            time.sleep(config_variables.smart_meter_texas_sleep_timer_after_login)
            #browser.get_screenshot_as_file("AfterLogin.png")
            self.logger.debug('Inside!')
            value = get_local_storage_item(browser, config_variables.smart_meter_texas_user_cookie)
            self.token = json.loads(value)['token']
            self.logger.info(f"Received token - {self.token}")
            self.token_last_obtained = datetime.datetime.now()
            cookies = browser.get_cookies()
            self.cookies = {}
            for cookie in cookies:
                self.cookies[cookie['name']] = cookie['value']
        except Exception as e:
            if config_variables.smart_meter_texas_error_screenshot_file:
                self.logger.error("Issue logging in! Screenshot will be captured")
                browser.get_screenshot_as_file(config_variables.smart_meter_texas_error_screenshot_file)
            else:
                self.logger.error(f"Issue logging in! {e}")
    
    def request_meter_read(self):
        request_headers = {
            "Content-Type" : "application/json",
            "Accept" : "application/json",
            "Authorization" : f"Bearer {self.token}",
        }
        request_data = { 
            "ESIID": self.ESIID
            , "MeterNumber": self.MeterNumber
        }
        try:
            self.logger.debug('Issuing read request')
            response = requests.post(config_variables.smart_meter_texas_on_demand_issue_read_api,data=json.dumps(request_data),headers=request_headers, timeout=30)
            if response.ok:
                self.logger.info(f'Request meter read suceeded - {response.text}')
                return True
            else:
                self.logger.error(f"Request meter read failed - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Issue requesting meter read - {e}")
            return False
    
    def collect_meter_read(self):
        request_headers = {
            "Content-Type" : "application/json",
            "Accept" : "application/json",
            "Authorization" : f"Bearer {self.token}"
        }
        request_data = { 
            "ESIID": self.ESIID
            , "MeterNumber": self.MeterNumber
        }
        try:
            response = requests.post(config_variables.smart_meter_texas_on_demand_get_read_api,data=json.dumps(request_data),headers=request_headers, cookies=self.cookies, timeout=30)
            if response.ok:
                val = response.json()
                while val['data']['odrstatus'] == "PENDING":
                    self.logger.debug(f'Meter result not ready, retry in {config_variables.smart_meter_texas_sleep_after_read_request} seconds')
                    self.logger.info(f'Message received: {val}')
                    time.sleep(config_variables.smart_meter_texas_sleep_after_read_request)
                    smt_handler.request_dns()
                    # wait for 1 min for response TODO: Transform into async call with timeout handling
                    response = requests.post(config_variables.smart_meter_texas_on_demand_get_read_api,data=json.dumps(request_data),headers=request_headers,timeout=60)
                    val = response.json()
                self.logger.debug('Received meter read')
                self.logger.info(val)
                # check if value returned has expected fields and is good. Instances of status equal to "none" and "error" caused issues
                if val['data'] and val['data']['odrstatus'] and val['data']['odrread'] and val['data']['odrstatus'] == "COMPLETED":
                    return val['data']['odrread']
                return False
            else:
                self.logger.error(f"Collect meter result failed - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Issue retrieving meter read - {e}")
            return False


def main():
    if config_variables.smart_meter_texas_log_file:
        logging.basicConfig(
            filename=config_variables.smart_meter_texas_log_file
            ,level=logging.INFO
            ,format='%(asctime)s %(message)s'
            , datefmt='%d/%m/%Y %I:%M:%S %p'
            )
    else:
        logging.basicConfig(
            level=logging.INFO
            ,format='%(asctime)s %(message)s'
            , datefmt='%d/%m/%Y %I:%M:%S %p'
            )

    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqttc.username_pw_set(config_variables.MQTT_info['username'],config_variables.MQTT_info['password'])
    mqttc.connect(config_variables.MQTT_info['mqtt_server'], 1883, 60)
    mqttc.loop_start()

    handler = smt_handler(config_variables.eesid,config_variables.meter_number,logger)
    handler.login(username=config_variables.smart_meter_texas_user,pwd=config_variables.smart_meter_texas_pwd)
    last_run = datetime.datetime(2025,1,1)
    while True:
        now_ts = datetime.datetime.now()
        now_hour = now_ts.hour
        logger.debug(f"Waking up to process - now ts = {now_ts}, last_run = {last_run}, next refresh = {last_run + datetime.timedelta(0,config_variables.smart_meter_texas_refresh_period)}")
        if (now_ts-last_run).total_seconds() > config_variables.smart_meter_texas_refresh_period:
            last_run = now_ts
            if smt_handler.request_dns():
                if((now_ts-handler.token_last_obtained).total_seconds() > config_variables.smart_meter_texas_login_token_refresh_period):
                    logger.info(f"Token is more than {config_variables.smart_meter_texas_login_token_refresh_period/3600} hours old, logging in again")
                    handler.login(username=config_variables.smart_meter_texas_user,pwd=config_variables.smart_meter_texas_pwd)
                if handler.request_meter_read():
                    val = handler.collect_meter_read()
                    if(val):
                        meter_value = val
                        msg_info = mqttc.publish(config_variables.MQTT_info['target_topic'],meter_value,qos=0)
                        msg_info.wait_for_publish()
                        logger.info(f"Finished processing - next refresh = {last_run + datetime.timedelta(0,config_variables.smart_meter_texas_refresh_period)}")
                    else:
                        logger.warning("Service returned bad data - not forwarded to MQTT")
                else:
                    logger.warning("Error requesting read, will try again next hour")
        
        logger.debug(f"Going to sleep for {config_variables.smart_meter_texas_sleep_between_cycles/60} min")
        time.sleep(config_variables.smart_meter_texas_sleep_between_cycles)


if __name__ == '__main__':
    main()
