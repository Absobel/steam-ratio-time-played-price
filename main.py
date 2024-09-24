#!/usr/bin/env python3

from collections import deque
from typing import Any, Dict, List, NamedTuple, Optional, Tuple
import os
import curses
from decouple import config
import steam_web_api as steam
import json
from currency_converter import CurrencyConverter
import pandas as pd
import time
import statistics as stats
import iterfzf as fzf

# CONSTANTS

CACHE_FOLDER = 'cache'
GAME_STATS_FILE = 'games_stats.json'
FORMATED_STATS_FILE = 'formated_stats.txt'
# TODO make these configurable
COUNTRY = "FR"
RATIO_CIBLE = 25

# CURSES UTILS

def choice(stdscr, options: List[str], title: str) -> int:
    """
    Displays a list of options to the user and prompts them to choose one.

    args:
        stdscr: The curses window object used for displaying text.
        options: A list of strings representing the options to choose from.
        title: The title to display above the options.

    returns:
        The index of the chosen option (0-based).

    """
    stdscr.clear()
    stdscr.addstr(title + '\n')
    for i, option in enumerate(options):
        stdscr.addstr(f'{i + 1}. {option}\n')
    stdscr.addstr('\nChoose an option: ')
    stdscr.refresh()

    while True:
        key = stdscr.getkey()
        if key.isdigit() and 1 <= int(key) <= len(options):
            stdscr.addstr('\n')
            return int(key) - 1

def input_strs(stdscr, prompts: List[str]) -> List[str]:
    """
    Prompts the user for multiple input strings using a curses window.
    
    args:
        stdscr: The curses window object.
        prompts: A list of prompt strings to display to the user.
    returns:
        A list of responses entered by the user corresponding to each prompt.
    """
    stdscr.clear()
    
    responses = []
    for prompt in prompts:
        stdscr.addstr(prompt + ': ')
        stdscr.refresh()
        curses.echo()
        response = stdscr.getstr().decode('utf-8')
        curses.noecho()
        responses.append(response)
        
    return responses

def input_str(stdscr, prompt: str) -> str:
    """
    Prompts the user for a single string input using the provided prompt.

    args:
        stdscr: The curses window object.
        prompt: The prompt message to display to the user.

    returns:
        The user's input as a string.
    """
    return input_strs(stdscr, [prompt])[0]

    
# OTHER UTILS

class ApiAccess(NamedTuple):
    stm: steam.Steam
    c: CurrencyConverter

def get_key(stdscr) -> str:
    """
    Retrieves the Steam API key from the environment if it exists. \\
    Otherwise, prompts the user to enter it and saves it to a .env file.
    
    args:
        stdscr: The curses window object.
        
    returns:
        The Steam API key as a string
    """
    KEY = config("STEAM_API_KEY", default=None)
    
    if KEY is None:
        stdscr.clear()
        KEY = input_str(stdscr, 'Enter your Steam API key (https://steamcommunity.com/dev/apikey): ')
        while len(KEY) != 32:
            KEY = input_str(stdscr, 'Enter a valid key (https://steamcommunity.com/dev/apikey): ')
    if not isinstance(KEY, str):
        raise Exception(f"Invalid key: {KEY}")
    
    with open('.env', 'w') as f:
        f.write(f'STEAM_API_KEY={KEY}\n')
    
    return KEY 


# CACHE

def get_cache_steam_ids() -> Optional[Dict[str, str]]:
    """
    Retrieves cached Steam IDs from the specified cache folder.

    returns:
        A dictionary mapping account names to Steam IDs if the cache folder exists, otherwise None.
    """
    if os.path.isdir(CACHE_FOLDER):
        data = {}
        for folder in os.listdir(CACHE_FOLDER):
            [name, steam_id] = folder.split('_')
            data[name] = steam_id
        return data
    else:
        return None

def add_cache_steam_id(data: Tuple[str, str]) -> None:
    """
    Creates or updates a cache directory for a given Steam user.

    args:
        data: A tuple containing the Steam user's name and ID.
    """
    if not os.path.isdir(CACHE_FOLDER):
        os.mkdir(CACHE_FOLDER)
    name = data[0]
    steam_id = data[1]
    folder_path = f'{CACHE_FOLDER}/{name}_{steam_id}'
    os.makedirs(folder_path, exist_ok=True)
    
def add_cache_all_games_stats(data: List[Dict[str, Any]], user_cache_folder: str) -> None:
    """
    Writes a list of game stats to a cache file.
    
    args:
        data: A json object containing the game stats.
        user_cache_folder: The name of the cache folder for the user.
    """
    with open(f"{CACHE_FOLDER}/{user_cache_folder}/{GAME_STATS_FILE}", "w", encoding='utf-8') as file:
        json.dump(data, file, indent=4)
        
