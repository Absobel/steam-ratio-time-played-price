import steam
from decouple import config
import json

# SETUP
KEY = config("STEAM_API_KEY")
stm = steam.Steam(KEY)

STEAM_USER = 76561198142605500      # Le mien  (325+ jeux)
#STEAM_USER = 76561199038321447      # Celui de Anarof  (18 jeux)

# Paramètres
JEUX_NON_JOUES = True



# Get all games owned by the user
games = stm.users.get_owned_games(STEAM_USER)

# Séparer les jeux joués et non joués
liste = []
for game in games["games"]:
    liste.append([game["appid"], game["name"], game["playtime_forever"]])

# à supprimer quand fini de tester
f = open("games.json", "w")
info_app = stm.apps.get_app_details(liste[14][0])
dico = json.loads(info_app)
f.write(json.dumps(dico, indent=4))
f.close()
print("done")
