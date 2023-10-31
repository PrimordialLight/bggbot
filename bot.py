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
    search_bgg,
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
    collection_search_results = [collection_game for collection_game in combined_collection['games'] if game_name in collection_game['name']]

    game_in_collection = False
    game_description = "No game was found in the collections of the known users using the provided search. The best match has been provided via BGG search."
    game_owners = f"```No one currently owns this game```"

    if len(collection_search_results) > 0:
        game_in_collection = True
        game_description = None
        print("game in collection")
        found_game = collection_search_results[0]
        game_owners = f"```{', '.join(found_game['owned_by'])}```"
        game_details = await get_game_details(found_game['objectid'])
    else:
        print("game not in collection")
        search_results = await search_bgg(game_name)
        print(search_results)

        if len(search_results) < 1:
            return await ctx.send(f"No game found using the provided search criteria: `{game_name}`")

        boardgame_names = [search_result['name'] for search_result in search_results] 
        boardgame_game_ids = [int(search_result['objectid']) for search_result in search_results]

        boardgame_game_ids = sorted(boardgame_game_ids)
        print(boardgame_game_ids)
        if len(boardgame_game_ids) > 1:
            preferred_game_id = boardgame_game_ids[int(len(boardgame_game_ids)/2)]
        else: 
            preferred_game_id = boardgame_game_ids[0]

        game_details = await get_game_details(preferred_game_id)
        num_games_to_return = 10

    
    embed = Embed(
        title=f"{game_details['label']} ({game_details['yearpublished']})",
        url=f"https://boardgamegeek.com/boardgame/{game_details['objectid']}",
        description=game_description,
        colour=discord.Color.dark_purple(),
    )

    embed.set_thumbnail(url=game_details['image'])
    embed.add_field(name="Avg Rating", value=game_details['averagerated'], inline=True)
    embed.add_field(name="Play Time", value=game_details['playtime'], inline=True)
    embed.add_field(name="Player Count", value=game_details['playercount'], inline=True)
    embed.add_field(name="Game Description", value=f"*{game_details['descriptionshort']}*", inline=False)
    embed.add_field(name="Owned By",value=game_owners, inline=False)
    if game_in_collection:
        if len(collection_search_results) > 1:
            # add bot command links for each found game, that can be clicked to send the command lookup for that game: https://stackoverflow.com/questions/73741997/clickable-command-in-text-discord
            all_found_games = "\n".join([search_game['label'] for search_game in collection_search_results[1:]])
            embed.add_field(name="Other Search Matches in Combined Collection", value=f"{all_found_games}", inline=False)
    else:
        if len(boardgame_names) >= num_games_to_return:
            title = f"Other Search Results ({num_games_to_return} of {len(boardgame_names)})"
        else: 
            title = f"Other Search Results ({len(boardgame_names)} of {len(boardgame_names)})"
        
        embed.add_field(name=title,value="\n".join(boardgame_names[:num_games_to_return]), inline=False)

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
