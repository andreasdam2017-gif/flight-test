# Crazyflie Python Starter

This folder uses Bitcraze's `cflib` Python library to talk to a Crazyflie over Crazyradio.

## Setup

Install the Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

This project is currently using Python 3.12 on this machine. In VS Code, select the same interpreter if imports show as missing:

```text
C:\Users\Andre\AppData\Local\Programs\Python\Python312\python.exe
```

If the Crazyradio is not detected on Windows, install the Bitcraze USB driver with Zadig:

https://www.bitcraze.io/documentation/repository/crazyradio-firmware/master/building/usbwindows/

## Files

- `testlogs.py` connects to the Crazyflie, changes a parameter, and logs roll, pitch, and yaw.
- `testflying.py` is a low-level motor thrust test. Run it with propellers removed.
- `motion_flying.py` is for higher-level movement with `MotionCommander`. Use it only when your positioning deck or positioning system is working.

## Good Starting Order

1. First prove the hardware connection in the Crazyflie client.
   Guide: https://www.bitcraze.io/documentation/tutorials/getting-started-with-crazyflie-2-x/

2. Then study connecting, logging, and parameters. This matches `testlogs.py`.
   Guide: https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/user-guides/sbs_connect_log_param/

3. Learn the shape of the Python API: URI, `Crazyflie`, `SyncCrazyflie`, logging variables, and parameters.
   Guide: https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/user-guides/python_api/

4. Move to `MotionCommander` only after the basic connection and logging work.
   Guide: https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/user-guides/sbs_motion_commander/

5. Use the official examples when you want to build your own scripts.
   Examples: https://github.com/bitcraze/crazyflie-lib-python/tree/master/examples

## Suggested First Experiments

Start with scripts that do not fly:

- Print the battery voltage.
- Log roll, pitch, and yaw for 10 seconds.
- Read a parameter without changing it.
- Change LED or non-flight parameters.

Then do props-off motor tests, and only then try small flight movements. For first real flights, keep heights low, such as `0.3` to `0.5` meters, and use a clear area.
