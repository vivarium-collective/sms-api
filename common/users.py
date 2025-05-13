from common.encryption.keydist import User, UserDb


user_db = UserDb()

test_user = User(username="JoeyD")
user_db.add_user(test_user)