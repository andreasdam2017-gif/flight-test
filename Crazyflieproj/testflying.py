import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper


URI = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

# Only show errors from the Crazyflie library.
logging.basicConfig(level=logging.ERROR)

# Low-level flight values.
# Keep roll and pitch at 0 to ask the stabilizer to stay level.
ROLL = 0.0
PITCH = 0.0
YAWRATE = 10.0

# Thrust is not height. It is motor power from 0 to 65535.
# This value is for a props-off motor response test, not a flight test.
MIN_THRUST = 30000
TEST_THRUST = 40000
SETPOINT_PERIOD = 0.02


def send_for_seconds(cf, roll, pitch, yawrate, thrust, seconds):
    end_time = time.time() + seconds

    while time.time() < end_time:
        cf.commander.send_setpoint(roll, pitch, yawrate, thrust)
        time.sleep(SETPOINT_PERIOD)


def ramp_thrust(cf, start, stop, step, delay):
    if start < stop:
        thrust_values = range(start, stop + 1, step)
    else:
        thrust_values = range(start, stop - 1, -step)

    for thrust in thrust_values:
        print(f'Thrust: {thrust}')
        cf.commander.send_setpoint(ROLL, PITCH, YAWRATE, thrust)
        time.sleep(delay)


def low_level_motor_test(scf):
    cf = scf.cf

    try:
        print('Arming')
        cf.platform.send_arming_request(True)
        time.sleep(1.0)

        print('Unlocking commander')
        cf.commander.send_setpoint(ROLL, PITCH, YAWRATE, 0)
        time.sleep(0.1)

        print('Sending low thrust setpoints')
        send_for_seconds(cf, ROLL, PITCH, YAWRATE, MIN_THRUST, 1.0)

        print('Ramping up')
        ramp_thrust(cf, MIN_THRUST, TEST_THRUST, step=1000, delay=0.08)

        print('Holding briefly')
        send_for_seconds(cf, ROLL, PITCH, YAWRATE, TEST_THRUST, 0.5)

        print('Ramping down')
        ramp_thrust(cf, TEST_THRUST, MIN_THRUST, step=1000, delay=0.08)

    finally:
        print('Stopping motors')
        cf.commander.send_stop_setpoint()
        cf.commander.send_notify_setpoint_stop()
        cf.platform.send_arming_request(False)
        time.sleep(0.2)


if __name__ == '__main__':
    input('Remove propellers. Put the Crazyflie in a clear area. Press Enter to start the motor test...')

    cflib.crtp.init_drivers()

    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        low_level_motor_test(scf)
