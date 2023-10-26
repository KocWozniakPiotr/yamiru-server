import datetime
import socket
from server_data.sql.database import *
from server_data import jail
import time
from threading import *
from cryptography.fernet import Fernet
from random import randint as r
from server_data.handlers.player import PlayerHandler

users_online = []


def create_secret(_date):
    key = Fernet.generate_key()
    data = bytes(str(_date), encoding='utf8')
    return str(key)[2:46], str(Fernet(key).encrypt(data))[2:122]


def decode_secret(client_key, data):
    key = bytes(client_key, encoding='utf8')
    data = bytes(data, encoding='utf8')
    _secret = None
    try:
        _secret = Fernet(key).decrypt(data)
        # logging.info(f'[   SECRET   ]: secret contains: [{str(_secret)[2:28]}]')
    except Fernet:
        logging.info(f'[   SECRET   ]: failed to decrypt secret data')
    return str(_secret)[2:28]


def try_reconnect(_id):
    reconnecting = 0
    online_cursor = db.cursor()
    while reconnecting < 15:
        online_cursor.execute("SELECT id, online FROM Accounts")
        for p in online_cursor:
            if _id == p[0]:
                if p[1] == '1':
                    logging.info(f'[   LOG-IN   ]: account [{_id}] awaits reconnecting because of active backup...')
                elif p[1] == '0':
                    logging.info(f'[   LOG-IN   ]: backup finished, account [{_id}] is ready to connect...')
                    online_cursor.close()
                    return 'online'
        reconnecting += 1
        time.sleep(2)
    online_cursor.close()
    return None


def login(client_key):
    usr_status = None
    if client_key == 'empty':
        logging.info(f'[   HELLO!   ]: client asked for new account, so creating...')
        usr_status = 'creating'
        _creation_date = str(datetime.now())
        logging.info(f'[   SECRET   ]: creating key and secret')
        client_key, server_secret = create_secret(_creation_date)
        logging.info(f'[  +ACCOUNT  ]: generating account using secret')
        my_cursor.execute(new_account, (_creation_date, server_secret))
        db.commit()
        user_id = str(my_cursor.lastrowid)
        client_key = client_key + user_id
    elif client_key[:6] == 'notify':
        user_id = client_key[6:]
        if user_id not in users_online:
            logging.info(f'[   HELLO!   ]: account [{user_id}] asked for notifications...')
            usr_status = 'notify'
        else:
            logging.info(f'[   HELLO!   ]: user [{user_id}] asked for notifications, but is still ingame')
    else:
        formatted_key = client_key[:44]
        user_id = client_key[44:]
        logging.info(f'[   HELLO!   ]: account [{user_id}] tries log-in with a key...')
        my_cursor.execute("SELECT id, creation, secret, online, nick FROM Accounts")

        for p in my_cursor:
            if int(user_id) == p[0]:
                logging.info(f'[  +ACCOUNT  ]: found account in database')
                _creation_date = decode_secret(formatted_key, p[2])
                if _creation_date == p[1]:
                    if jail.is_temp_jailed(user_id):
                        logging.info(f'[   (U__U)   ]: account [{user_id}] already banned, so kicking!')
                        usr_status = 'banned'
                        break
                    else:
                        user_nick = p[4]
                        if p[3] == '0':
                            if user_nick is None:
                                logging.info(
                                    f'[   LOG-IN   ]: account [{user_id}] online, but still on in-game setup')
                                usr_status = 'setup'
                                break
                            else:
                                logging.info(f'[   LOG-IN   ]: account [{user_id}] with a nick [{p[4]}] logged in game!')
                                usr_status = 'entering'
                                break
                        else:
                            logging.info(f'[   LOG-IN   ]: account [{user_id}] awaits logging in...')
                            if try_reconnect(int(user_id)) == 'online':
                                if user_nick is None:
                                    usr_status = 'setup'
                                else:
                                    usr_status = 'entering'
                            else:
                                usr_status = None
                            break
                else:
                    logging.info(f'[   LOG-IN   ]: failed to log-in with key [{p[2]}]')
                    usr_status = 'attempting'
                    break

    return usr_status, user_id, client_key


def allow_stay(connection, ip):
    try:
        data = connection.recv(2048)
    except socket.error:
        return False
    if not data:
        return False
    else:
        usr_status, user_id, client_key = login(data.decode())
        if usr_status is None:
            return False
        elif usr_status == 'attempting':
            # tries += 1
            connection.send('tries'.encode())
            # if tries >= 3:
                # jail.ban(user_id, ip, "login failed", jail.SOFT_BAN)
                # connection.send('soft_ban'.encode())
                # return False
            return False
        elif usr_status == 'banned':
            connection.send(usr_status.encode())
            return False
        elif usr_status == 'notify':
            notify_client(connection, user_id)
            return False
        elif usr_status == 'creating':
            # Sends a key to client when creating a new account
            connection.send(client_key.encode())
            time.sleep(0.1)
            connection.send(usr_status.encode())
            us = UserSession(usr_status, user_id, connection)
            return True
        elif usr_status == 'setup':
            connection.send(usr_status.encode())
            us = UserSession(usr_status, user_id, connection)
            return True
        elif usr_status == 'entering':
            connection.send(usr_status.encode())
            us = UserSession(usr_status, user_id, connection)
            return True


