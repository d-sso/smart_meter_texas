import login_information

MQTT_info = {
    'username': login_information.mqtt_username,
    'password': login_information.mqtt_password,
    'mqtt_server': login_information.mqtt_server,
    'target_topic': 'custom_integration/smart_meter_texas/meter_read'
}

smart_meter_texas_user = login_information.smart_meter_texas_user
smart_meter_texas_pwd = login_information.smart_meter_texas_pwd
eesid = login_information.eesid
meter_number = login_information.meter_number

smart_meter_texas_webpage = 'https://www.smartmetertexas.com'
smart_meter_texas_on_demand_issue_read_api = smart_meter_texas_webpage + "/api/ondemandread"
smart_meter_texas_on_demand_get_read_api = smart_meter_texas_webpage + "/api/usage/latestodrread"

smart_meter_texas_sleep_timer_after_login = 3
smart_meter_texas_sleep_timer_timeout_page_load = 20
smart_meter_texas_user_cookie = 'smt_user'
#smart_meter_texas_error_screenshot_file = 'err.png'
smart_meter_texas_error_screenshot_file = False
smart_meter_texas_log_file = ''
smart_meter_texas_sleep_between_cycles = 300
smart_meter_texas_refresh_period = 3600
smart_meter_texas_login_token_refresh_period = 7200
smart_meter_texas_sleep_after_read_request = 10