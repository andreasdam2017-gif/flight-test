import os
import logging
import time
import json


import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.utils import uri_helper
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath) 
os.chdir(dname)
uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')
current_battery = 100
latest_gyro_z = None
latest_baro_asl = 0
latest_x = None
latest_y = None
latest_vx = None
latest_vy = None
latest_yaw = None
latest_state_timestamp = None
def motor_log_var():
    log_motor = LogConfig(name='MotorLog', period_in_ms=10)
    log_rpm = LogConfig(name='RPMLog', period_in_ms=10)
    log_motor.add_variable('motor.m1','uint16_t')
    log_motor.add_variable('motor.m2','uint16_t')
    log_motor.add_variable('motor.m3','uint16_t')
    log_motor.add_variable('motor.m4','uint16_t')
    log_rpm.add_variable('rpm.m1','uint16_t')
    log_rpm.add_variable('rpm.m2','uint16_t')
    log_rpm.add_variable('rpm.m3','uint16_t')
    log_rpm.add_variable('rpm.m4','uint16_t')
    return log_motor,log_rpm

def accelo_log_var():
    log_acc = LogConfig(name='AccelometerLog', period_in_ms=10)
    log_acc.add_variable('acc.x')
    log_acc.add_variable('acc.y')
    log_acc.add_variable('acc.z')
    return log_acc
def gyro_log_var():
    log_gyro = LogConfig(name='GyrometerLog', period_in_ms=10)
    log_gyro.add_variable('gyro.x','float')
    log_gyro.add_variable('gyro.y','float')
    log_gyro.add_variable('gyro.z','float')
    return log_gyro
def baro_log_var():
    log_baro = LogConfig(name='BarometerLog', period_in_ms=10)
    log_baro.add_variable('baro.asl','float') #altitude above sea level
    log_baro.add_variable('baro.pressure','float')#airpressure
    log_baro.add_variable('baro.temp','float') 
    return log_baro
def stab_log_var():
    log_stab = LogConfig(name='StabilizerLog', period_in_ms=10)
    log_stab.add_variable('stabilizer.thrust', 'float')
    log_stab.add_variable('stabilizer.roll', 'float')
    log_stab.add_variable('stabilizer.pitch', 'float')
    log_stab.add_variable('stabilizer.yaw', 'float')
    return log_stab
def state_estimate_log_var():
    log_state = LogConfig(name='StateEstimateLog', period_in_ms=100)

    log_state.add_variable('stateEstimate.x', 'float')
    log_state.add_variable('stateEstimate.y', 'float')
    log_state.add_variable('stateEstimate.vx', 'float')
    log_state.add_variable('stateEstimate.vy', 'float')
    log_state.add_variable('stateEstimate.yaw', 'float')

    return log_state
def bat_log_var():
    log_bat = LogConfig(name='BatteryLog', period_in_ms=1000)
    log_bat.add_variable('pm.batteryLevel', 'uint8_t')
    log_bat.add_variable('pm.vbat','float')
    return log_bat

def logger(cf):
    log_stab = stab_log_var()
    log_bat = bat_log_var()
    log_baro = baro_log_var()
    log_gyro = gyro_log_var()
    log_acc = accelo_log_var()
    log_motor, log_rpm = motor_log_var()
    log_state = state_estimate_log_var()
    
    f = open("logging.jsonl", "w", buffering=1)

    def battery_callback(timestamp, data, logconf):
        global current_battery
        current_battery = data['pm.batteryLevel']
        entry = {
            "timestamp_ms": timestamp,
            "log": logconf.name,
            "data": data
        }
        
        json.dump(entry, f)
        f.write("\n")

    def stab_callback(timestamp, stab_data, logconf):
        global latest_baro_asl, latest_x, latest_y
        global latest_vx, latest_vy, latest_yaw, latest_state_timestamp
        global latest_gyro_z

        entry = {
            "timestamp_ms": timestamp,
            "log": logconf.name,
            "data": stab_data
        }
        if 'gyro.z' in stab_data:
            latest_gyro_z = stab_data['gyro.z']


        if 'baro.asl' in stab_data:
            latest_baro_asl = stab_data['baro.asl']

        if 'stateEstimate.x' in stab_data:
            latest_x = stab_data['stateEstimate.x']
            latest_state_timestamp = timestamp

        if 'stateEstimate.y' in stab_data:
            latest_y = stab_data['stateEstimate.y']

        if 'stateEstimate.vx' in stab_data:
            latest_vx = stab_data['stateEstimate.vx']

        if 'stateEstimate.vy' in stab_data:
            latest_vy = stab_data['stateEstimate.vy']

        if 'stateEstimate.yaw' in stab_data:
            latest_yaw = stab_data['stateEstimate.yaw']

        json.dump(entry, f)
        f.write("\n")

    log_configs = [
        (log_bat, battery_callback),
        (log_stab, stab_callback),
        (log_baro, stab_callback),
        (log_gyro, stab_callback),
        (log_acc, stab_callback),
        (log_motor, stab_callback),
        (log_rpm, stab_callback),
         (log_state, stab_callback),
    ]

    for log_config, callback in log_configs:
        log_config.data_received_cb.add_callback(callback)
        cf.log.add_config(log_config)
        log_config.start()

    return log_configs, f
