try:
    import mariadb
except:
    pass
from server_data.logs.logger import *

db = mariadb.connect(
    host="127.0.0.1",
    user="your-username",
    password="your-password",
    database="LoginData"
)
my_cursor = db.cursor(buffered=True)


def _is_connected(connection):
    try:
        connection.ping()
    except connection:
        return False
    return True


def check_db_status():
    if _is_connected(db):
        logging.info('[   MY-SQL   ]: database connection active.')
    else:
        logging.info('[x  MY-SQL  x]: connection to database failed!')
        logging.info('[~~~MY-SQL~~~]: trying reconnect...')
        try:
            db.reconnect()
            logging.info('[ < MY-SQL > ]: reconnect successful!')
        except mariadb:
            logging.info('[ SQL ERROR! ]: failed to reconnect!')


ban_query = "INSERT INTO Prisoners (target, userIP, packets, ban, lastTry) VALUES (%s,%s,%s,%s,%s)"
new_account = "INSERT INTO Accounts (creation, secret) VALUES (%s,%s)"
set_nickname = "UPDATE Accounts SET nick = %s WHERE id = %s"
new_character = "INSERT INTO Characters (userID, profession, skin, level, hp, atk, def) VALUES (%s,%s,%s,%s,%s,%s,%s)"
update_oline_status = "UPDATE Accounts SET online = %s WHERE id = %s"
reduce_ban = "UPDATE Prisoners SET ban = %s WHERE userIP = %s"
release_prisoner = "DELETE FROM Prisoners WHERE userIP = %s"


# SELECT `id`, `nick`, `secret`, `online` FROM `LoginData`.`Accounts` WHERE  `id`=2;
# my_cursor.execute("SELECT id, creation, secret, online FROM Accounts WHERE id = 2") # check if correct !!!!!!!!!!!


