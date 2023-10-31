import discord
from discord.ext import commands
from discord import Embed, Color
from dotenv import load_dotenv
import os
import requests

from bgg import (
    BggCollectionError, 
    BggCollectionTimeoutError, 
    get_bgg_collection, 
    get_game_details,
    get_game_from_collection,
    combine_bgg_collections,
    collections_known
)

from utils.text import normalize

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

known_users = collections_known

@bot.command()
async def ping(ctx):
    await ctx.send("pong bitch")


@bot.command()
async def game(ctx, *, game_name):
    game_name = normalize(game_name, True)

    try: 
        collections = [await get_bgg_collection(user) for user in known_users]
    except BggCollectionTimeoutError as e: 
        await ctx.send(f"{str(e)}; creating partial combined collection")
    except BggCollectionError as e: 
        await ctx.send(f"{str(e)}; creating partial combined collection")

    combined_collection = await combine_bgg_collections(collections)
    search_results = [collection_game for collection_game in combined_collection['games'] if game_name in collection_game['name']]

    if len(search_results) > 0:
        found_game = search_results[0]

        owners = f"{', '.join(found_game['owned_by'])}"
        game_details = await get_game_details(found_game['objectid'])

        embed = Embed(
            title=f"{game_details['label']} ({game_details['yearpublished']})",
            url=f"https://boardgamegeek.com/boardgame/{found_game['objectid']}",
            colour=discord.Color.dark_purple(),
        )

        embed.set_thumbnail(url=found_game['image'])
        embed.add_field(name="Avg Rating", value=game_details['rating'], inline=True)
        embed.add_field(name="Play Time", value=game_details['play_time'], inline=True)
        embed.add_field(name="Player Count", value=game_details['player_count_details'], inline=True)
        embed.add_field(name="Game Description", value=f"*{game_details['description']}*", inline=False)
        embed.add_field(name="Owned By",value=f"```{owners}```", inline=False)
        if len(search_results) > 1:
            # add bot command links for each found game, that can be clicked to send the command lookup for that game: https://stackoverflow.com/questions/73741997/clickable-command-in-text-discord
            all_found_games = "\n".join([search_game['label'] for search_game in search_results[1:]])
            embed.add_field(name="Other Search Matches in Combined Collection", value=f"{all_found_games}", inline=False)
        await ctx.send(embed=embed)
    else: 
        # TODO: Move entire section except for embed logic to bgg module
        search_url = f"https://boardgamegeek.com/xmlapi2/search?query={game_name}&type=boardgame".replace(" ", "%20")
        resp = requests.get(search_url)
        tree = xml.fromstring(resp.content)
        items = tree.findall('item')
        search_results_games = []
        boardgame_names = []
        boardgame_game_ids = []
        
        for item in items:
            search_result = {
                "objectid": item.attrib['id'],
                "type": item.attrib['type'],
                "name": normalize(item.find('name').attrib['value'])
            }
            
            boardgame_names.append(search_result['name'])
            boardgame_game_ids.append(int(search_result['objectid']))
            search_results_games.append(search_result)
        
        if len(search_results_games) < 1:
            return await ctx.send(f"No game found using the provided search criteria: `{game_name}`")

        search_results_games_list = [search_game for  search_game in search_results_games]
        boardgame_game_ids = sorted(boardgame_game_ids)
        preferred_game_id = boardgame_game_ids[-1]
        game_details = await get_game_details(preferred_game_id)
        num_games_to_return = 10

        embed = Embed(
            title=f"{game_details['label']} ({game_details['yearpublished']})",
            url=f"https://boardgamegeek.com/boardgame/{game_details['objectid']}",
            description=f"No game was found in the collections of the known users using the provided search. The newest best match has been provided via BGG search: {search_url}",
            colour=discord.Color.dark_purple(),
        )

        embed.set_thumbnail(url=game_details['image'])
        embed.add_field(name="Avg Rating", value=game_details['rating'], inline=True)
        embed.add_field(name="Play Time", value=game_details['play_time'], inline=True)
        embed.add_field(name="Player Count", value=game_details['player_count_details'], inline=True)
        embed.add_field(name="Game Description", value=f"*{game_details['description']}*", inline=False)
        embed.add_field(name="Owned By",value=f"```No one currently owns this game```", inline=False)
        embed.add_field(name=f"Other Search Results ({num_games_to_return} of {len(boardgame_names)})",value="\n".join(boardgame_names[:num_games_to_return]), inline=False)

        await ctx.send(embed=embed)
    

@bot.command()
async def refresh_collection(ctx, *, username):
    username = normalize(username, True)
    await ctx.send(f"refreshing {username}'s collection cache")
    delete_cache("collection", username)
    user_collection = await get_bgg_collection(username)
    await ctx.send(f"{username}'s collection cache updated: {len(user_collection['game_id_list'])} games")


@bot.command()
async def collection(ctx, username):
    collection = await get_bgg_collection(username)
    collection_formatted = f"""```json {json.dumps(collection["games"][0])}```"""
    for game in collection['games']:
        await ctx.send(game['thumbnail'])


@bot.command()
async def known_collections(ctx):
    # TODO: Add link to bgg user collection https://boardgamegeek.com/collection/user/<username>
    kc = []
    for user in known_users:
        crown = ""
        # TODO: find actual top game count and assign crown
        if user.lower() == "jchamilton":
            crown = ":crown:"

        user_link = f"[{user}](https://boardgamegeek.com/collection/user/{user})"
        user_collection = await get_bgg_collection(user)
        user_collection_size = len(user_collection['games'])

        kc.append(f"{user_link} ({user_collection_size} Games) {crown}")

    kc = "\n".join(kc)

    embed = Embed(
        title="Known Collections",
        description=f"""Currently I know the collections of:\n{kc}""",
        colour=discord.Color.dark_purple(),
    )
    await ctx.send(embed=embed)

# TODO: hot list command
# TODO: list all games in combined collection command

load_dotenv()
bot.run(os.getenv('BOT_TOKEN', None))
