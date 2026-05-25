import argparse
import os
import statistics
import time
from collections import defaultdict

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper


abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

URI = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

SAFE_THRUST_STEPS = (
    (0, 0.8),
    (15000, 1.5),
    (25000, 1.5),
    (35000, 1.5),
    (0, 0.8),
)

FULL_POWER_THRUST_STEPS = (
    (0, 0.8),
    (15000, 1.0),
    (30000, 1.0),
    (50000, 0.6),
    (65535, 0.25),
    (0, 1.0),
)

LOG_PERIOD_MS = 10


def motor_log_config():
    log_config = LogConfig(name='PropOffMotorTest', period_in_ms=LOG_PERIOD_MS)
    log_config.add_variable('motor.m1', 'uint16_t')
    log_config.add_variable('motor.m2', 'uint16_t')
    log_config.add_variable('motor.m3', 'uint16_t')
    log_config.add_variable('motor.m4', 'uint16_t')
    return log_config


def summarize(samples):
    motor_keys = ('motor.m1', 'motor.m2', 'motor.m3', 'motor.m4')

    print("\nMotor command summary")
    print(f"samples: {len(samples)}")

    for key in motor_keys:
        values = [sample[key] for sample in samples]
        print(
            f"{key}: "
            f"min={min(values):6.0f} "
            f"mean={statistics.fmean(values):7.1f} "
            f"max={max(values):6.0f} "
            f"std={statistics.pstdev(values):7.1f}"
        )

    nonzero_samples = [
        sample for sample in samples
        if any(sample[key] > 0 for key in motor_keys)
    ]
    if not nonzero_samples:
        print("No nonzero motor samples found.")
        return

    totals = {
        key: sum(sample[key] for sample in nonzero_samples)
        for key in motor_keys
    }
    total_output = sum(totals.values())
    print("\nShare of commanded output while motors were active")
    for key in motor_keys:
        print(f"{key}: {totals[key] / total_output * 100:5.1f}%")

    spreads = [
        max(sample[key] for key in motor_keys) - min(sample[key] for key in motor_keys)
        for sample in nonzero_samples
    ]
    print(
        "\nPer-sample motor spread while active: "
        f"mean={statistics.fmean(spreads):.1f}, "
        f"max={max(spreads):.1f}"
    )


def run_test(cf, thrust_steps):
    samples = []
    samples_by_step = defaultdict(list)
    current_step = {'thrust': None}

    log_config = motor_log_config()

    def log_callback(timestamp, data, logconf):
        row = dict(data)
        row['timestamp_ms'] = timestamp
        samples.append(row)
        samples_by_step[current_step['thrust']].append(row)

    log_config.data_received_cb.add_callback(log_callback)
    cf.log.add_config(log_config)
    log_config.start()

    try:
        print("Arming for prop-off motor output test...")
        cf.supervisor.send_arming_request(True)
        time.sleep(1.0)

        for thrust, duration in thrust_steps:
            current_step['thrust'] = thrust
            print(f"Sending level thrust {thrust} for {duration:.1f}s")
            end_time = time.time() + duration
            while time.time() < end_time:
                cf.commander.send_setpoint(0, 0, 0, thrust)
                time.sleep(0.05)

        print("Stopping motors...")
        cf.commander.send_stop_setpoint()
        time.sleep(0.5)
    finally:
        log_config.stop()
        log_config.delete()
        log_config.data_received_cb.remove_callback(log_callback)

    summarize(samples)

    print("\nBy thrust step")
    for thrust, step_samples in samples_by_step.items():
        if thrust is None or not step_samples:
            continue
        print(f"\nThrust {thrust}")
        summarize(step_samples)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a prop-off Crazyflie motor command diagnostic."
    )
    parser.add_argument(
        '--full-power',
        action='store_true',
        help='include a 0.25 second 65535 thrust burst; props must be removed',
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    print("REMOVE ALL PROPELLERS BEFORE RUNNING THIS TEST.")
    print("Keep the Crazyflie restrained and keep fingers clear of the motors.\n")

    thrust_steps = SAFE_THRUST_STEPS
    if args.full_power:
        print("FULL POWER MODE: this includes a 0.25s burst at thrust 65535.")
        confirmation = input("Type PROPS OFF to continue: ").strip()
        if confirmation != 'PROPS OFF':
            raise SystemExit("Full-power test cancelled.")
        thrust_steps = FULL_POWER_THRUST_STEPS

    cflib.crtp.init_drivers()

    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        cf = scf.cf
        try:
            run_test(cf, thrust_steps)
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
        finally:
            print("Emergency stop/disarm cleanup...")
            cf.commander.send_stop_setpoint()
            cf.commander.send_notify_setpoint_stop()
            cf.supervisor.send_arming_request(False)
