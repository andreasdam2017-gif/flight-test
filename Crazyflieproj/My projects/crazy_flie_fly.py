import os
import time

import crazylogger
from crazylogger import logger
from telemetry_store import DB_PATH, new_flight_id, save_flight_log_to_db, utc_now

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

k = None
HOVER_THRUST = 40000 
# Forward/right drift: make these more negative in 0.3-0.5 degree steps.
# Backward/left drift: move them back toward zero, or positive if needed.
ROLL_SETPOINT_TRIM_DEGREES = 0
PITCH_SETPOINT_TRIM_DEGREES = -0.5
TAKEOFF_THRUST = 39500
HOVER_START_THRUST = 38000
HOVER_MIN_THRUST = 30000
HOVER_MAX_THRUST = 52000


def send_trimmed_setpoint(roll, pitch, yaw, thrust):
    cf.commander.send_setpoint(
        roll + ROLL_SETPOINT_TRIM_DEGREES,
        pitch + PITCH_SETPOINT_TRIM_DEGREES,
        yaw,
        thrust,
    )


def average_baro(samples=50, delay=0.02):
    total = 0
    for i in range(samples):
        total += crazylogger.latest_baro_asl
        time.sleep(delay)
    return total / samples


def log_synch(i):
    global k
    
    if i == 1 and k is None:
        baro_asl_baseline = average_baro()
        k = baro_asl_baseline
    
    print(k)
    return k


def take_off(i):
    send_trimmed_setpoint(0, 0, 0, 0)
    time.sleep(0.1)
    for i in range(int(i * 10)):
        send_trimmed_setpoint(0, 0, 0, TAKEOFF_THRUST)
        time.sleep(0.1) 

    

def hover(i):
    roll = -1.5
    pitch = -1
    yaw = 0
    thrust = HOVER_START_THRUST

    baro_baseline = log_synch(2)
    target_baro = baro_baseline + 0.5
    filtered_baro = crazylogger.latest_baro_asl

    send_trimmed_setpoint(roll, pitch, yaw, thrust)
    time.sleep(0.4) 
    for i in range(int(i * 10)):
        latest_baro_asl = crazylogger.latest_baro_asl
        filtered_baro = 0.9 * filtered_baro + 0.1 * latest_baro_asl
        altitude_error = target_baro - filtered_baro

        if altitude_error > 0.08:
            thrust += 50
        elif altitude_error < -0.08:
            thrust -= 50

        thrust = max(HOVER_MIN_THRUST, min(HOVER_MAX_THRUST, thrust))
        send_trimmed_setpoint(roll, pitch, yaw, thrust)
        time.sleep(0.1)


def land(i):
        HOVER_THRUST =  37800
        
        send_trimmed_setpoint(0, 0, 0, HOVER_THRUST)
        time.sleep(0.6)
        for i in range(int(i * 10)):
            
            send_trimmed_setpoint(0, 0, 0, HOVER_THRUST)
            HOVER_THRUST = HOVER_THRUST - 100
            time.sleep(0.1) 
        time.sleep(0.2)
          
cflib.crtp.init_drivers()


with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
    cf = scf.cf
    flight_id = None
    flight_started_at = None
    log_configs = []
    log_file = None
    try:
        flight_id = new_flight_id()
        flight_started_at = utc_now()
        log_configs, log_file = logger(cf)

        print("Arming...")
        
        cf.supervisor.send_arming_request(True)
        time.sleep(1)
        
        log_synch(1)
        time.sleep(0.5)
        print("Taking off...")
        take_off(1)
        
        time.sleep(0.1)
        hover(3.0)
        print("landing starting")
        land(3.0)
        


    except KeyboardInterrupt:
        print("\nFlight interrupted by user!")
        #land(5)
    except Exception as e:
        print(f"Flight logic error caught: {e}")

    finally:

        print("Stopping...")

        cf.commander.send_stop_setpoint()
        cf.commander.send_notify_setpoint_stop()
        cf.supervisor.send_arming_request(False)
            
        for log_config, _ in log_configs:
            log_config.stop()
        time.sleep(0.2)
        if log_file is not None:
            log_file.close()
        flight_ended_at = utc_now()

        if flight_id is not None:
            try:
                saved_count = save_flight_log_to_db(flight_id, flight_started_at, flight_ended_at)
                print(f"Saved {saved_count} telemetry entries to {DB_PATH} as {flight_id}")
            except Exception as e:
                print(f"Telemetry database save failed: {e}")