def get_cache_all_games_stats(user_cache_folder: str) -> List[Dict[str, Any]]:
    """
    Retrieves game stats from a specific user's cache folder.
    
    args:
        folder_cache_name: The name of the cache folder for the user.
        
    returns:
        The converted json object containing the game stats.
    """
    with open(f"{CACHE_FOLDER}/{user_cache_folder}/{GAME_STATS_FILE}", "r", encoding='utf-8') as file:
        return json.load(file)
    
def does_cache_all_games_stats_exist(user_cache_folder: str) -> bool:
    """
    Checks if the cache file for a specific user exists.
    
    args:
        folder_cache_name: The name of the cache folder for the user.
        
    returns:
        True if the cache file exists, otherwise False.
    """
    return os.path.isfile(f'{CACHE_FOLDER}/{user_cache_folder}/{GAME_STATS_FILE}')


# FETCH/COMPUTE STATS

def all_games_info(stdscr, steam_id: str, api_access: ApiAccess) -> List[Dict[str, Any]]:
    """
    Fetches information about all games owned by a user from the Steam API.
    
    args:
        stdscr: The curses window object.
        steam_id: The Steam ID of the user.
        init_data: A named tuple containing the Steam API object and the currency converter object.
    
    returns:
        A json object containing game information.
    """
    stm = api_access.stm
    c = api_access.c
    games = stm.users.get_owned_games(steam_id)
    
    liste_jeux: list[dict[str, Any]] = []
    for game in games["games"]:
        liste_jeux.append({"appid": game["appid"], "name": game["name"], "playtime_forever": game["playtime_forever"]})
        
    is_rate_limiting = len(liste_jeux) > 200
    num_games = len(liste_jeux)
    max_width = curses.COLS // 4
    curses.curs_set(0)
    
    for i,game in enumerate(liste_jeux):
        # TODO : make it better and more informative (estimated time left, etc.)
        progress = int(i / num_games * max_width)
        progress_bar_str = "[" + "#" * progress + " " * (max_width - progress - 1) + "]"
        fraction_str = f'{i+1}/{num_games}'
        percentage_str = f'{int(i / num_games * 100)}%'
        stdscr.addstr(0, 0, ' ' * curses.COLS)
        stdscr.addstr(0, 0, f'{progress_bar_str} {fraction_str} | {percentage_str} | {game["name"]}')
        stdscr.refresh()
        
        start = time.time()
        
        dico = stm.apps.get_app_details(game["appid"], country=COUNTRY, filters="basic,price_overview")
        if dico is None:
            time.sleep(1)
            dico = stm.apps.get_app_details(game["appid"], country=COUNTRY, filters="basic,price_overview")
            if dico is None:
                raise Exception("Probably rate limiting idk")
        dico = dico[str(game["appid"])]
        
        if "data" not in dico:
            liste_jeux[i]["error"] = "No store page"
            continue
        
        is_payant = not dico["data"]["is_free"]
        
        if is_payant and "price_overview" not in dico["data"]:
            liste_jeux[i]["error"] = "Not standalone"
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
    
    curses.curs_set(1)
    return liste_jeux    

# TODO : factorize the way to display each type of game stats
def write_formated_stats_cache(user_cache_folder: str):
    """
    Computes and writes the full stats to a cache file.
    
    args:
        user_cache_folder: The name of the cache folder for the user.
    """
    json_stats = get_cache_all_games_stats(user_cache_folder)
    liste_norm = []
    liste_playtime0 = []
    liste_prix_inconnus = []
    liste_prix_gratuits = []
    for game in json_stats:
        if "price" not in game:
            liste_prix_inconnus.append(game)
        elif game["price"] == 0:
            liste_prix_gratuits.append(game)
        elif game["playtime_forever"] == 0:
            liste_playtime0.append(game)
        else:
            liste_norm.append(game)
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
        temps_vise_float = game["price"] * RATIO_CIBLE
        if temps_vise_float > 60:
            temps_vise = "{:.2f}".format(temps_vise_float/60) + "h"
        else:
            temps_vise = "{:.2f}".format(temps_vise_float) + "min"
        liste_a_afficher[0].append([game["name"],"{:.2f}".format(game["price"])+ "€", temps_vise])
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

    liste_a_afficher.append([])
    for game in liste_prix_inconnus:
        liste_a_afficher[3].append([game["name"], "{:.2f}".format(game["playtime_forever"]/60)+"h", game["error"]])
        temps_total += game["playtime_forever"]

    with open(f"{CACHE_FOLDER}/{user_cache_folder}/{FORMATED_STATS_FILE}", "w", encoding='utf-8') as f:
        if len(liste_prix_inconnus) > 0:
            f.write("Games which price is unknown\n")
            f.write(str(pd.DataFrame(liste_a_afficher[3], columns=["Name", "Playtime", "Reason"])))
            f.write("\n\n")
        if len(liste_prix_gratuits) > 0:
            f.write("Jeux gratuits\n")
            f.write(str(pd.DataFrame(liste_a_afficher[2], columns=["Name", "Playtime"])))
            f.write("\n\n")
        if len(liste_playtime0) > 0:
            f.write("Jeux non joués\n")
            f.write(str(pd.DataFrame(liste_a_afficher[0], columns=["Name", "Price", "Target playtime"])))
            f.write("\n\n")
        if len(liste_norm) > 0:
            f.write("Jeux joués\n")
            f.write(str(pd.DataFrame(liste_a_afficher[1], columns=["Name", "Playtime", "Price", "Ratio (min/€)", "Remaining playtime"])))
            f.write("\n\n")

        f.write("Mean ratio : " + "{:.2f}".format(stats.mean(liste_ratios)) + "\n")
        f.write("Median ratio : " + "{:.2f}".format(stats.median(liste_ratios)) + "\n")
        f.write("\n")
        f.write("Total playtime : " + "{:.2f}".format(temps_total/60) + "h\n")
        f.write("Total price : " + "{:.2f}".format(prix_total) + "€\n")

