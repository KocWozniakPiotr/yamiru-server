import logging
import time
from datetime import datetime


def begin_log():
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    ymd = str(datetime.now())[0:10]
    y_m_d = '/home/ubuntu/yamiru-server/server_data/logs/' + ymd + '_' + str(datetime.now())[11:16]
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(message)s',
                        datefmt=ymd + ' | %H:%M:%S',
                        filename=y_m_d,
                        filemode='w')

    log = logging.StreamHandler()
    log.setLevel(logging.INFO)
    logging.getLogger().addHandler(log)
    return ymd


recent_date = begin_log()


def log_update():
    global recent_date
    if str(datetime.now())[0:10] != recent_date:
        recent_date = begin_log()


def server_started(boot_time):
    time_passed = str(round(time.perf_counter() - boot_time))
    loaded_server = f'                      GAME SERVER STARTED IN {time_passed} SECONDS                      '
    logging.info('-' * len(loaded_server))
    logging.info(loaded_server)
    logging.info('-' * len(loaded_server))
