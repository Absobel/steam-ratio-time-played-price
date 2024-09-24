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

# TODO : Verify docstrings

# CONSTANTS

CACHE_FOLDER = 'cache'
GAME_STATS_FILE = 'games_stats.json'
FORMATED_STATS_FILE = 'formated_stats.txt'
# TODO make these configurable
COUNTRY = "FR"
RATIO_CIBLE = 25

stm: steam.Steam = None # type: ignore
c: CurrencyConverter = None # type: ignore
user_name: str = None # type: ignore
steam_id: str = None # type: ignore

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
    
def add_cache_all_games_stats(data: List[Dict[str, Any]]) -> None:
    """
    Writes a list of game stats to a cache file.
    
    args:
        data: A json object containing the game stats.
    """
    user_cache_folder = f'{user_name}_{steam_id}'
    with open(f"{CACHE_FOLDER}/{user_cache_folder}/{GAME_STATS_FILE}", "w", encoding='utf-8') as file:
        json.dump(data, file, indent=4)
    
def update_cache_one_game_stats(selected: str, data: Dict[str, Any]) -> None:
    all_game_stats = get_cache_all_games_stats()
    for i,game in enumerate(all_game_stats):
        if game['name'] == selected:
            all_game_stats[i] = data
            break
    add_cache_all_games_stats(all_game_stats)
        
def get_cache_all_games_stats() -> List[Dict[str, Any]]:
    """
    Retrieves game stats from a specific user's cache folder.
    
    args:
        folder_cache_name: The name of the cache folder for the user.
        
    returns:
        The converted json object containing the game stats.
    """
    user_cache_folder = f'{user_name}_{steam_id}'
    with open(f"{CACHE_FOLDER}/{user_cache_folder}/{GAME_STATS_FILE}", "r", encoding='utf-8') as file:
        return json.load(file)
    
def does_cache_all_games_stats_exist() -> bool:
    """
    Checks if the cache file for a specific user exists.
    
    args:
        folder_cache_name: The name of the cache folder for the user.
        
    returns:
        True if the cache file exists, otherwise False.
    """
    user_cache_folder = f'{user_name}_{steam_id}'
    return os.path.isfile(f'{CACHE_FOLDER}/{user_cache_folder}/{GAME_STATS_FILE}')


# FETCH/COMPUTE STATS