def notify_client(connection, user_id):
    ids = ''
    # This is only for testing purposes. Make a proper reading of SQL notifications of the player
    # Messages should be sent as string numbers separated by SPACE
    messages = r(0, 3)
    for m in range(messages):
        n = str(r(1, 9))
        while n in ids:
            n = str(r(1, 9))
        ids += str(n) + ' '
    # Check in sql user id and his data for notifications to send

    # ids are temporary 0 to mute notifications client side
    # for testing comment line with ids = 0
    #ids = '0'
    try:
        connection.send(ids.encode())
        if ids == '0':
            logging.info(f'[  SESSION>  ]: no available notifications for account: [{user_id}]')
        else:
            logging.info(f'[  SESSION>  ]: successfully sent {messages} notifications to account: [{user_id}]')
    except socket.error:
        logging.info(f'[  SESSION>  ]: failed sending notifications to account: [{user_id}]')


class UserSession:

    def __init__(self,usr_status, user_id, connection):
        self.status = usr_status
        self.usr_id = user_id
        self.con = connection
        self.player = PlayerHandler(user_id)
        self.start_data_session()

    # separate this method into more sending sessions... one for chat, one for others stuff, etc.
    def start_data_session(self):
        online_cursor = db.cursor()
        if self.status is 'entering':
            online_cursor.execute(update_oline_status, ['1', self.usr_id])
            db.commit()
            online_cursor.close()
            logging.info(f'[  SESSION>  ]: account: [{self.usr_id}] is now online')
            users_online.append(self.usr_id)
        t_transfer_data = Thread(target=self.transfer_data)
        t_transfer_data.start()

    def transfer_data(self):
        tries = 0
        responding = True
        while True:
            if self.status is 'entering':
                try:
                    self.con.settimeout(10)
                    packet = self.con.recv(256).decode()
                    self.con.settimeout(None)
                    self.translate(packet)
                    self.con.send('0'.encode())
                    tries = 0
                    if not responding:
                        responding = True
                        logging.info(f'[  SESSION>  ]: account: [{self.usr_id}] is back online!')
                except socket.error as e:
                    if responding:
                        responding = False
                        logging.info(f'[  SESSION>  ]: account: [{self.usr_id}] unreachable! Awaiting reconnect...')
                    if not responding:
                        tries += 1
                    time.sleep(3)
                if tries > 2:
                    self.end_user_connection()
                    logging.info(f'[  SESSION>  ]: connection for account: [{self.usr_id}] closed. Starting user backup...')
                    t_store_account_data = Thread(target=self.store_account_data)
                    t_store_account_data.start()
                    break
            else:
                try:
                    self.con.settimeout(5)
                    packet = self.con.recv(256).decode()
                    self.con.settimeout(None)
                    self.translate(packet)
                    self.con.send('0'.encode())
                except socket.error as e:
                    self.end_user_connection()
                    logging.info(f'[  SESSION>  ]: account: [{self.usr_id}] unreachable! Setup/Creating so disconnecting asap...')
                    break

    def translate(self, packet):
        if len(packet) > 0:
            header = packet[0]
            if header == 'c':  # CHAT
                # private chat
                pass
            elif header == 'm':  # MOVEMENT
                # move character to destined position on the map
                pass
            elif header == 'a':  # ACTION
                # activate an action or skill which player send request for
                pass
            elif header == 'p':  # PLAYER
                # update player stats
                logging.info(f'[   PACKET   ]: incoming packet [ {packet} ]')
                self.return_packet(self.player.update(packet))
            elif header == 'i':  # INVENTORY
                # update inventory functions
                pass
            elif header == 'd':  # DROP
                # display received drop
                pass
            elif header == 'g':  # GUILD
                # receive guild info
                pass

    def return_packet(self, content):
        # logging.info(f'[   PACKET   ]: sending packet [ {content} ] back to user')
        if content is not None:
            try:
                self.con.send(content.encode())
                logging.info(f'[   PACKET   ]: packet was sent to user successfully')
            except:
                logging.info(f'[   PACKET   ]: failed sending packet to user')
        else:
            logging.info(f'[   PACKET   ]: ups ...content of the packet is NONE !')

    # stores all dynamic data of a user/account after logout/disconnect - level, exp, inventory etc.
    def store_account_data(self):
        offline_cursor = db.cursor()
        logging.info(f'[  <SESSION  ]: saving session user-data from account [{self.usr_id}] ...')
        offline_cursor.execute(update_oline_status, ['0', self.usr_id])
        db.commit()
        offline_cursor.close()
        users_online.pop(users_online.index(self.usr_id))
        logging.info(f'[  <SESSION  ]: account: [{self.usr_id}] status is offline.')

        # list.append() and list.pop() are threadsafe methods, anything else could output false data
        # online_users.pop(online_users.index(account))  # this should probably NOT run in a thread loop !!!

    def end_user_connection(self):
        try:
            self.con.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        logging.info('[  BYE-BYE!  ]: user disconnected from server.')
        self.con.close()








