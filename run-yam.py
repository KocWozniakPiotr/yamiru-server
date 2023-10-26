import os
from server_data import core, jail
from threading import *
from server_data.sql import database
from server_data.sql.database import *

all_threads = []

def check_threats():
    _threads = active_count()
    if _threads != 4:
        logging.info(f'[   THREAD   ]: currently {str(_threads)} active threads')


def task_worker():
    hours = 0
    worker_start = time.time()
    logging.info('[TASK::WORKER]: starting jail guard...')
    while True:
        time.sleep(60)
        if round(time.time() - worker_start) > 3600:
            hours += 1
            worker_start = time.time()
            logging.info(f'[TASK::WORKER]: running already {hours} hours... active threads: {active_count()}')
            log_update()

            # add more functions like changing mobs, time of day/night, NPCs behaviour etc.
            core.check_version()
        jail.run_guard()
        check_threats()


t_core_loop = Thread(target=core.socket_loop)


def init_loop():
    while True:
        if core.bind_and_listen():
            if not t_core_loop.is_alive():
                t_core_loop.start()
                all_threads.append(t_core_loop)
            break
        time.sleep(5)


def core_thread():
    fix_tries = 0
    boot_time = time.perf_counter()
    logging.info('[  STARTING  ]: booting up server...')
    t_task_worker = Thread(target=task_worker)
    while True:
        exception_found = False
        if not t_core_loop.is_alive():
            try:
                core.load_new_ssl_context()
            except ValueError:
                logging.info(f'[    LOADING NEW SSL CONTEXT - DID NOT GO WELL...    ]')
                exception_found = True
            try:
                logging.info(f'[    CORE    ]: starting socket loop...')
                init_loop()
            except ValueError:
                logging.info('[    INITIALIZING LOOP - DID NOT GO WELL...    ]')
                exception_found = True
            try:
                database.check_db_status()
            except ValueError:
                logging.info(f'[    CHECKING DB STATUS - DID NOT GO WELL...    ]')
                exception_found = True
        if not t_task_worker.is_alive():
            try:
                t_task_worker.start()
                all_threads.append(t_task_worker)
            except ValueError:
                logging.info(f'[    STARTING TASK WORKER - DID NOT GO WELL...    ]')
                exception_found = True
            try:
                core.check_version()
            except ValueError as er:
                logging.info(f'[    CHECKING VERSION - DID NOT GO WELL...    ]')
                exception_found = True

            if not exception_found:
                logging.info(f'[  FIRMWARE  ]: current version: {str(core.version)}')
                server_started(boot_time)

        if exception_found:
            fix_tries += 1
            logging.info(f"[CORE_THREAD ]: found problems! Unsuccessful tries: {fix_tries} ")
            if fix_tries >= 10:
                logging.info(f"[CORE_THREAD ]: core_thread is corrupted, so closing...")
                break
        else:
            fix_tries = 0
        time.sleep(5)


#os.system('clear')
t_core_thread = Thread(target=core_thread)
t_core_thread.start()
all_threads.append(t_core_thread)
tries = 0

try:
    while True:
        if not t_core_thread.is_alive():
            try:
                logging.info('[ BASE--LOOP ]: base loop trying to restart core loop thread')
                t_core_thread = Thread(target=core_thread)
                t_core_thread.run()
                tries = 0
            except ThreadError as e:
                logging.info(f'[ BASE--LOOP ]: base loop could not restart core_thread: {str(e)}')
            tries += 1
        time.sleep(10)
        if tries > 10:
            break
    logging.info('[ BASE--LOOP ]: base loop ended, shutting down server...')
except KeyboardInterrupt:
    print("Server stopped")
finally:
    if core.server:
        core.server.close()
    for t in all_threads:
        t.join()

