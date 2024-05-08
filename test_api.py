import steam_web_api as steam
from decouple import config
import json

# SETUP
KEY = config("STEAM_API_KEY")
stm = steam.Steam(KEY) # type: ignore

STEAM_USER = "76561198142605500"

# Paramètres
JEUX_NON_JOUES = True

# Get all games owned by the user
games = stm.users.get_owned_games(STEAM_USER)

f = open("games.json", "w")
f.write(json.dumps(games))
f.close()
print("done")
