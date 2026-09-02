import logging
import sys
import time
from threading import Event, Thread
import crazylogger
import math
import json

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper

from crazylogger import logger


URI = uri_helper.uri_from_env(
    default='radio://0/80/2M/E7E7E7E7E7'
)

DEFAULT_HEIGHT = 0.5

deck_attached_event = Event()

logging.basicConfig(level=logging.ERROR)


# ---------------- FLIGHT ----------------

def flight(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:


        mc.turn_left(360, rate=30)
        time.sleep(1)

        mc.forward(0.5)
        time.sleep(0.3)
        mc.turn_left(90, rate=30)
        time.sleep(0.3)
        mc.forward(0.5)
        time.sleep(0.3)
        mc.turn_left(90, rate=30)
        time.sleep(0.3)
        mc.forward(0.5)



# ---------------- VELOCITY CALCULATION ----------------

previous_x = None
previous_y = None
previous_time = None
previous_yaw = None
total_rotation = 0.0

def loggers():
    global previous_x, previous_y, previous_time, previous_yaw, total_rotation
    gyro_z = crazylogger.latest_gyro_z
    x = crazylogger.latest_x
    y = crazylogger.latest_y
    current_time = crazylogger.latest_state_timestamp
    current_yaw = crazylogger.latest_yaw

    # The logger thread may not have received its first position yet
    if (x is None or y is None or current_time is None or
            current_yaw is None or gyro_z is None):
        return None

    # We need two measurements before velocity can be calculated
    if previous_time is None:
        previous_time = current_time
        previous_x = x
        previous_y = y
        previous_yaw = current_yaw
        return None

    dt = (current_time - previous_time) / 1000

    # No new stateEstimate packet yet
    if dt <= 0:
        return None

    # Linear velocity
    x_lin_vel = (x - previous_x) / dt
    y_lin_vel = (y - previous_y) / dt

    # Angular velocity
    delta_yaw = current_yaw - previous_yaw

    # Handle yaw wrapping around -180 / +180 degrees
    delta_yaw = (delta_yaw + 180) % 360 - 180

    angular_vel = delta_yaw / dt

    total_horz_speed = math.sqrt(
        x_lin_vel * x_lin_vel +
        y_lin_vel * y_lin_vel
    )
    distance = total_horz_speed * dt
    total_rotation += gyro_z * dt
    # Current values become previous values
    previous_time = current_time
    previous_x = x
    previous_y = y
    previous_yaw = current_yaw

    return {
        "timestamp_ms": current_time,
        "vx_calculated": x_lin_vel,
        "vy_calculated": y_lin_vel,
        "angular_velocity": angular_vel,
        "Crazyflie_ang_vel": gyro_z,
        "Total rotation": total_rotation,
        "vx_crazyflie": crazylogger.latest_vx,
        "vy_crazyflie": crazylogger.latest_vy,
        "speed": total_horz_speed,
        "distance": distance
    }

# ---------------- MATH FILE WRITER ----------------

math_logging = True


def log_writer():
    global math_logging

    with open("mather.jsonl", "a", buffering=1) as json_file:

        while math_logging:

            math_data = loggers()

            if math_data is not None:
                json.dump(math_data, json_file)
                json_file.write("\n")

            time.sleep(0.01)


# ---------------- FLOW DECK CHECK ----------------

def param_deck_flow(_, value_str):

    value = int(value_str)
    print(value)

    if value:
        deck_attached_event.set()
        print('Deck is attached!')
    else:
        print('Deck is NOT attached!')


# ---------------- MAIN ----------------

if __name__ == '__main__':

    cflib.crtp.init_drivers()

    with SyncCrazyflie(
        URI,
        cf=Crazyflie(rw_cache='./cache')
    ) as scf:

        cf = scf.cf

        scf.cf.param.add_update_callback(
            group='deck',
            name='bcFlow2',
            cb=param_deck_flow
        )

        scf.cf.param.request_param_update('deck.bcFlow2')

        if not deck_attached_event.wait(timeout=5):
            print('No flow deck detected!')
            sys.exit(1)

        # Start your normal Crazyflie logger
        log_configs, log_file = logger(cf)

        scf.cf.supervisor.send_arming_request(True)
        time.sleep(1.0)

        # Start math logger alongside the flight
        math_thread = Thread(target=log_writer)
        math_thread.start()

        try:

            flight(scf)

        finally:

            print("Stopping...")

            scf.cf.commander.send_stop_setpoint()
            scf.cf.supervisor.send_arming_request(False)

            # Stop math logger
            math_logging = False
            math_thread.join()

            # Stop Crazyflie loggers
            for log_config, _ in log_configs:
                log_config.stop()

            time.sleep(0.2)

            log_file.close()
