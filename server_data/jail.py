import socket
import datetime
from server_data.sql.database import *

SOFT_BAN, TEMP_BAN, HARD_BAN, PERM_BAN = 60, 1440, 10080, 65535
ban_cursor = db.cursor(buffered=True)


def verify_client(client, address):
    verify = False
    data = None
    try:
        client.settimeout(5)
        data = client.recv(100)
        client.settimeout(None)
        try:
            data = data.decode()
        except socket.error:
            data = "corrupted data"
            logging.info('[    JAIL    ]: could not decode packet because too big or corrupted... banning!')
            ban("anon", address, "corrupted data", PERM_BAN)
    except socket.error:
        logging.info('[    JAIL    ]: could not receive any data, possible stalking or spoofing... banning!')
        ban("anon", address, "no data", TEMP_BAN)
    if data:
        if data == '-Cl13NT-G4ME-T0K3N-':
            logging.info('[    -OK-    ]: client token received!')
            verify = True
        else:
            logging.info('[    JAIL    ]: forbidden data incoming...')
            ban("anon", address, "forbidden data: " + data, PERM_BAN)
    return verify


def is_perm_jailed(ip_address):
    jail = False
    my_cursor.execute(f"SELECT ban, userIP FROM Prisoners")
    for p in my_cursor:
        if p[0] == PERM_BAN:
            if p[1] == ip_address:
                jail = True
    return jail


def is_temp_jailed(account):
    jail = False
    my_cursor.execute(f"SELECT ban, target FROM Prisoners")
    for p in my_cursor:
        if p[0] != PERM_BAN:
            if p[1] == account:
                jail = True
    return jail


def approve(client, address):
    logging.info('[    ....    ]: analysing data ...')
    if verify_client(client, address):
        return True
    else:
        logging.info('[  JAILING!  ]: address not allowed! Closing connection!')
        return False


def ban(target, _address, _data, _time):
    my_cursor.execute(ban_query, (target, _address, _data, _time, datetime.now()))
    db.commit()
    logging.info('[  JAILING!  ]: added IP to the ban list')


def run_guard():
    _usr, _ban, _userIP = 0, 1, 2
    my_cursor.execute("SELECT target, ban, userIP FROM Prisoners")
    for prison in my_cursor:
        if prison[_ban] != PERM_BAN:
            if prison[_ban] > 0:
                ban_time = prison[_ban] - 1
                ban_cursor.execute(reduce_ban, (ban_time, prison[_userIP]))
            if prison[_ban] == 0:
                ban_cursor.execute(release_prisoner, (prison[_userIP],))
                logging.info(f'[ JAIL-GUARD ]: releasing prisoner [{prison[_usr]}] from jail!')
    db.commit()
