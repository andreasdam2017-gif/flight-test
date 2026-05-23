import os
import time

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


HOVER_THRUST = 40000 


def hover(i):
        cf.commander.send_setpoint(0, 0, 0, 40000)
        time.sleep(0.4)
        for i in range(i):
            cf.commander.send_setpoint(0, 6, 0 , 37500)
            time.sleep(0.4)
            time.sleep(0.1)
        

def land(i):
        HOVER_THRUST =  38000
        
        cf.commander.send_setpoint(0, -12, 0, HOVER_THRUST)
        time.sleep(0.6)
        for i in range(i):
            
            cf.commander.send_setpoint(-1,0,0,HOVER_THRUST)
            HOVER_THRUST = HOVER_THRUST - 1000
            time.sleep(1.0) 
        cf.commander.send_setpoint(-1,0,0,45000)
        time.sleep(0.2)
          
cflib.crtp.init_drivers()


with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
    cf = scf.cf
    flight_id = new_flight_id()
    flight_started_at = utc_now()
    log_configs, log_file = logger(cf)
    
    

    try:
        print("Arming...")
        cf.supervisor.send_arming_request(True)
        time.sleep(1)

        print("Taking off...")
        cf.commander.send_setpoint(0, 0, 0, 0)
        time.sleep(0.1)
        hover(6)
        print("landing starting")
        land(6)
        
        cf.commander.send_stop_setpoint()
        cf.commander.send_notify_setpoint_stop()
        cf.supervisor.send_arming_request(False)
        


    except KeyboardInterrupt:
        print("\nFlight interrupted by user!")
        #land(5)
    except Exception as e:
        print(f"Flight logic error caught: {e}")

    finally:

        print("Stopping...")

        time.sleep(3)
        for log_config, _ in log_configs:
            log_config.stop()
        log_file.close()
        flight_ended_at = utc_now()

        try:
            saved_count = save_flight_log_to_db(flight_id, flight_started_at, flight_ended_at)
            print(f"Saved {saved_count} telemetry entries to {DB_PATH} as {flight_id}")
        except Exception as e:
            print(f"Telemetry database save failed: {e}")
