from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


LOG_PATH = Path(__file__).resolve().parent / "logging.jsonl"
SHOW_OPTIONAL_PITCH_BY_ROLL = False
SHOW_INDIVIDUAL_ACTUATOR_PLOTS = True


def load_log_data(log_path=LOG_PATH):
    df = pd.read_json(log_path, lines=True)

    data_df = pd.json_normalize(df["data"])
    df = pd.concat([df.drop(columns=["data"]), data_df], axis=1)
    df = df.sort_values("timestamp_ms").reset_index(drop=True)
    df["time_s"] = (df["timestamp_ms"] - df["timestamp_ms"].iloc[0]) / 1000

    for column in ["pm.batteryLevel", "pm.vbat"]:
        if column in df.columns:
            df[column] = df[column].ffill().bfill()

    return df


def get_log_df(df, log_name):
    return df[df["log"] == log_name].copy()


def short_label(column_name):
    return column_name.split(".", 1)[-1]


def available_columns(df, columns):
    return [
        column
        for column in columns
        if column in df.columns and df[column].notna().any()
    ]


def add_average_column(df, source_columns, output_column):
    source_columns = available_columns(df, source_columns)
    if source_columns:
        df[output_column] = df[source_columns].mean(axis=1)


def add_magnitude_column(df, source_columns, output_column):
    input_columns = source_columns
    source_columns = available_columns(df, source_columns)
    if len(source_columns) == len(input_columns):
        df[output_column] = np.sqrt((df[source_columns] ** 2).sum(axis=1))


def add_motor_diagonal_columns(motor_df):
    motor_columns = ["motor.m1", "motor.m2", "motor.m3", "motor.m4"]
    if len(available_columns(motor_df, motor_columns)) != len(motor_columns):
        return

    motor_df["motor.diag_m1_m3"] = motor_df["motor.m1"] + motor_df["motor.m3"]
    motor_df["motor.diag_m2_m4"] = motor_df["motor.m2"] + motor_df["motor.m4"]
    motor_df["motor.diag_diff_13_minus_24"] = (
        motor_df["motor.diag_m1_m3"] - motor_df["motor.diag_m2_m4"]
    )


def plot_columns(ax, df, columns, title, ylabel, step=False):
    columns = available_columns(df, columns)

    if df.empty or not columns:
        ax.set_title(f"{title} (no data)")
        ax.axis("off")
        return

    for column in columns:
        if step:
            ax.step(df["time_s"], df[column], where="post", label=short_label(column))
        else:
            ax.plot(df["time_s"], df[column], linewidth=1.2, label=short_label(column))

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", ncols=min(len(columns), 4))


def plot_individual_columns(df, columns, title, ylabel, step=False):
    columns = available_columns(df, columns)

    if df.empty or not columns:
        print(f"Skipping {title}: no data.")
        return

    fig, axes = plt.subplots(len(columns), 1, figsize=(13, 2.4 * len(columns)), sharex=True)
    axes = np.atleast_1d(axes)

    for ax, column in zip(axes, columns):
        if step:
            ax.step(df["time_s"], df[column], where="post", linewidth=1.2)
        else:
            ax.plot(df["time_s"], df[column], linewidth=1.2)

        ax.set_title(short_label(column))
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Time (s)")
    fig.suptitle(title)
    fig.tight_layout(rect=[0, 0, 1, 0.97])


def plot_motor_difference_from_average(motor_df):
    motor_columns = available_columns(motor_df, ["motor.m1", "motor.m2", "motor.m3", "motor.m4"])
    if motor_df.empty or len(motor_columns) < 2:
        print("Skipping motor difference plot: not enough motor data.")
        return

    motor_df = motor_df.copy()
    motor_df["motor.avg"] = motor_df[motor_columns].mean(axis=1)

    fig, ax = plt.subplots(figsize=(13, 5))
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.35)

    for column in motor_columns:
        ax.step(
            motor_df["time_s"],
            motor_df[column] - motor_df["motor.avg"],
            where="post",
            linewidth=1.1,
            label=f"{short_label(column)} - avg",
        )

    ax.set_title("Motor command difference from average")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Command difference")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", ncols=min(len(motor_columns), 4))
    fig.tight_layout()


