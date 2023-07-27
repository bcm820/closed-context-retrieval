from jarvis.config import Config
from jarvis.llama import Llama
from jarvis.redis import RedisDB
from jarvis.bot import Bot
from jarvis.cogs import Messaging, Bookmarks


class App:
    def __init__(self, conf: Config) -> None:
        llama = Llama(conf)
        rdb = RedisDB(conf)
        self.bot = Bot(llama, rdb)

    def run(self):
        self.bot.run(Messaging, Bookmarks)
