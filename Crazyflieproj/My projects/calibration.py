import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.utils import uri_helper

ESTIMATOR_AUTO = 0
ESTIMATOR_COMPLEMENTARY = 1
ESTIMATOR_KALMAN = 2


def param_stab_est_callback(name, value):
    print('The crazyflie has parameter ' + name + ' set at number: ' + value)


def set_estimator(cf, estimator=ESTIMATOR_KALMAN):
    cf.param.add_update_callback(group='stabilizer', name='estimator',
                                 cb=param_stab_est_callback)
    cf.param.set_value('stabilizer.estimator', estimator)
    time.sleep(0.5)


def simple_param_async(scf, groupstr, namestr):
    cf = scf.cf
    full_name = groupstr + '.' + namestr

    cf.param.add_update_callback(group=groupstr, name=namestr,
                                 cb=param_stab_est_callback)
    time.sleep(1)
    cf.param.set_value(full_name, 2)
    time.sleep(1)
    cf.param.set_value(full_name, 1)
    time.sleep(1)