def plot_motor_diagonal_balance(ax, motor_df):
    pair_columns = available_columns(motor_df, ["motor.diag_m1_m3", "motor.diag_m2_m4"])
    diff_columns = available_columns(motor_df, ["motor.diag_diff_13_minus_24"])

    if motor_df.empty or len(pair_columns) < 2 or not diff_columns:
        ax.set_title("Diagonal motor balance (no data)")
        ax.axis("off")
        return

    ax.set_title("Diagonal motor balance: m1+m3 vs m2+m4")
    ax.grid(True, alpha=0.3)

    pair_lines = []
    pair_lines += ax.step(
        motor_df["time_s"],
        motor_df["motor.diag_m1_m3"],
        where="post",
        color="tab:blue",
        linewidth=1.1,
        label="m1+m3",
    )
    pair_lines += ax.step(
        motor_df["time_s"],
        motor_df["motor.diag_m2_m4"],
        where="post",
        color="tab:green",
        linewidth=1.1,
        label="m2+m4",
    )
    ax.set_ylabel("Pair command")

    diff_ax = ax.twinx()
    diff_ax.axhline(0, color="black", linewidth=0.8, alpha=0.35)
    diff_line = diff_ax.plot(
        motor_df["time_s"],
        motor_df["motor.diag_diff_13_minus_24"],
        color="tab:red",
        linewidth=1.0,
        alpha=0.9,
        label="diff",
    )[0]
    diff_ax.set_ylabel("m1+m3 - m2+m4", color="tab:red")
    diff_ax.tick_params(axis="y", labelcolor="tab:red")

    lines = pair_lines + [diff_line]
    ax.legend(lines, [line.get_label() for line in lines], loc="best", ncols=3)


def plot_flight_profile(ax, stab_df, baro_df):
    has_altitude = "baro.asl" in baro_df.columns and baro_df["baro.asl"].notna().any()
    has_thrust = "stabilizer.thrust" in stab_df.columns and stab_df["stabilizer.thrust"].notna().any()

    if not has_altitude and not has_thrust:
        ax.set_title("Flight profile (no data)")
        ax.axis("off")
        return

    ax.set_title("Flight profile: altitude response and thrust")
    ax.grid(True, alpha=0.3)

    if has_altitude:
        altitude_change = baro_df["baro.asl"] - baro_df["baro.asl"].iloc[0]
        ax.plot(
            baro_df["time_s"],
            altitude_change,
            color="tab:blue",
            linewidth=1.4,
            label="altitude change",
        )
        ax.set_ylabel("Altitude change (m)", color="tab:blue")
        ax.tick_params(axis="y", labelcolor="tab:blue")

    if has_thrust:
        thrust_ax = ax.twinx() if has_altitude else ax
        thrust_ax.step(
            stab_df["time_s"],
            stab_df["stabilizer.thrust"],
            where="post",
            color="tab:orange",
            alpha=0.75,
            linewidth=1.1,
            label="thrust",
        )
        thrust_ax.set_ylabel("Thrust command", color="tab:orange")
        thrust_ax.tick_params(axis="y", labelcolor="tab:orange")


def plot_battery(ax, battery_df):
    has_level = "pm.batteryLevel" in battery_df.columns and battery_df["pm.batteryLevel"].notna().any()
    has_vbat = "pm.vbat" in battery_df.columns and battery_df["pm.vbat"].notna().any()

    if battery_df.empty or (not has_level and not has_vbat):
        ax.set_title("Battery (no data)")
        ax.axis("off")
        return

    ax.set_title("Battery")
    ax.set_xlabel("Time (s)")
    ax.grid(True, alpha=0.3)

    if has_level:
        ax.plot(
            battery_df["time_s"],
            battery_df["pm.batteryLevel"],
            color="tab:purple",
            marker="o",
            markersize=3,
            label="batteryLevel",
        )
        ax.set_ylabel("Battery (%)", color="tab:purple")
        ax.tick_params(axis="y", labelcolor="tab:purple")

    if has_vbat:
        voltage_ax = ax.twinx()
        voltage_ax.plot(
            battery_df["time_s"],
            battery_df["pm.vbat"],
            color="tab:brown",
            marker="o",
            markersize=3,
            label="vbat",
        )
        voltage_ax.set_ylabel("Voltage (V)", color="tab:brown")
        voltage_ax.tick_params(axis="y", labelcolor="tab:brown")


