# steam-game-time-price-ratio
Sorts Steam games by the ratio of playtime to price for a user. If you have more than 200 entries in your library, it will take much longer due to Steam API's call rate limits.

# To make it work
You need to run this in a terminal, preferably in a virtual environment : 
```bash
pip install -r requirements.txt
```

You also need to create a `.env` file with [your API key](https://steamcommunity.com/dev/apikey) in the following format:
```bash
STEAM_API_KEY=[YOUR_API_KEY]
```

# TODO
- [ ] Complete the TODOs in the code
- [ ] Add DLCs (possibly with https://store.steampowered.com/dynamicstore/userdata but meh)