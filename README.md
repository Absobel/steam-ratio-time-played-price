Sorts Steam games by the ratio of playtime to price for a user. If you have more than 200 entries in your library, it will take much longer due to Steam API's call rate limits.

It works with linux and windows !

# To make it work
You need to run this in a terminal, preferably in a virtual environment : 
```bash
pip install -r requirements.txt
```

You also need to create a `.env` file with [your API key](https://steamcommunity.com/dev/apikey) in the following format:
```bash
STEAM_API_KEY=[YOUR_API_KEY]
```

# How to use

After adding the Steam ID of the account you want to analyze, you have four options to choose from:

1. **One Game**: Retrieve statistics for a single game from the list of previously cached games.
2. **All Games**: Perform an analysis of your entire library.
3. **Cached Games**: Update the file with statistics from your entire library based on a cached analysis.
4. **Global Stats**: Provide miscellaneous statistics about your library.

# Known issues

It takes neither DLCs nor family shared games into account (feel free to make a PR if you have a solution).