def active_windows_from_series(time_values, value_series):
    values = value_series.to_numpy()
    if len(values) == 0 or np.nanmax(values) <= 0:
        return []

    threshold = max(np.nanmax(values) * 0.05, 1)
    active = values > threshold
    if not np.any(active):
        return []

    times = time_values.to_numpy()
    windows = []
    start = None

    for time_s, is_active in zip(times, active):
        if is_active and start is None:
            start = time_s
        elif not is_active and start is not None:
            windows.append((start, time_s))
            start = None

    if start is not None:
        windows.append((start, times[-1]))

    return windows


def get_active_windows(stab_df, motor_df, rpm_df):
    for df, column in [
        (motor_df, "motor.avg"),
        (rpm_df, "rpm.avg"),
        (stab_df, "stabilizer.thrust"),
    ]:
        if column in df.columns and df[column].notna().any():
            windows = active_windows_from_series(df["time_s"], df[column])
            if windows:
                return windows

    return []


def shade_active_windows(axes, active_windows):
    if not active_windows:
        return

    for ax in axes:
        for start_s, end_s in active_windows:
            ax.axvspan(start_s, end_s, color="tab:orange", alpha=0.08, linewidth=0)

    first_start, first_end = active_windows[0]
    axes[0].text(
        (first_start + first_end) / 2,
        0.96,
        "motors active",
        transform=axes[0].get_xaxis_transform(),
        ha="center",
        va="top",
        color="tab:orange",
        fontsize=9,
    )


def plot_flight_story_dashboard(stab_df, gyro_df, acc_df, motor_df, rpm_df, baro_df, battery_df):
    stab_df = stab_df.copy()
    gyro_df = gyro_df.copy()
    acc_df = acc_df.copy()
    motor_df = motor_df.copy()
    rpm_df = rpm_df.copy()

    add_magnitude_column(gyro_df, ["gyro.x", "gyro.y", "gyro.z"], "gyro.mag")
    add_magnitude_column(acc_df, ["acc.x", "acc.y", "acc.z"], "acc.mag")
    add_average_column(motor_df, ["motor.m1", "motor.m2", "motor.m3", "motor.m4"], "motor.avg")
    add_motor_diagonal_columns(motor_df)
    add_average_column(rpm_df, ["rpm.m1", "rpm.m2", "rpm.m3", "rpm.m4"], "rpm.avg")

    fig, axes = plt.subplots(
        8,
        1,
        figsize=(15, 17),
        sharex=True,
        gridspec_kw={"height_ratios": [1.25, 1, 1, 1, 1, 0.95, 1, 0.9]},
    )

    plot_flight_profile(axes[0], stab_df, baro_df)
    plot_columns(
        axes[1],
        stab_df,
        ["stabilizer.roll", "stabilizer.pitch", "stabilizer.yaw"],
        "Attitude: how the craft was tilted",
        "deg",
    )
    plot_columns(
        axes[2],
        gyro_df,
        ["gyro.x", "gyro.y", "gyro.z", "gyro.mag"],
        "Gyro: how quickly it rotated",
        "deg/s",
    )
    plot_columns(
        axes[3],
        acc_df,
        ["acc.x", "acc.y", "acc.z", "acc.mag"],
        "Acceleration: forces measured by the IMU",
        "g",
    )
    plot_columns(
        axes[4],
        motor_df,
        ["motor.m1", "motor.m2", "motor.m3", "motor.m4", "motor.avg"],
        "Motor commands: what the controller asked for",
        "command",
        step=True,
    )
    plot_motor_diagonal_balance(axes[5], motor_df)
    plot_columns(
        axes[6],
        rpm_df,
        ["rpm.m1", "rpm.m2", "rpm.m3", "rpm.m4", "rpm.avg"],
        "RPM: what the motors actually did",
        "rpm",
    )
    plot_battery(axes[7], battery_df)

    active_windows = get_active_windows(stab_df, motor_df, rpm_df)
    shade_active_windows(axes, active_windows)

    axes[-1].set_xlabel("Time (s)")
    fig.suptitle("Flight Story Dashboard", fontsize=16)
    fig.tight_layout(rect=[0, 0, 1, 0.98])


