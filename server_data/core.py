from threading import *
import socket
from server_data import jail
import ssl
from server_data import session
from server_data.sql.database import *

HOST, PORT = '192.168.1.2', 5005
context = ssl.SSLContext()
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

# dummy number
version = '0.0.1.1'


def check_version():
    global version
    my_cursor.execute("SELECT version FROM ServerParameters")
    for v in my_cursor:
        version = v[0]


def load_new_ssl_context():
    logging.info('[LOADING--SSL]: starting new SSL context using certificate data...')
    context.load_cert_chain('/etc/letsencrypt/live/asyllion.com/fullchain.pem',
                            '/etc/letsencrypt/live/asyllion.com/privkey.pem')
    context.set_ciphers('AES256+ECDH:AES256+EDH')


def bind_and_listen():
    try:
        server.bind((HOST, PORT))
        server.listen(5)
        logging.info('[ <<SOCKET>> ]: socket bind successful... now listening')
        return True
    except socket.error:
        logging.info('[   SOCKET   ]: reconnecting...')
        return False


def end_client(connection):
    try:
        connection.shutdown(socket.SHUT_RDWR)
    except socket.error:
        pass
    try:
        connection.close()
        logging.info('[    CYA!    ]: disconnected!')
    except socket.error:
        logging.info('[    CYA?    ]: ...not gracefully disconnected?')


def new_client(connection, ip_address):
    ssl_tries = 0
    ssl_failed = False
    if jail.is_perm_jailed(ip_address):
        logging.info('[   (>__<)   ]: kicking because already banned!')
        end_client(connection)
        return
    # adds short loop to repeat ssl wrapping in case of a lagging slow device on client side
    # which could break wrapping the socket thus banning unintentionally potential user
    while ssl_tries < 3:
        try:
            connection.settimeout(10)
            connection = context.wrap_socket(connection, server_side=True)
            connection.settimeout(None)
            ssl_failed = False
            logging.info('[    .SSL    ]: safe handshake approved... connected!')
            break
        except ssl.SSLError:
            logging.info('[    .SSL    ]: safe handshake wrapping ...failed!!!')
            ssl_tries += 1
            ssl_failed = True

    if ssl_failed:
        jail.ban("anon", ip_address, "no ssl", jail.PERM_BAN)
        logging.info(f'[> > >  < < <]: SSL handshake failed {ssl_tries} times, closing connection...')
        end_client(connection)
        logging.info('[   THREAD   ]: closing client thread...')
        return

    if jail.approve(connection, ip_address):
        try:
            # sends variable with current game version
            connection.send(version.encode())
        except socket.error:
            logging.info('[SEND--UPDATE]: client not receiving update info.')
            end_client(connection)
            return
        if not session.allow_stay(connection, ip_address):
            end_client(connection)


def socket_loop():
    client, address = None, None
    try:
        while True:
            try:
                client, address = server.accept()
                logging.info('-----------------------------------------------------------------------------')
                logging.info(f'[ < <    > > ]: incoming connection ...')
                t_new_client = Thread(target=new_client, args=(client, address[0]))
                t_new_client.start()
            except socket.error:
                logging.info('[ << !!!! >> ]: error while accepting connection!')
                end_client(client)
                logging.info('[ << !!!! >> ]: rejecting and closing client.')
    except socket.error as e:
        logging.info(f'[ << !!!! >> ]: SERVER CLOSING... {e}')
        server.close()
