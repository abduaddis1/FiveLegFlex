import requests

API_KEY = "b2257261e43d9f1c926ede0fec0c5c18"
SPORT = "basketball_nba"
REGIONS = "us"
ODDS_FORMAT = "american"


# get NBA games for today
def getEvents():
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


# gets all player points and creates a map of different books with player's lines and odds for event_id (game)
def getPlayersPointsOddsForGame(event_id):
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
    player_odds_all_books = {}

    if response.status_code == 200:
        odds_data = response.json()

        # Iterate over all bookmakers in the response
        for bookmaker in odds_data["bookmakers"]:
            bookmaker_name = bookmaker["key"]
            # skip these 2 books (weird odds)
            if bookmaker_name == "betrivers" or bookmaker_name == "unibet_us":
                continue
            player_odds = {}  # This will store odds for the current bookmaker

            for market in bookmaker["markets"]:
                if market["key"] == MARKETS:
                    for outcome in market["outcomes"]:
                        player_name = outcome["description"]
                        if player_name not in player_odds:
                            # set over and under odds to None at the moment, get values in the next statement
                            player_odds[player_name] = {
                                "points": outcome["point"],
                                "overOdds": None,
                                "underOdds": None,
                            }
                        if outcome["name"].lower() == "over":
                            player_odds[player_name]["overOdds"] = outcome["price"]
                        elif outcome["name"].lower() == "under":
                            player_odds[player_name]["underOdds"] = outcome["price"]

            # Add the odds from the current bookmaker to the overall dictionary
            player_odds_all_books[bookmaker_name] = player_odds
    else:
        print(f"Failed to retrieve data: {response.status_code}, {response.text}")

    # Print the remaining and used request counts
    print("Remaining requests:", response.headers.get("x-requests-remaining"))
    print("Used requests:", response.headers.get("x-requests-used"))

    return player_odds_all_books


# returns a sorted list with best points props
def pointsOptimizer(game):
    return


# main
def main():
    table = []
    games_ids = getEvents()

    if games_ids:
        for event_id in games_ids:
            print(f"Fetching player points odds for game ID: {event_id}")
            table.append(getPlayersPointsOddsForGame(event_id))
            break  # one game for now for testing
    else:
        print("No NBA games found for today.")

    print("\n\n\n\n\n\n\n\n")
    print(table)


if __name__ == "__main__":
    main()