def plot_flight_overview(stab_df, gyro_df, acc_df, baro_df, battery_df):
    fig, axes = plt.subplots(5, 1, figsize=(13, 12), sharex=True)

    plot_columns(
        axes[0],
        stab_df,
        ["stabilizer.roll", "stabilizer.pitch", "stabilizer.yaw"],
        "Attitude",
        "Degrees",
    )
    plot_columns(
        axes[1],
        gyro_df,
        ["gyro.x", "gyro.y", "gyro.z"],
        "Gyro",
        "deg/s",
    )
    plot_columns(
        axes[2],
        acc_df,
        ["acc.x", "acc.y", "acc.z"],
        "Acceleration",
        "g",
    )
    plot_columns(
        axes[3],
        baro_df,
        ["baro.asl"],
        "Barometer altitude",
        "m",
    )
    plot_battery(axes[4], battery_df)

    axes[-1].set_xlabel("Time (s)")
    fig.suptitle("Flight Telemetry Overview")
    fig.tight_layout()


def plot_motor_and_rpm(motor_df, rpm_df):
    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)

    plot_columns(
        axes[0],
        motor_df,
        ["motor.m1", "motor.m2", "motor.m3", "motor.m4"],
        "Motor command",
        "Command",
        step=True,
    )
    plot_columns(
        axes[1],
        rpm_df,
        ["rpm.m1", "rpm.m2", "rpm.m3", "rpm.m4"],
        "Motor RPM",
        "RPM",
    )

    axes[-1].set_xlabel("Time (s)")
    fig.suptitle("Actuator Output")
    fig.tight_layout()


def plot_individual_actuator_output(motor_df, rpm_df):
    plot_individual_columns(
        motor_df,
        ["motor.m1", "motor.m2", "motor.m3", "motor.m4"],
        "Motor commands individually",
        "Command",
        step=True,
    )
    plot_motor_difference_from_average(motor_df)
    plot_individual_columns(
        rpm_df,
        ["rpm.m1", "rpm.m2", "rpm.m3", "rpm.m4"],
        "Motor RPM individually",
        "RPM",
    )


def plot_baro_environment(baro_df):
    fig, axes = plt.subplots(3, 1, figsize=(13, 8), sharex=True)

    plot_columns(axes[0], baro_df, ["baro.asl"], "Altitude above sea level", "m")
    plot_columns(axes[1], baro_df, ["baro.pressure"], "Air pressure", "mbar")
    plot_columns(axes[2], baro_df, ["baro.temp"], "Barometer temperature", "C")

    axes[-1].set_xlabel("Time (s)")
    fig.suptitle("Barometer")
    fig.tight_layout()


def plot_pitch_by_roll(stab_df):
    columns = available_columns(stab_df, ["stabilizer.roll", "stabilizer.pitch"])
    if len(columns) < 2:
        print("Skipping pitch-by-roll plot: not enough stabilizer data.")
        return

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.plot(
        stab_df["stabilizer.roll"],
        stab_df["stabilizer.pitch"],
        marker="o",
        markersize=2,
        linewidth=0.8,
        color="tab:blue",
    )
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.4)
    ax.axvline(0, color="black", linewidth=0.8, alpha=0.4)
    ax.set_xlabel("Roll (deg)")
    ax.set_ylabel("Pitch (deg)")
    ax.set_title("Pitch by Roll")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()


