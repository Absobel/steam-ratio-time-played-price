import steam
from decouple import config
import json
from currency_converter import CurrencyConverter
from alive_progress import alive_bar
import pandas as pd
import time

# SETUP
KEY = config("STEAM_API_KEY")
stm = steam.Steam(KEY)

STEAM_USER = 76561198142605500      # Le mien  (325+ jeux)
#STEAM_USER = 76561199038321447      # Celui de Anarof  (18 jeux)
#STEAM_USER = 76561198383805394      # Celui de feitan
#STEAM_USER = 76561198026300020      # Celui de Anno
#STEAM_USER = 76561198831558703      # Celui de Nico
#STEAM_USER = 76561198119301466      # Celui de Louis
#STEAM_USER = 76561198263261820      # Celui d'Alexandre

c = CurrencyConverter()
pd.set_option('display.max_rows', None)

# Paramètres
JEUX_NON_JOUES = True
API_WAIT = True



# Get all games owned by the user
games = stm.users.get_owned_games(STEAM_USER)

# Séparer les jeux joués et non joués
liste = []
for game in games["games"]:
    liste.append([game["appid"], game["name"], game["playtime_forever"]])

len_liste = len(liste)
with alive_bar(len_liste) as bar:
    for i,game in enumerate(liste):
        start = time.time()
        try:
            info_app = stm.apps.get_app_details(game[0])
            if API_WAIT:
                while info_app == "null":
                    print("API limit reached, waiting 10s")
                    time.sleep(10);
                    info_app = stm.apps.get_app_details(game[0])
            dico = json.loads(info_app)
            if dico[str(game[0])]["data"]["is_free"] == False:
                price = c.convert(dico[str(game[0])]["data"]["price_overview"]["initial"] / 100, dico[str(game[0])]["data"]["price_overview"]["currency"], "EUR")
            else:
                price = 0
        except:
            print(i, " : ", game[1])
            price = None
        liste[i].append(price)
        end = time.time()
        if len_liste > 200 and not API_WAIT:
            while end - start < 2:
                time.sleep(0.1)
                end = time.time()
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

f = open("result.txt", "w")

if JEUX_NON_JOUES and len(liste_playtime0) > 0:
    f.write("Jeux non joués\n")
    f.write(str(pd.DataFrame(liste_a_afficher[0], columns=["Nom", "Prix"])))
    f.write("\n\n")
if len(liste) > 0:
    f.write("Jeux joués\n")
    f.write(str(pd.DataFrame(liste_a_afficher[1], columns=["Nom", "Temps de jeu", "Prix"])))
    f.write("\n\n")
if len(liste_prix_gratuits) > 0:
    f.write("Jeux gratuits\n")
    f.write(str(pd.DataFrame(liste_a_afficher[2], columns=["Nom", "Temps de jeu"])))
    f.write("\n\n")
if len(liste_prix_inconnus) > 0:
    f.write("Jeux dont le prix est inconnu\n")
    f.write(str(pd.DataFrame(liste_a_afficher[3], columns=["Nom", "Temps de jeu"])))
