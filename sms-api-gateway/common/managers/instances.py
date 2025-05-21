from common.managers.db import MongoManager, SqlManager
from common.managers.stream import SocketConnectionManager


mongo_manager = MongoManager()  # TODO: get dynamic url for this
sql_manager = SqlManager()
socket_manager = SocketConnectionManager()