def plot_stabilizer_values_next_to_each_other(stab_df):
    stab_values = [
        "stabilizer.thrust",
        "stabilizer.roll",
        "stabilizer.pitch",
        "stabilizer.yaw",
    ]
    colors = [
        "tab:blue",
        "tab:orange",
        "tab:green",
        "tab:red",
    ]

    stab_values = available_columns(stab_df, stab_values)
    if not stab_values:
        print("Skipping stabilizer side-by-side plot: no stabilizer data.")
        return

    fig, axes = plt.subplots(1, len(stab_values), figsize=(16, 4), sharex=True)
    axes = np.atleast_1d(axes)

    for ax, stab_value, color in zip(axes, stab_values, colors):
        ax.plot(stab_df["time_s"], stab_df[stab_value], color=color)
        ax.set_title(short_label(stab_value))
        ax.set_xlabel("Time (s)")

        if "pm.batteryLevel" in stab_df.columns and stab_df["pm.batteryLevel"].notna().any():
            battery_ax = ax.twinx()
            battery_ax.plot(stab_df["time_s"], stab_df["pm.batteryLevel"], color="tab:purple")
            battery_ax.set_ylabel("Battery (%)", color="tab:purple")

    fig.tight_layout()


def plot_attitude_velocity_field(stab_df):
    columns = available_columns(stab_df, ["stabilizer.roll", "stabilizer.pitch"])
    if len(columns) < 2 or len(stab_df) < 2:
        print("Skipping attitude velocity field: not enough stabilizer data.")
        return

    rolls = stab_df["stabilizer.roll"].to_numpy()
    pitches = stab_df["stabilizer.pitch"].to_numpy()

    d_roll = np.diff(rolls)
    d_pitch = np.diff(pitches)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.plot(rolls, pitches, alpha=0.3, color="gray")

    skip = max(len(stab_df) // 200, 1)
    ax.quiver(
        rolls[:-1:skip],
        pitches[:-1:skip],
        d_roll[::skip],
        d_pitch[::skip],
        scale_units="xy",
        angles="xy",
        scale=1,
        color="tab:blue",
        alpha=0.8,
    )

    ax.set_xlabel("Roll angle (deg)")
    ax.set_ylabel("Pitch angle (deg)")
    ax.set_title("Attitude State Velocity Field")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()


def calculate_stability_efficiency(stab_df):
    columns = available_columns(stab_df, ["stabilizer.roll", "stabilizer.pitch"])
    if len(columns) < 2:
        print("Not enough stabilizer data to calculate stability efficiency.")
        return 0

    rolls = stab_df["stabilizer.roll"].to_numpy()
    pitches = stab_df["stabilizer.pitch"].to_numpy()

    v = rolls**2 + pitches**2
    dv = np.diff(v)

    total_steps = len(dv)
    if total_steps == 0:
        print("Not enough stabilizer data to calculate stability efficiency.")
        return 0

    stabilizing_steps = np.sum(dv < 0)
    stability_efficiency = (stabilizing_steps / total_steps) * 100

    print(f"Stability efficiency: {stability_efficiency:.1f}% of roll/pitch samples moved closer to level.")
    return stability_efficiency


def main():
    df = load_log_data()

    stab_df = get_log_df(df, "StabilizerLog")
    gyro_df = get_log_df(df, "GyrometerLog")
    acc_df = get_log_df(df, "AccelometerLog")
    motor_df = get_log_df(df, "MotorLog")
    rpm_df = get_log_df(df, "RPMLog")
    baro_df = get_log_df(df, "BarometerLog")
    battery_df = get_log_df(df, "BatteryLog")

    calculate_stability_efficiency(stab_df)
    plot_flight_story_dashboard(stab_df, gyro_df, acc_df, motor_df, rpm_df, baro_df, battery_df)

    
    plot_individual_actuator_output(motor_df, rpm_df)

    plot_baro_environment(baro_df)

    
    plot_pitch_by_roll(stab_df)

    plt.show()


if __name__ == "__main__":
    main()
