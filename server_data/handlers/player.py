from server_data.list_data.lists import ListLoader
from server_data.instances.player import *
from server_data.sql.database import *
import logging

create_character = 'p00'
nick_change = 'p01'
ask_for_userdata = 'p02'

_list = ListLoader()
_list.load_bad_words_list()
profession = ProfessionInstance()

class PlayerHandler:

    def __init__(self, passed_id):
        self.player_cursor = db.cursor()
        self.id = passed_id

        self.nick = None
        self.profession = None
        self.level = None
        self.skin = None
        self.attack = None
        self.health = None
        self.defense = None

    def update(self, content):
        command = content[:3]
        parameter = content[3:]
        if command == nick_change:
            return self.change_nickname(parameter)
        elif command == create_character:
            return self.character_creation(parameter)
        elif command == ask_for_userdata:
            return self.user_data()

    def change_nickname(self, new_nickname):

        lower_nickname = new_nickname.lower()
        for word in _list.bad_words:
            word_len = len(lower_nickname)
            for x in range(word_len):
                if word in lower_nickname[x:len(word) + x]:
                    if len(word) > 1:
                        logging.info(f'[   PACKET   ]: user [{self.id}] tried changing nick using bad word: [ {word} ]')
                        return nick_change + 'forbidden words are not allowed'

        self.player_cursor.execute("SELECT id, nick FROM Accounts")
        for p in self.player_cursor:
            print(f'[{lower_nickname}] [{p[1]}]')
            if lower_nickname == p[1]:
                return nick_change + 'nickname already in use'

        self.player_cursor.execute(set_nickname, [new_nickname, self.id])
        db.commit()
        logging.info(f'[   PACKET   ]: user [{self.id}] changed nickname to [ {new_nickname} ]')
        return nick_change + 'nickname has been changed!'

    def character_creation(self, parameter):
        selected_profession = profession.get_profession[int(parameter[0])]["type"]
        selected_skin = int(parameter[1])
        _level = profession.get_profession[int(parameter[0])]["level"]
        _hp = profession.get_profession[int(parameter[0])]["hp"]
        _atk = profession.get_profession[int(parameter[0])]["atk"]
        _def = profession.get_profession[int(parameter[0])]["def"]
        selected_nick = parameter[2:]

        lower_nickname = selected_nick.lower()
        for word in _list.bad_words:
            word_len = len(lower_nickname)
            for x in range(word_len):
                if word in lower_nickname[x:len(word) + x]:
                    if len(word) > 1:
                        logging.info(f'[   PACKET   ]: user [{self.id}] tried using nick with a bad word: [ {word} ]')
                        return create_character + 'forbidden words are not allowed'

        self.player_cursor.execute("SELECT id, nick FROM Accounts")
        for p in self.player_cursor:
            if p[1] is not None:
                if lower_nickname == p[1].lower():
                    return create_character + 'nickname already in use'

        self.player_cursor.execute(set_nickname, [selected_nick, self.id])
        self.player_cursor.execute(new_character, (self.id, selected_profession, selected_skin, _level, _hp, _atk, _def))
        db.commit()
        logging.info(f'[   PACKET   ]: user [{self.id}] changed nickname to [ {selected_nick} ]')
        return create_character + 'passed'

    def user_data(self):
        self.player_cursor.execute("SELECT id, nick FROM Accounts")
        for p in self.player_cursor:
            if p[0] == int(self.id):
                self.nick = p[1]
                break
        self.player_cursor.execute("SELECT userID, skin, profession, level, atk, hp, def FROM Characters")
        for p in self.player_cursor:
            if p[0] == int(self.id):
                self.skin = p[1]
                self.profession = p[2]
                self.level = p[3]
                self.health = p[4]
                self.attack = p[5]
                self.defense = p[6]
                return ask_for_userdata + str(','.join([self.nick,str(p[1]),str(p[2]),str(p[3]),str(p[4]),str(p[5]),str(p[6])]))
