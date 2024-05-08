import steam_web_api as steam
from decouple import config
import json
from currency_converter import CurrencyConverter
from alive_progress import alive_bar
import pandas as pd
import time
from typing import Any
import statistics as stats

# SETUP
KEY = config("STEAM_API_KEY")
stm = steam.Steam(KEY) # type: ignore

MON_STEAM_USER = "76561198142605500"    # (500+ entrées)

STEAM_USER = MON_STEAM_USER
# STEAM_USER = "76561199038321447"      # Celui de Anarof
# STEAM_USER = "76561198383805394"      # Celui de feitan
# STEAM_USER = "76561198026300020"      # Celui de Anno
# STEAM_USER = "76561198831558703"      # Celui de Nico
# STEAM_USER = "76561198119301466"      # Celui de Louis
# STEAM_USER = "76561198263261820"      # Celui d'Alexandre
# STEAM_USER = "76561198913575906"      # Celui de JM
# STEAM_USER = "76561198338124856"      # Celui de JP
# STEAM_USER = "76561198119301466"      # Celui de Louis

c = CurrencyConverter()
pd.set_option('display.max_rows', None)

# Paramètres
JEUX_NON_JOUES = True
COUNTRY = "FR"
RATIO_CIBLE = 25

# Get all games owned by the user
games = stm.users.get_owned_games(STEAM_USER)

# Séparer les jeux joués et non joués
liste_jeux: list[dict[str, Any]] = []
for game in games["games"]:
    liste_jeux.append({"appid": game["appid"], "name": game["name"], "playtime_forever": game["playtime_forever"]})

is_rate_limiting = len(liste_jeux) > 200
with alive_bar(len(liste_jeux), enrich_print=False) as bar:
    for i,game in enumerate(liste_jeux):
        start = time.time()
        
        dico = stm.apps.get_app_details(game["appid"], country=COUNTRY, filters="basic,price_overview")
        if dico is None:
            print("Unknown Error, trying again...")
            time.sleep(1)
            dico = stm.apps.get_app_details(game["appid"], country=COUNTRY, filters="basic,price_overview")
            if dico is None:
                print("Probably rate limiting idk, exiting...")
                exit(1)
        dico = dico[str(game["appid"])]
         
        if "data" not in dico:
            print("No store page  : ", game["name"])
            bar()
            continue
        
        is_payant = not dico["data"]["is_free"]
        
        if is_payant and "price_overview" not in dico["data"]:
            print("Not standalone : ", game["name"])
            bar()
            continue
        
        if is_payant:
            price = c.convert(
                dico["data"]["price_overview"]["initial"] / 100, 
                dico["data"]["price_overview"]["currency"], 
                "EUR"
            )
        else:
            price = 0
            
        liste_jeux[i]["price"] = price
        
        end = time.time()
        if is_rate_limiting:
            while end - start < 2:
                time.sleep(0.1)
                end = time.time()
        bar()
# game : [appid, name, playtime_forever, price]

liste_norm = []
liste_playtime0 = []
liste_prix_inconnus = []
liste_prix_gratuits = []
with alive_bar(len(liste_jeux)) as bar:
    for i, game in enumerate(liste_jeux):
        if "price" not in game:
            liste_prix_inconnus.append(game)
        elif game["price"] == 0:
            liste_prix_gratuits.append(game)
        elif game["playtime_forever"] == 0:
            liste_playtime0.append(game)
        else:
            liste_norm.append(game)
        bar()
liste_norm.sort(key=lambda x: x["playtime_forever"]/x["price"], reverse=True)
liste_playtime0.sort(key=lambda x: x["price"], reverse=True)
liste_prix_gratuits.sort(key=lambda x: x["playtime_forever"], reverse=True)
liste_prix_inconnus.sort(key=lambda x: x["playtime_forever"], reverse=True)

# Affichage
liste_a_afficher = []
temps_total = 0
prix_total = 0
liste_ratios = []

liste_a_afficher.append([])
for game in liste_playtime0:
    liste_a_afficher[0].append([game["name"],"{:.2f}".format(game["price"])+ "€"])
    prix_total += game["price"]

liste_a_afficher.append([])
for game in liste_norm:
    ratio = game["playtime_forever"]/game["price"]
    if ratio < RATIO_CIBLE:
        temps_vise_float = game["price"] * RATIO_CIBLE - game["playtime_forever"]
        if temps_vise_float > 60:
            temps_vise = "{:.2f}".format(temps_vise_float/60) + "h"
        else:
            temps_vise = "{:.2f}".format(temps_vise_float) + "min"
    else:
        temps_vise = "N/A"
    liste_a_afficher[1].append([game["name"], "{:.2f}".format(game["playtime_forever"]/60)+"h", "{:.2f}".format(game["price"])+"€", "{:.2f}".format(ratio), temps_vise])
    temps_total += game["playtime_forever"]
    prix_total += game["price"]
    liste_ratios.append(ratio)

liste_a_afficher.append([])
for game in liste_prix_gratuits:
    liste_a_afficher[2].append([game["name"], "{:.2f}".format(game["playtime_forever"]/60)+"h"])
    temps_total += game["playtime_forever"]
    previous_info = game["playtime_forever"]

liste_a_afficher.append([])
for game in liste_prix_inconnus:
    liste_a_afficher[3].append([game["name"], "{:.2f}".format(game["playtime_forever"]/60)+"h"])
    temps_total += game["playtime_forever"]
    previous_info = game["playtime_forever"]

if STEAM_USER == MON_STEAM_USER:
    f = open("monresult.txt", "w")
else:
    f = open("result.txt", "w")

if len(liste_prix_inconnus) > 0:
    f.write("Jeux dont le prix est inconnu\n")
    f.write(str(pd.DataFrame(liste_a_afficher[3], columns=["Nom", "Temps de jeu"])))
    f.write("\n\n")
if len(liste_prix_gratuits) > 0:
    f.write("Jeux gratuits\n")
    f.write(str(pd.DataFrame(liste_a_afficher[2], columns=["Nom", "Temps de jeu"])))
    f.write("\n\n")
if JEUX_NON_JOUES and len(liste_playtime0) > 0:
    f.write("Jeux non joués\n")
    f.write(str(pd.DataFrame(liste_a_afficher[0], columns=["Nom", "Prix"])))
    f.write("\n\n")
if len(liste_norm) > 0:
    f.write("Jeux joués\n")
    f.write(str(pd.DataFrame(liste_a_afficher[1], columns=["Nom", "Temps de jeu", "Prix", "Ratio", "Temps restant visé"])))
    f.write("\n\n")

f.write("Ratio moyen : " + "{:.2f}".format(stats.mean(liste_ratios)) + "\n")
f.write("Ratio médian : " + "{:.2f}".format(stats.median(liste_ratios)) + "\n")
f.write("\n")
f.write("Temps total de jeu : " + "{:.2f}".format(temps_total/60) + "h\n")
f.write("Prix total : " + "{:.2f}".format(prix_total) + "€\n")