def process_stats_game(game: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes the stats for a single game from the Steam API.
    
    args:
        game: A json object containing the game stats as given by the Steam API.
    
    returns:
        A json object containing the processed game stats.
    """
  
    # dico : stats for one game
    dico = stm.apps.get_app_details(game["appid"], country=COUNTRY, filters="basic,price_overview")
    if dico is None:
        time.sleep(1)
        dico = stm.apps.get_app_details(game["appid"], country=COUNTRY, filters="basic,price_overview")
        if dico is None:
            raise Exception("Probably rate limiting idk")
    dico = dico[str(game["appid"])]
    
    processed_game = {"appid": game["appid"], "name": game["name"], "playtime_forever": game["playtime_forever"]}

    if "data" not in dico:
        processed_game["error"] = "No store page"
        return processed_game
    
    is_payant = not dico["data"]["is_free"]
    
    if is_payant and "price_overview" not in dico["data"]:
        processed_game["error"] = "Not standalone"
        return processed_game
    
    if is_payant:
        price = c.convert(
            dico["data"]["price_overview"]["initial"] / 100, 
            dico["data"]["price_overview"]["currency"], 
            "EUR"
        )
    else:
        price = 0
        
    processed_game["price"] = price
    return processed_game
    
def all_games_info(stdscr) -> List[Dict[str, Any]]:
    """
    Fetches information about all games owned by a user from the Steam API.
    
    args:
        stdscr: The curses window object.
        steam_id: The Steam ID of the user.
    
    returns:
        A json object containing game information.
    """
    games = stm.users.get_owned_games(steam_id)
    
    liste_jeux: list[dict[str, Any]] = []

    # Setup progress bar
    is_rate_limiting = len(liste_jeux) > 200
    num_games = len(games["games"])
    max_width = curses.COLS // 4
    curses.curs_set(0)
    
    for i,game in enumerate(games["games"]):
        # TODO : make it better and more informative (estimated time left, etc.)
        # Update progress bar
        progress = int(i / num_games * max_width)
        progress_bar_str = "[" + "#" * progress + " " * (max_width - progress - 1) + "]"
        fraction_str = f'{i+1}/{num_games}'
        percentage_str = f'{int(i / num_games * 100)}%'
        stdscr.addstr(0, 0, ' ' * curses.COLS)
        stdscr.addstr(0, 0, f'{progress_bar_str} {fraction_str} | {percentage_str} | {game["name"]}')
        stdscr.refresh()
        
        start = time.time()
        
        liste_jeux.append(process_stats_game(game))
        
        end = time.time()
        if is_rate_limiting:
            while end - start < 2:
                time.sleep(0.1)
                end = time.time()
    
    curses.curs_set(1)
    return liste_jeux    

def update_info_game(selected: str):
    """
    Fetches and updates the stats for a single game in cache from the Steam API.
    
    args:
        selected: The name of the game.
    """
    games = stm.users.get_owned_games(steam_id)
    
    game_info = None
    for game in games["games"]:
        if game['name'] == selected:
            game_info = process_stats_game(game)
            break
    if game_info is None:
        raise Exception(f"The cache somehow got modified while the program was running")
    
    update_cache_one_game_stats(selected, game_info)

# TODO : factorize the way to display each type of game stats
def write_formated_stats_cache():
    """
    Computes and writes the full stats to a cache file.
    
    args:
        user_cache_folder: The name of the cache folder for the user.
    """
    json_stats = get_cache_all_games_stats()
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

    with open(f"{CACHE_FOLDER}/{user_name}_{steam_id}/{FORMATED_STATS_FILE}", "w", encoding='utf-8') as f:
        if len(liste_prix_inconnus) > 0:
            f.write("Games which price is unknown\n")
            f.write(str(pd.DataFrame(liste_a_afficher[3], columns=["Name", "Playtime", "Reason"])))
            f.write("\n\n")
        if len(liste_prix_gratuits) > 0:
            f.write("Free games\n")
            f.write(str(pd.DataFrame(liste_a_afficher[2], columns=["Name", "Playtime"])))
            f.write("\n\n")
        if len(liste_playtime0) > 0:
            f.write("Unplayed games\n")
            f.write(str(pd.DataFrame(liste_a_afficher[0], columns=["Name", "Price", "Target playtime"])))
            f.write("\n\n")
        if len(liste_norm) > 0:
            f.write("Played payed games\n")
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


# MAIN

def init_first():
    """
    Initializes other stuff
    """
    # Change the working directory to the script's directory
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    os.chdir(script_dir)
    
    pd.set_option('display.max_rows', None)

def init_api(stdscr):
    """
    Initializes api access
    
    args:
        stdscr: The curses window object.
    """
    KEY = get_key(stdscr)
    
    global stm, c 
    stm = steam.Steam(KEY)
    c = CurrencyConverter()

def init_user_info(stdscr):
    global user_name, steam_id
    
    maybe_steam_ids: Optional[Dict[str, str]] = get_cache_steam_ids()
    if maybe_steam_ids:
        steam_id_options = []
        for user_name, steam_id in maybe_steam_ids.items():
            steam_id_options.append(f'{user_name} : {steam_id}')
        steam_id_options.append('Add SteamID')
    else:
        steam_id_options = ['Add SteamID']
    steam_id_choice = choice(stdscr, steam_id_options, 'Select SteamID')
    
    if steam_id_options[steam_id_choice] == 'Add SteamID':
        [user_name, steam_id] = input_strs(stdscr, ['Enter name of the account (just for clarity, you can put whatever)', 'Enter SteamID'])
        while len(steam_id) != 17 or not steam_id.isdigit():
            steam_id = input_str(stdscr, 'Invalid SteamID. Please enter a valid SteamID')
        add_cache_steam_id((user_name, steam_id))
    else:
        user_name, steam_id = steam_id_options[steam_id_choice].split(' : ')

def main(stdscr):
    init_first()
    init_api(stdscr)
    init_user_info(stdscr)
    
    stdscr.clear()
        
    while True:
        # TODO : make the option clearer
        mode_options = ['One Game', 'All Games', 'Cached Games', 'Global Stats', "Quit"]
        mode_choice = choice(stdscr, mode_options, 'Select Mode')    
        stdscr.clear()
        match mode_options[mode_choice]:
            case 'One Game':
                if does_cache_all_games_stats_exist():
                    cached_game_infos = get_cache_all_games_stats()
                    all_game_names = [game['name'] for game in cached_game_infos]
                    selected = fzf.iterfzf(all_game_names)
                    if isinstance(selected, str):
                        update_info_game(selected)
                        display_stats_for_one_game(stdscr, cached_game_infos, selected)
                    else:
                        stdscr.addstr('Problem with the game selection')
                else:
                    stdscr.addstr('No cached data for this account. Please run "All Games" mode first.')
            case 'All Games':
                game_infos = all_games_info(stdscr)
                add_cache_all_games_stats(game_infos)
                write_formated_stats_cache()
                stdscr.clear()
                stdscr.addstr(f"You will find the formated stats in : {CACHE_FOLDER}/{user_name}_{steam_id}/{FORMATED_STATS_FILE}")
            case 'Cached Games':
                if does_cache_all_games_stats_exist():
                    write_formated_stats_cache()
                    stdscr.clear()
                    stdscr.addstr(f"You will find the formated stats in : {CACHE_FOLDER}/{user_name}_{steam_id}/{FORMATED_STATS_FILE}")
                else:
                    stdscr.addstr('No cached data for this account. Please run "All Games" mode first.')
            case 'Global Stats':
                if does_cache_all_games_stats_exist():
                    with open(f"{CACHE_FOLDER}/{user_name}_{steam_id}/{FORMATED_STATS_FILE}", "r", encoding='utf-8') as f:
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