# TODO : better display, feels too cramped + factorize with previous function
def display_stats_for_one_game(stdscr, game_infos: List[Dict[str, Any]], selected: str):
    """
    Computes and displays the full stats for a single game from the cache.
    
    args:
        stdscr: The curses window object.
        game_infos: A json object containing the game stats.
        selected: The name of the game.
    """
    stdscr.clear()
    for game in game_infos:
        if game['name'] == selected:
            if "price" not in game:
                a_afficher = [[game["name"], "{:.2f}".format(game["playtime_forever"]/60)+"h", game["error"]]]
                stdscr.addstr(f"Price is unknown for {selected}\n\n")
                stdscr.addstr(pd.DataFrame(a_afficher, columns=["Name", "Playtime", "Reason"]).to_string(index=False))
            elif game["price"] == 0:
                a_afficher = [[game["name"], "{:.2f}".format(game["playtime_forever"]/60)+"h"]]
                stdscr.addstr(f"{selected} is free\n\n")
                stdscr.addstr(pd.DataFrame(a_afficher, columns=["Name", "Playtime"]).to_string(index=False))
            elif game["playtime_forever"] == 0:
                temps_vise_float = game["price"] * RATIO_CIBLE
                if temps_vise_float > 60:
                    temps_vise = "{:.2f}".format(temps_vise_float/60) + "h"
                else:
                    temps_vise = "{:.2f}".format(temps_vise_float) + "min"
                a_afficher = [[game["name"], "{:.2f}".format(game["price"])+"€", temps_vise]]
                stdscr.addstr(f"{selected} has not been played\n\n")
                stdscr.addstr(pd.DataFrame(a_afficher, columns=["Name", "Price", "Targeted Playtime"]).to_string(index=False))
            else:
                ratio = game["playtime_forever"]/game["price"]
                if ratio < RATIO_CIBLE:
                    temps_vise_float = game["price"] * RATIO_CIBLE - game["playtime_forever"]
                    if temps_vise_float > 60:
                        temps_vise = "{:.2f}".format(temps_vise_float/60) + "h"
                    else:
                        temps_vise = "{:.2f}".format(temps_vise_float) + "min"
                else:
                    temps_vise = "N/A"
                a_afficher = [[game["name"], "{:.2f}".format(game["playtime_forever"]/60)+"h", "{:.2f}".format(game["price"])+"€", "{:.2f}".format(ratio), temps_vise]]
                stdscr.addstr(pd.DataFrame(a_afficher, columns=["Name", "Playtime", "Price", "Ratio (min/€)", "Target remaining time"]).to_string(index=False))
    pass

# TODO : factorize the way to update each type of game stats
def update_info_game(game_infos: List[Dict[str, Any]], selected: str, name: str, steam_id: str, api_access: ApiAccess):
    """
    Fetches and updates the stats for a single game in cache from the Steam API.
    
    args:
        game_infos: A json object containing the game stats.
        selected: The name of the game.
        name: The name of the user.
        steam_id: The Steam ID of the user.
        init_data: A named tuple containing the Steam API object and the currency converter object.
    """
    stm = api_access.stm
    c = api_access.c
    folder_cache_name = f'{name}_{steam_id}'
    games = stm.users.get_owned_games(steam_id)
    for game in games["games"]:
        if game["name"] == selected:
            playtime_selected = game["playtime_forever"]
    
    for game in game_infos:
        if game['name'] == selected:
            dico = stm.apps.get_app_details(game["appid"], country=COUNTRY, filters="basic,price_overview")
            if dico is None:
                time.sleep(1)
                dico = stm.apps.get_app_details(game["appid"], country=COUNTRY, filters="basic,price_overview")
                if dico is None:
                    raise Exception("Probably rate limiting idk")
            dico = dico[str(game["appid"])]

            if "data" not in dico:
                game["error"] = "No store page"
                break

            is_payant = not dico["data"]["is_free"]

            if is_payant and "price_overview" not in dico["data"]:
                game["error"] = "Not standalone"
                break

            if is_payant:
                price = c.convert(
                    dico["data"]["price_overview"]["initial"] / 100, 
                    dico["data"]["price_overview"]["currency"], 
                    "EUR"
                )
            else:
                price = 0

            game["price"] = price
            game["playtime_forever"] = playtime_selected # type: ignore
    add_cache_all_games_stats(game_infos, folder_cache_name)


