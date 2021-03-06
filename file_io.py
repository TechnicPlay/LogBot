import json
from log_user import LogUser

USER_SAVE_PATH = "./sub_users.json"
SECRET_SAVE_PATH = "./secret.json"

def save_users(sender, new_user):
    data = []
    for user in sender.subscribed_users:
        data.append({"discord_user_id": user.discord_user_id, "steam_id_64": user.steam_id_64})

    with open(USER_SAVE_PATH, "w") as f:
        json.dump(data, f)


def load_users():
    with open(USER_SAVE_PATH, "r") as f:
        data = json.load(f)

    users = []
    for user_dict in data:
        user = LogUser(user_dict["discord_user_id"], user_dict["steam_id_64"])
        users.append(user)

    return users

def load_secret():
    with open(SECRET_SAVE_PATH, "r") as f:
        data = json.load(f)

    return (data["client_token"], data["bot_token"], data["steam_api_key"])
