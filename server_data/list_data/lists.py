
class ListLoader:
    bad_words = []
    other_lists = []

    def load_bad_words_list(self):
        with open('/home/ubuntu/yamiru-server/server_data/list_data/badwords.txt', 'r') as f:
            self.bad_words = f.read().rsplit()
