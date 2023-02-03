import steam
from decouple import config
import json
from currency_converter import CurrencyConverter
from alive_progress import alive_bar
import pandas as pd

# SETUP
KEY = config("STEAM_API_KEY")
stm = steam.Steam(KEY)

STEAM_USER = 76561198142605500      # Le mien  (325+ jeux)
#STEAM_USER = 76561199038321447      # Celui de Anarof  (18 jeux)

c = CurrencyConverter()
pd.set_option('display.max_rows', None)

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
info_app = stm.apps.get_app_details(liste[0][0])
dico = json.loads(info_app)
f.write(json.dumps(dico, indent=4))
f.close()
print("done")


with alive_bar(len(liste)) as bar:
    for i,game in enumerate(liste):
        try:
            info_app = stm.apps.get_app_details(game[0])
            dico = json.loads(info_app)
            if dico[str(game[0])]["data"]["is_free"] == False:
                try:
                    price = c.convert(dico[str(game[0])]["data"]["price_overview"]["initial"] / 100, dico[str(game[0])]["data"]["price_overview"]["currency"], "EUR")
                except:
                    price = None
            else:
                price = 0
        except:
            print(i, " : ", game[1])
            price = None
        liste[i].append(price)
        bar()
# liste : [appid, name, playtime_forever, price]

liste_playtime0 = []
liste_prix_inconnus = []
liste_prix_gratuits = []
with alive_bar(len(liste)) as bar:
    for i, game in enumerate(liste):
        if game[3] == None:
            liste[i] = None
            liste_prix_inconnus.append(game)
        elif game[3] == 0:
            liste[i] = None
            liste_prix_gratuits.append(game)
        elif game[2] == 0:
            liste[i] = None
            liste_playtime0.append(game)
        bar()
liste = [x for x in liste if x != None]
liste.sort(key=lambda x: x[2]/x[3])
liste_playtime0.sort(key=lambda x: x[3], reverse=True)
liste_prix_gratuits.sort(key=lambda x: x[2])
liste_prix_inconnus.sort(key=lambda x: x[2])

# Affichage
liste_a_afficher = []

liste_a_afficher.append([])
for game in liste_playtime0:
    liste_a_afficher[0].append([game[1],"{:.2f}".format(game[3])+ "€"])

liste_a_afficher.append([])
for game in liste:
    liste_a_afficher[1].append([game[1], "{:.2f}".format(game[2]/60)+"h", "{:.2f}".format(game[3])+"€"])

liste_a_afficher.append([])
for game in liste_prix_gratuits:
    liste_a_afficher[2].append([game[1], "{:.2f}".format(game[2]/60)+"h"])

liste_a_afficher.append([])
for game in liste_prix_inconnus:
    liste_a_afficher[3].append([game[1], "{:.2f}".format(game[2]/60)+"h"])

if JEUX_NON_JOUES and len(liste_playtime0) > 0:
    print("Jeux non joués")
    print(pd.DataFrame(liste_a_afficher[0], columns=["Nom", "Prix"]))
    print()
if len(liste) > 0:
    print("Jeux joués")
    print(pd.DataFrame(liste_a_afficher[1], columns=["Nom", "Temps de jeu", "Prix"]))
    print()
if len(liste_prix_gratuits) > 0:
    print("Jeux gratuits")
    print(pd.DataFrame(liste_a_afficher[2], columns=["Nom", "Temps de jeu"]))
    print()
if len(liste_prix_inconnus) > 0:
    print("Jeux dont le prix est inconnu")
    print(pd.DataFrame(liste_a_afficher[3], columns=["Nom", "Temps de jeu"]))