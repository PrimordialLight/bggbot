import os
import json
from datetime import datetime


CACHE_DATETIME_FMT = "%Y-%m-%d-%H-%M-%S"


def get_cache_age(cache_file: str) -> float:
    """
    Retrieves a cache file based on type and name
    :param str cache_type: "collection" | "game" 
    :param str cache_name: unique name of the case
    :param int cache_age_max: the maximum acceptable age for a cache in hours
    """
    cache_time = datetime.strptime(cache_file.split("_")[2].split(".")[0], CACHE_DATETIME_FMT)
    cache_age = (datetime.now() - cache_time).total_seconds()
    return cache_age


def delete_cache(cache_type: str, cache_name: str) -> None:
    """
    Deletes a cache file based on type and unique name
    :param str cache_type: "collection" | "game" 
    :param str cache_name: unique name of the case
    """
    cache_dir_path = f"cache/{cache_type}"
    cache_filename_prefix = f"{cache_type}_{cache_name}_"
    cache_filename = None
    for file in os.listdir(cache_dir_path):
        if file.startswith(cache_filename_prefix):
            cache_filename = file
    
    if cache_filename is not None:
        print("delete cache")
        os.remove(f"{cache_dir_path}/{cache_filename}")


def get_cache(cache_type: str, cache_name: str, cache_age_max: int=6) -> None:
    """
    Retrieves a cache file based on type and name
    :param str cache_type: "collection" | "game" 
    :param str cache_name: unique name of the case
    :param int cache_age_max: the maximum acceptable age for a cache in hours
    """
    cache_dir_path = f"cache/{cache_type}"
    if not os.path.exists(cache_dir_path):
        os.mkdir(cache_dir_path)
        
    cache_filename_prefix = f"{cache_type}_{cache_name}_"
    cache_filename = None
    for file in os.listdir(cache_dir_path):
        if file.startswith(cache_filename_prefix):
            cache_filename = file
    
    if cache_filename is None:
        return None 
    elif get_cache_age(cache_filename) > (cache_age_max * 60 * 60):
        print("delete stale cache")
        delete_cache(cache_type, cache_name)
        return None
    else:
        print("get cache content")
        with open(f"{cache_dir_path}/{cache_filename}") as cache_file: 
            return json.load(cache_file)


def create_cache(cache_type: str, cache_name: str, content: object) -> None:
    """
    Creates a cache file based on type and unique name
    :param str cache_type: "collection" | "game" 
    :param str cache_name: unique name of the case
    :param str content: the content to write to cache; is converted to json
    """
    print(f"Creating {cache_type} cache for {cache_name}")
    timestamp = datetime.now().strftime(CACHE_DATETIME_FMT)
    cache_dir_path = f"cache/{cache_type}"
    with open(f"{cache_dir_path}/{cache_type}_{cache_name}_{timestamp}.cache.json", "w") as outfile:
        outfile.write(json.dumps(content))