# MAIN

def init(stdscr) -> ApiAccess:
    """
    Initializes needed data for the application.
    
    args:
        stdscr: The curses window object.
        
    returns:
        A named tuple containing the Steam API object and the currency converter object.
    """
    KEY = get_key(stdscr)
    pd.set_option('display.max_rows', None)
    
    stm = steam.Steam(KEY)
    c = CurrencyConverter()
        
    return ApiAccess(stm, c)

def main(stdscr):
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    os.chdir(script_dir)
   
    init_data = init(stdscr)
    
    stdscr.clear()

    # STEAM ID CHOICE
    maybe_steam_ids: Optional[Dict[str, str]] = get_cache_steam_ids()
    if maybe_steam_ids:
        steam_id_options = []
        for name, steam_id in maybe_steam_ids.items():
            steam_id_options.append(f'{name} : {steam_id}')
        steam_id_options.append('Add SteamID')
    else:
        steam_id_options = ['Add SteamID']
    steam_id_choice = choice(stdscr, steam_id_options, 'Select SteamID')
    
    if steam_id_options[steam_id_choice] == 'Add SteamID':
        [name, steam_id] = input_strs(stdscr, ['Enter name of the account (just for clarity, you can put whatever)', 'Enter SteamID'])
        while len(steam_id) != 17 or not steam_id.isdigit():
            steam_id = input_str(stdscr, 'Invalid SteamID. Please enter a valid SteamID')
        add_cache_steam_id((name, steam_id))
    else:
        name, steam_id = steam_id_options[steam_id_choice].split(' : ')

    cache_folder_name = f'{name}_{steam_id}'
    
    # MODE CHOICE
    
    while True:
        # TODO : make the option clearer
        mode_options = ['One Game', 'All Games', 'Cached Games', 'Global Stats', "Quit"]
        mode_choice = choice(stdscr, mode_options, 'Select Mode')    
        stdscr.clear()
        match mode_options[mode_choice]:
            case 'One Game':
                if does_cache_all_games_stats_exist(cache_folder_name):
                    game_infos = get_cache_all_games_stats(cache_folder_name)
                    all_game_names = [game['name'] for game in game_infos]
                    selected = fzf.iterfzf(all_game_names)
                    if isinstance(selected, str):
                        update_info_game(game_infos, selected, name, steam_id, init_data)
                        display_stats_for_one_game(stdscr, game_infos, selected)
                    else:
                        stdscr.addstr('Problem with the game selection')
                else:
                    stdscr.addstr('No cached data for this account. Please run "All Games" mode first.')
            case 'All Games':
                game_infos = all_games_info(stdscr, steam_id, init_data)
                add_cache_all_games_stats(game_infos, cache_folder_name)
                write_formated_stats_cache(cache_folder_name)
                stdscr.clear()
                stdscr.addstr(f"You will find the formated stats in : {CACHE_FOLDER}/{cache_folder_name}/{FORMATED_STATS_FILE}")
            case 'Cached Games':
                if does_cache_all_games_stats_exist(cache_folder_name):
                    write_formated_stats_cache(cache_folder_name)
                    stdscr.clear()
                    stdscr.addstr(f"You will find the formated stats in : {CACHE_FOLDER}/{cache_folder_name}/{FORMATED_STATS_FILE}")
                else:
                    stdscr.addstr('No cached data for this account. Please run "All Games" mode first.')
            case 'Global Stats':
                if does_cache_all_games_stats_exist(cache_folder_name):
                    with open(f"{CACHE_FOLDER}/{cache_folder_name}/{FORMATED_STATS_FILE}", "r", encoding='utf-8') as f:
                        for line in deque(f, maxlen=5):
                            stdscr.addstr(line)
                else:
                    stdscr.addstr('No cached data for this account. Please run "All Games" mode first.')
            case 'Quit':
                break

        # To keep the app open until the user presses a key
        stdscr.refresh()
        stdscr.getkey()

if __name__ == '__main__':
    curses.wrapper(main)