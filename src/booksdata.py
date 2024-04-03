import requests

API_KEY = "b2257261e43d9f1c926ede0fec0c5c18"
SPORT = "basketball_nba"
REGIONS = "us"
ODDS_FORMAT = "american"


def getEvents():
    """
    Fetches IDs for NBA games happening today.

    Returns:
        event_ids (list): A list of event IDs for today's NBA games.
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


def getPlayersPointsOddsForGame(event_id):
    """
    Retrieves player points, odds, and team names from different bookmakers for a given game.

    Parameters:
        event_id (str): The ID of the game for which to fetch player points and odds.

    Returns:
        players_odds_all_books (dict): A dictionary containing odds from all bookmakers
                                        for each player in the game along with the team names.
    """
    EVENT_ID = event_id
    MARKETS = "player_points"

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
    #print("Remaining requests:", response.headers.get("x-requests-remaining"))
    #print("Used requests:", response.headers.get("x-requests-used"))

    return players_odds_all_books


def calculate_implied_probability(odds):
    """
    Calculates the implied probability of given American odds.

    Parameters:
        odds (int): The American odds for which to calculate the implied probability.

    Returns:
        float: The implied probability of the given odds.
    """
    if odds < 0:
        return -odds / (-odds + 100)
    else:
        return 100 / (odds + 100)


def find_best_props(players_data):
    """
    Analyzes player data to find the best betting propositions based on odds,
    and includes all odds from all bookmakers for the top 2 players,
    as well as the team names they belong to.

    Parameters:
        players_data (dict): A dictionary containing odds and points for each player
                             across different bookmakers.

    Returns:
        top_props (list): List of the top 2 betting propositions based on the analysis.
    """
    all_props = []

    for player, data in players_data.items():
        player_props = []
        # Extract team names
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
                        "points": odds["points"],
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
            # Create a comprehensive entry for this player
            player_entry = {
                "player": player,
                "home_team": home_team,  # Include team names
                "away_team": away_team,
                "points": best_bet["points"],
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


# main
def main():
    games_ids = getEvents()
    best_points_props = []

    if games_ids:
        for event_id in games_ids:
            player_points_odds = getPlayersPointsOddsForGame(event_id)
            recommendations = find_best_props(player_points_odds)
            best_points_props.extend(recommendations)
    else:
        print("No NBA games found for today.")

    best_points_props_sorted = sorted(
        best_points_props, key=lambda x: x["bestBetProbability"], reverse=True
    )

    print("\n\n\n\n\n\n\n\n")
    #print(best_points_props_sorted)
    for d in best_points_props_sorted:
        print(f'{d['home_team']} vs {d['away_team']}: {d['player']}, {d['bestBet']} at {d['points']}.')


if __name__ == "__main__":
    main()
