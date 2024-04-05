import requests

API_KEY = "b2257261e43d9f1c926ede0fec0c5c18"
SPORT = "basketball_nba"
REGIONS = "us"
ODDS_FORMAT = "american"


def getEvents():
    """
    Fetches a list of event IDs for today's NBA games using The Odds API.

    Returns:
        list: A list containing the IDs of today's NBA games. Returns an empty list if no games are found or an error occurs.
    """

    events_url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events"
    params = {"apiKey": API_KEY}
    event_ids = []

    try:
        response = requests.get(events_url, params=params)
        response.raise_for_status()
        events_data = response.json()

        if events_data:
            print(f"Retrieved {len(events_data)} events for {SPORT}.")
            event_ids = [event["id"] for event in events_data]
        else:
            print(f"No events found for {SPORT}.")

    except requests.RequestException as e:
        print(f"An error occurred while fetching events: {e}")

    return event_ids


def getPlayersPropsOddsForGame(event_id, prop_type):
    """
    Retrieves betting odds for specified player propositions (e.g., points, assists, rebounds) from different bookmakers for a specific game.

    Parameters:
        event_id (str): The unique ID for the game.
        prop_type (str): The type of player prop to retrieve odds for (e.g., "player_points", "player_assists", "player_rebounds").

    Returns:
        dict: A dictionary mapping player names to their odds information from different bookmakers.
    """

    EVENT_ID = event_id
    MARKETS = prop_type

    request_url = (
        f"https://api.the-odds-api.com/v4/sports/{SPORT}/events/{EVENT_ID}/odds"
    )

    params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT,
    }

    response = requests.get(request_url, params=params)

    # Initialize a dictionary to hold player odds from all bookmakers
    players_odds_all_books = {}

    if response.status_code == 200:
        odds_data = response.json()

        # Extract home and away team names
        home_team = odds_data.get("home_team")
        away_team = odds_data.get("away_team")

        # Iterate over all bookmakers in the response
        for bookmaker in odds_data["bookmakers"]:
            bookmaker_name = bookmaker["key"]
            # Skip these 2 books (weird odds)
            if bookmaker_name in ["betrivers", "unibet_us"]:
                continue

            for market in bookmaker["markets"]:
                if market["key"] == MARKETS:
                    for outcome in market["outcomes"]:
                        player_name = outcome["description"]
                        if player_name not in players_odds_all_books:
                            players_odds_all_books[player_name] = {
                                "home_team": home_team,
                                "away_team": away_team,
                            }

                        if bookmaker_name not in players_odds_all_books[player_name]:
                            players_odds_all_books[player_name][bookmaker_name] = {
                                "points": outcome["point"],
                                "overOdds": None,
                                "underOdds": None,
                            }

                        # assign overOdds and underOdds
                        if "over" in outcome["name"].lower():
                            players_odds_all_books[player_name][bookmaker_name][
                                "overOdds"
                            ] = outcome["price"]
                        elif "under" in outcome["name"].lower():
                            players_odds_all_books[player_name][bookmaker_name][
                                "underOdds"
                            ] = outcome["price"]
    else:
        print(f"Failed to retrieve data: {response.status_code}, {response.text}")

    # Print the remaining and used request counts
    # print("Remaining requests:", response.headers.get("x-requests-remaining"))
    # print("Used requests:", response.headers.get("x-requests-used"))

    return players_odds_all_books


def calculate_implied_probability(odds):
    """
    Converts American odds to an implied probability percentage.

    Parameters:
        odds (int): The American odds to convert.

    Returns:
        float: The implied probability as a decimal. For example, 0.5 represents a 50% chance.
    """

    if odds < 0:
        return -odds / (-odds + 100)
    else:
        return 100 / (odds + 100)


def find_best_props(players_data, prop_type):
    """
    Analyzes odds for player props across different bookmakers to find the best betting opportunities.

    Parameters:
        players_data (dict): A nested dictionary containing each player's odds data from different bookmakers.
        prop_type (str): The type of prop (e.g., points, assists, rebounds) that is being analyzed.

    Returns:
        list: A list of dictionaries, each containing the best betting proposition for a player, including the team names, with only the top 2 by implied probability included.
    """

    # Mapping from API prop types to more readable prop types
    prop_type_mapping = {
        "player_points": "points",
        "player_assists": "assists",
        "player_rebounds": "rebounds",
    }

    readable_prop_type = prop_type_mapping.get(
        prop_type, prop_type
    )  # Default to prop_type if not found in mapping

    all_props = []

    for player, data in players_data.items():
        player_props = []
        home_team = data["home_team"]
        away_team = data["away_team"]

        # Collect all valid odds for the current player
        for book, odds in data.items():
            if book in ["home_team", "away_team"]:  # Skip team name keys
                continue
            if odds.get("overOdds") is not None and odds.get("underOdds") is not None:
                over_probability = calculate_implied_probability(odds["overOdds"])
                under_probability = calculate_implied_probability(odds["underOdds"])
                player_props.append(
                    {
                        "book": book,
                        "line": odds["points"],
                        "overOdds": odds["overOdds"],
                        "underOdds": odds["underOdds"],
                        "overProbability": over_probability,
                        "underProbability": under_probability,
                    }
                )

        if player_props:
            # Find the bet with the highest implied probability among collected valid bets
            best_bet = max(
                player_props,
                key=lambda x: max(x["overProbability"], x["underProbability"]),
            )
            # Create an entry for this player
            player_entry = {
                "player": player,
                "prop_type": readable_prop_type,  # Use the more readable prop type
                "home_team": home_team,
                "away_team": away_team,
                "line": best_bet["line"],
                "bestBet": (
                    "over"
                    if best_bet["overProbability"] > best_bet["underProbability"]
                    else "under"
                ),
                "bestBetOdds": (
                    best_bet["overOdds"]
                    if best_bet["overProbability"] > best_bet["underProbability"]
                    else best_bet["underOdds"]
                ),
                "bestBetProbability": max(
                    best_bet["overProbability"], best_bet["underProbability"]
                ),
                "allOdds": player_props,  # Include all valid odds for this player
            }
            all_props.append(player_entry)

    # Sort all players by the best bet probability and select the top 2
    top_props = sorted(all_props, key=lambda x: x["bestBetProbability"], reverse=True)[
        :2
    ]
    return top_props


def main():
    prop_types = ["player_points", "player_assists", "player_rebounds"]
    games_ids = getEvents()
    best_props = []

    # for each game
    for event_id in games_ids:
        # for each prop type in prop_types[]
        for prop_type in prop_types:
            player_odds = getPlayersPropsOddsForGame(event_id, prop_type)
            best_props.extend(find_best_props(player_odds, prop_type))
        break  # testing for 1 game

    best_props_sorted = sorted(
        best_props, key=lambda x: x["bestBetProbability"], reverse=True
    )

    for prop in best_props_sorted:
        probability_percentage = round(prop["bestBetProbability"] * 100, 2)
        print(
            f"{prop['home_team']} vs {prop['away_team']}: {prop['player']}, {prop['prop_type']} {prop['bestBet']} {prop['linec']} ({probability_percentage}%)"
        )


if __name__ == "__main__":
    main()
