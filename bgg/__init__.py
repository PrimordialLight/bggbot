import requests
import xmltodict
import xml.etree.ElementTree as xml

from cache import (
    create_cache, 
    delete_cache, 
    get_cache, 
    get_cache_age
)

from utils.text import normalize


collections_known = ['exhaustx', 'wayniackc', 'jchamilton', 'cgaikwad', 'n0ki']


class BggCollectionTimeoutError(Exception):
    pass


class BggCollectionError(Exception):
    pass


async def get_game_details(game: int):
    game_id = str(game)

    cached_game = get_cache("game", game_id, cache_age_max=24)
    if cached_game != None: 
        print(f"Using {game_id}'s cached game details")
        return cached_game
    else:
        resp = requests.get(f"https://boardgamegeek.com/xmlapi2/thing?id={game_id}&stats=1")
        if resp.status_code == 429:
            print("--[WARNING: BGG rate limit throttling causing slow requests]--")
            time.sleep(2)
            resp = requests.get(f"https://boardgamegeek.com/xmlapi2/thing?id={game_id}&stats=1")
        
        game_details = {}
        tree = xml.fromstring(resp.content)
        item = tree.findall('item')[0]
        poll = item.findall('poll')[0]
        poll = [poll for poll in item.findall('poll') if poll.attrib['name'] == 'suggested_numplayers'][0]
        results = poll.findall('results')

        all_numplayer_results = []
        for result in results:
            game_numplayer_results = {}
            game_numplayer_results["numplayers"] = result.attrib['numplayers']
            recommendation = None
            recommendation_votes = 0
            
            for value in result.findall('result'):
                if int(value.attrib['numvotes']) > recommendation_votes:
                    recommendation = value.attrib['value']
                    recommendation_votes = int(value.attrib['numvotes'])

            all_numplayer_results.append(
                {
                    "numplayers": result.attrib['numplayers'],
                    "recommendation": recommendation,
                    "votes": recommendation_votes
                }
            )

        game_description = normalize(item.find("description").text)
        game_description = (game_description[:400] + '...[more]') if len(game_description) > 400 else game_description

        game_details['label'] = normalize(item.findall('name')[0].attrib['value'])
        game_details['objectid'] = game_id
        game_details['yearpublished'] = item.find('yearpublished').attrib['value']
        game_details['image'] = item.find('image').text
        game_details['description'] = game_description
        game_details['avg_rating'] = float(item.findall('statistics')[0].findall('ratings')[0].findall('average')[0].attrib['value'])
        game_details['rating'] = str(round(game_details['avg_rating'], 1))
        
        # player count details 
        game_details['min_players'] = int(item.findall('minplayers')[0].attrib['value'])
        game_details['max_players'] = int(item.findall('maxplayers')[0].attrib['value'])
        if game_details['min_players'] == game_details['max_players']:
            game_details['player_count'] = game_details['min_players']
        else: 
            game_details['player_count'] = f"{game_details['min_players']} - {game_details['max_players']}"

        game_details['rec_num_players'] = all_numplayer_results
        game_details['best_player_count'] = "/".join([recommendation['numplayers'] for recommendation in game_details['rec_num_players'] if recommendation['recommendation'] == "Best"])
        game_details['player_count_details'] = f"{game_details['player_count']}, Best: {game_details['best_player_count']}"

        game_details['min_playtime'] = int(item.findall('minplaytime')[0].attrib['value'])
        game_details['max_playtime'] = int(item.findall('maxplaytime')[0].attrib['value'])
        game_details["play_time"] = f"{game_details['min_playtime']} - {game_details['max_playtime']} Min"
        
        create_cache("game", game_id, game_details)
        return game_details


async def get_bgg_collection(username: str, owned_only: bool=True, include_status: bool=False) -> dict:
    """
    retreievee a boardgamegeek collection by username
    :param str username: the bgg username of the collection to grab
    :param bool owned_only: only return games from the user's collection that they own
    :param bool include_status: will exclude user game status for items in the collection (owned, want to buy, for trade, etc)
    """
    resp_code = 0
    attempts = 0
    cached_collection = get_cache("collection", username)
    if cached_collection != None: 
        print(f"Using {username}'s cached collection")
        return cached_collection
    
    try: 
        while resp_code != 200:
            print(f"Refreshing {username}'s collection cache from bgg...")
            if owned_only:
                resp = requests.get(f"https://boardgamegeek.com/xmlapi2/collection?username={username}&own=1")
            else:
                resp = requests.get(f"https://boardgamegeek.com/xmlapi2/collection?username={username}")

            if resp.status_code == 200:
                resp_code = 200
            elif resp.status_code == 202:
                raise BggCollectionTimeoutError(f"{username}'s Collection has been requested, waiting on collection to be made available by BGG...")
                time.sleep(5)
            else: 
                raise BggCollectionError(resp.status_code, resp.content)

    except BggCollectionTimeoutError as e:
        raise e
    except BggCollectionError as e:
        raise e

    tree = xml.fromstring(resp.content)
    collection = {
        "type": "UserCollection",
        "owner": username,
        "games": []
    }

    for child in tree.findall('item'):
        game = {}
        game["owned_by"] = [username]
        game["type"] = child.attrib["subtype"]
        game["objectid"] = child.attrib["objectid"]
        for item in child: 
            if(item.tag == 'status'):
                if include_status: 
                    game[item.tag] = item.attrib
            elif(item.tag == 'name'):
                game['label'] = normalize(item.text)
                game[item.tag] = normalize(game['label'], True)
            else: 
                game[item.tag] = item.text
        
        collection["games"].append(game)

    collection["game_list"] = [game['name'] for game in collection["games"]]
    collection["game_id_list"] = [game['objectid'] for game in collection["games"]]
    collection["total_games"] = len(collection["game_list"])

    create_cache("collection", username, collection)
    return collection


async def combine_bgg_collections(collections: list):
    """
    combines N number of boardgame collections into a single total collection
    :param list collections: a list of collection dictionaries; collections are return by get_bgg_collection
    """
    source_collection = collections.pop(0)
    total_collection = source_collection
    total_collection['type'] = "CombinedUserCollection"
    total_collection['owner'] = [source_collection['owner']]

    for collection in collections:
        try:
            total_collection['owner'].append(collection['owner'])
            for game in collection["games"]:
                if game['name'] not in total_collection['game_list']:
                    total_collection['game_list'].append(game['name'])
                    total_collection['game_id_list'].append(game['objectid'])
                    total_collection['games'].append(game)
                else:
                    for total_collection_game in total_collection['games']:
                        if total_collection_game['name'] == game['name']:
                            total_collection_game["owned_by"].append(collection['owner'])
        except Exception as e:
            print(f"failed to add {total_collection['owner']}'s collection to the combined collection: {str(e)}")
            pass

    total_collection["game_list"] = sorted(total_collection["game_list"], reverse=False)
    total_collection["game_id_list"] = sorted(total_collection["game_id_list"], reverse=False)
    total_collection["total_games"] = len(total_collection["game_list"])
    return total_collection


async def get_game_from_collection(game_name: str, collection: dict) -> dict:
    for game in collection['games']:
        if game['name'] == game_name:
            return game
