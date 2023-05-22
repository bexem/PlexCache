import os, json, logging, glob, subprocess, socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from plexapi.server import PlexServer
from plexapi.video import Episode
from plexapi.video import Movie
from plexapi.myplex import MyPlexAccount

script_folder="/mnt/user/system/PlexCache/"
settings_filename = os.path.join(script_folder, "settings.json")
watchlist_cache_file = Path(os.path.join(script_folder, "watchlist_cache.json"))
watched_cache_file = Path(os.path.join(script_folder, "watched_cache.json"))
log_file_pattern = "plexcache_script_*.log"
max_log_files = 5

# Check if the script_folder exist, if not check for writing permissions, if okay, it will then create the folder
if not os.path.exists(script_folder):
    if not os.access(script_folder, os.W_OK):
        exit("Script folder not writable, please fix the variable accordingly.")
    else:
        os.makedirs(script_folder)
# As the script_folder exist, check for writing permissions
if not os.access(script_folder, os.W_OK):
    exit("Script folder not writable, please fix the variable accordingly.")

current_time = datetime.now().strftime("%Y%m%d_%H%M")
log_file = os.path.join(script_folder, f"{log_file_pattern[:-5]}{current_time}.log")
logging.basicConfig(filename=log_file, filemode='w', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create or update the symbolic link to the latest log file
latest_log_file = os.path.join(script_folder, f"{log_file_pattern[:-5]}latest.log")
if os.path.exists(latest_log_file):
    os.remove(latest_log_file)  # Remove the existing link if it exists

os.symlink(log_file, latest_log_file)  # Create a new link to the latest log file

# Check if the number of log files exceeds the limit and remove the oldest log file(s)
existing_log_files = glob.glob(os.path.join(script_folder, log_file_pattern))
if len(existing_log_files) >= max_log_files: 
    existing_log_files.sort(key=os.path.getctime)
    for i in range(len(existing_log_files) - max_log_files + 1):
        os.remove(existing_log_files[i])

# Check if the settings file exists
if os.path.exists(settings_filename):
    # Loading the settings file
    with open(settings_filename, 'r') as f:
        settings_data = json.load(f)
else:
    logging.error("Settings file not found, please fix the variable accordingly.")
    exit("Settings file not found, please fix the variable accordingly.")

# Reads the settings file and all the settings
try:
    PLEX_URL = settings_data['PLEX_URL']
    PLEX_TOKEN = settings_data['PLEX_TOKEN']
    number_episodes = settings_data['number_episodes']
    valid_sections = settings_data['valid_sections']
    users_toggle = settings_data['users_toggle']
    skip_users = settings_data['skip_users']
    watchlist_toggle = settings_data['watchlist_toggle']
    watchlist_episodes = settings_data['watchlist_episodes']
    days_to_monitor = settings_data['days_to_monitor']
    cache_dir = settings_data['cache_dir']
    plex_source = settings_data['plex_source']
    real_source = settings_data['real_source']
    nas_library_folders = settings_data['nas_library_folders']
    plex_library_folders = settings_data['plex_library_folders']
    unraid = settings_data['unraid']
    watched_move = settings_data['watched_move']
    watchlist_cache_expiry = settings_data['watchlist_cache_expiry']
    watched_cache_expiry = settings_data['watched_cache_expiry']
    skip = settings_data['skip']
    debug = settings_data['debug']
    max_concurrent_moves_array = settings_data['max_concurrent_moves_array']
    max_concurrent_moves_cache = settings_data['max_concurrent_moves_cache']
except KeyError as e:
    logging.error(f"Error: {e} not found in settings file, please re-run the setup or manually edit the settings file.")
    exit(f"Error: {e} not found in settings file, please re-run the setup or manually edit the settings file.")

# Initialising necessary arrays
processed_files = []
files_to_skip = []
media_to = []
media_to_cache = []
media_to_array = []
move_commands = []

# Connect to the Plex server
try:
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
except Exception as e:
    logging.error(f"Error connecting to the Plex server: {e}")
    exit(f"Error connecting to the Plex server: {e}")

# Check if any active session
sessions = plex.sessions()
if sessions:
    if skip:
        logging.warning('There is an active session. Exiting...')
        exit('There is an active session. Exiting...')
    else:
        for session in sessions:
            media = str(session.source())
            media_id = media[media.find(":") + 1:media.find(":", media.find(":") + 1)]
            media_item = plex.fetchItem(int(media_id))
            media_title = media_item.title
            print(f"Active session detected, skipping: {media_title}")
            logging.info(f"Active session detected, skipping: {media_title}")
            media_path = media_item.media[0].parts[0].file
            files_to_skip.append(media_path)

# Check if debug mode is active
if debug:
    print("Debug mode is active, no file will be moved. Extra info available in the log file.")
    logging.info("Debug mode is active, no file will be moved.")
    # Extra debugging 
    logging.info("______________")
    logging.info(f"Real source: {real_source}")
    logging.info(f"Cache dir: {cache_dir}")
    logging.info(f"Plex source: {plex_source}")
    logging.info(f"NAS folders: ({nas_library_folders}")
    logging.info(f"Plex folders: {plex_library_folders}")
    logging.info(f"Unraid: {unraid}")

# Function to print all files present in the currently in use array, only used if debug is on
def log_files(files, calledby):
    if debug:
        if len(files) > 0:
            logging.info(f"_____*{calledby}*_____")
            for file in files:
                logging.info(f"{file}")
            logging.info("______________________")

# Function to debug naming scheme, only used if debug is on
def log_file_info(file, cache_path, cache_file_name):
    if debug:
        logging.info(f"File: {file}")
        logging.info(f"Cache_path: {cache_path}")
        logging.info(f"Cache_file_name: {cache_file_name}")

# Function to fetch onDeck media files
def fetch_on_deck_media(plex, valid_sections, days_to_monitor, number_episodes, user=None):
    username, plex = get_plex_instance(plex, user)
    if not plex:
        return []

    print(f"Fetching {username}'s onDeck media...")
    logging.info(f"Fetching {username}'s onDeck media...")
    
    on_deck_files = []
    for video in plex.library.onDeck():
        if video.section().key in valid_sections:
            delta = datetime.now() - video.lastViewedAt
            if delta.days <= days_to_monitor:
                if isinstance(video, Episode):
                    process_episode_ondeck(video, number_episodes, on_deck_files)
                elif isinstance(video, Movie):
                    process_movie_ondeck(video, on_deck_files)

    log_files(on_deck_files, calledby="onDeck media")
    return on_deck_files

# Function to fetch the Plex instance
def get_plex_instance(plex, user):
    if user:
        username = user.title
        try:
            return username, PlexServer(PLEX_URL, user.get_token(plex.machineIdentifier))
        except Exception:
            print(f"Error: Failed to Fetch {username} onDeck media")
            logging.error(f"Error: Failed to Fetch {username} onDeck media")
            return None, None
    else:
        username = plex.myPlexAccount().title
        return username, PlexServer(PLEX_URL, PLEX_TOKEN)

# Function to process the onDeck media files
def process_episode_ondeck(video, number_episodes, on_deck_files):
    for media in video.media:
        on_deck_files.extend(part.file for part in media.parts)
    show = video.grandparentTitle
    library_section = video.section()
    episodes = list(library_section.search(show)[0].episodes())
    current_season = video.parentIndex
    next_episodes = get_next_episodes(episodes, current_season, video.index, number_episodes)
    for episode in next_episodes:
        for media in episode.media:
            on_deck_files.extend(part.file for part in media.parts)

# Function to process the onDeck movies files
def process_movie_ondeck(video, on_deck_files):
    for media in video.media:
        on_deck_files.extend(part.file for part in media.parts)

# Function to get the next episodes
def get_next_episodes(episodes, current_season, current_episode_index, number_episodes):
    next_episodes = []
    for episode in episodes:
        if (episode.parentIndex > current_season or (episode.parentIndex == current_season and episode.index > current_episode_index)) and len(next_episodes) < number_episodes:
            next_episodes.append(episode)
        if len(next_episodes) == number_episodes:
            break
    return next_episodes

# Function to search for a file in the Plex server
def search_plex(plex, title):
    results = plex.search(title)
    return results[0] if len(results) > 0 else None

# Function to fetch watchlist media files for the main user
def fetch_watchlist_media(plex, valid_sections, watchlist_episodes, users_toggle=False, skip_users=None):
    if skip_users is None:
        skip_users = []

    def get_watchlist(token, user=None):
        account = MyPlexAccount(token)
        if user:
            account = account.switchHomeUser(user.title)
        return account.watchlist(filter='released')

    def process_show(file, watchlist_episodes):
        episodes = file.episodes()
        count = 0

        if count <= watchlist_episodes:
            for episode in episodes[:watchlist_episodes]:
                if len(episode.media) > 0 and len(episode.media[0].parts) > 0:
                    count += 1
                    if not episode.isPlayed:
                        yield episode.media[0].parts[0].file

    def process_movie(file):
        yield file.media[0].parts[0].file

    users_to_fetch = [None]  # Start with main user (None)
    if users_toggle:
        users_to_fetch += plex.myPlexAccount().users()

    for user in users_to_fetch:
        current_username = plex.myPlexAccount().title if user is None else user.title
        print(f"Fetching {current_username}'s watchlist media...")
        logging.info(f"Fetching {current_username}'s watchlist media...")

        watchlist = get_watchlist(PLEX_TOKEN, user)
        
        for item in watchlist:
            file = search_plex(plex, item.title)
            if file and file.librarySectionID in valid_sections:
                if file.TYPE == 'show':
                    yield from process_show(file, watchlist_episodes)
                else:
                    yield from process_movie(file)

# Function to fetch watched media files
def get_watched_media(plex, valid_sections, user=None):
    def fetch_user_watched_media(plex_instance, username):
        print(f"Fetching {username}'s watched media...")
        logging.info(f"Fetching {username}'s watched media...")

        try:
            for section_id in valid_sections:
                section = plex_instance.library.sectionByID(section_id)
                for video in section.search(unwatched=False):
                    yield from process_video(video)
        except Exception:
            print(f"Error: Failed to Fetch {username}'s watched media")
            logging.info(f"Error: Failed to Fetch {username}'s watched media")

    def process_video(video):
        if video.TYPE == 'show':
            for episode in video.episodes():
                yield from process_episode(episode)
        else:
            file_path = video.media[0].parts[0].file
            yield file_path

    def process_episode(episode):
        for media in episode.media:
            for part in media.parts:
                if episode.isPlayed:
                    file_path = part.file
                    yield file_path

    main_username = plex.myPlexAccount().title
    yield from fetch_user_watched_media(plex, main_username)

    if users_toggle:
        for user in plex.myPlexAccount().users():
            username = user.title
            user_token = user.get_token(plex.machineIdentifier)
            user_plex = PlexServer(PLEX_URL, user_token)
            yield from fetch_user_watched_media(user_plex, username)

# Function to load watched media from cache
def load_watched_media_from_cache(cache_file):
    if cache_file.exists():
        with cache_file.open('r') as f:
            return set(json.load(f))
    return set()

# Function to change the paths to the correct ones
def modify_file_paths(files, plex_source, real_source, plex_library_folders, nas_library_folders):
    print("Editing file paths...")
    logging.info("Editing file paths...")
    if files is None:
        return []
    files = [file_path for file_path in files if file_path.startswith(plex_source)]
    for i, file_path in enumerate(files):
        file_path = file_path.replace(plex_source, real_source, 1) # Replace the plex_source with the real_source, thanks to /u/planesrfun
        for j, folder in enumerate(plex_library_folders): # Determine which library folder is in the file path
            if folder in file_path:
                file_path = file_path.replace(folder, nas_library_folders[j]) # Replace the plex library folder with the corresponding NAS library folder             
                break
        files[i] = file_path
    log_files(files, calledby="Modified path")
    return files or []

# Function to filter the files, based on the destination
def filter_files(files, destination, real_source, cache_dir, fileToCache):
    print(f"Filtering media files for {destination}...")
    logging.info(f"Filtering media files {destination}...")

    if fileToCache is None:
        fileToCache = []

    processed_files = set()
    media_to = []

    for file in files:
        if file in processed_files:
            continue

        processed_files.add(file)
        cache_path, cache_file_name = get_cache_paths(file, real_source, cache_dir)
        log_file_info(file, cache_path, cache_file_name)

        if destination == 'array' and should_add_to_array(file, cache_file_name, fileToCache):
            media_to.append(file)
        elif destination == 'cache' and should_add_to_cache(cache_file_name):
            media_to.append(file)

    log_files(media_to, calledby="Filtered media")
    return media_to or []

def get_cache_paths(file, real_source, cache_dir):
    file_path = Path(file)
    real_source_path = Path(real_source)
    cache_dir_path = Path(cache_dir)

    try:
        relative_path = file_path.relative_to(real_source_path)
    except ValueError:
        # handle the error appropriately, maybe log it and return None, or re-raise
        logging.warning(f"Error: file path {file_path} is not inside real source path {real_source_path}")
        print(f"Error: file path {file_path} is not inside real source path {real_source_path}")
        return None, None

    cache_path = cache_dir_path / relative_path.parent
    cache_file_name = cache_path / file_path.name

    return str(cache_path), str(cache_file_name)


def should_add_to_array(file, cache_file_name, fileToCache):
    if file in fileToCache:
        if debug:
            logging.info(f"Skipped {file} because present in fileToCache")
        return False
    return os.path.isfile(cache_file_name)

def should_add_to_cache(cache_file_name):
    return not os.path.isfile(cache_file_name)

# Function to fetch the subtitles
def get_media_subtitles(media_files, files_to_skip=None):
    print("Fetching subtitles...")
    logging.info("Fetching subtitles...")
    
    if files_to_skip is None:
        files_to_skip = set()
    
    processed_files = set()
    all_media_files = media_files.copy()

    for file in media_files:
        if file in files_to_skip or file in processed_files:
            continue

        processed_files.add(file)
        directory_path = os.path.dirname(file)
        log_directory_path(directory_path)

        if os.path.exists(directory_path):
            subtitle_files = find_subtitle_files(directory_path, file)
            all_media_files.extend(subtitle_files)

    log_files(all_media_files, calledby="Subtitles")
    return all_media_files or []

def log_directory_path(directory_path):
    if debug:
        logging.info(f"Directory path: {directory_path}")

def find_subtitle_files(directory_path, file):
    directory_path = Path(directory_path)
    file_path = Path(file)

    file_name = file_path.stem

    subtitle_files = [
        str(f) 
        for f in directory_path.iterdir() 
        if f.stem.startswith(file_name) and f.name != file_path.name
    ]

    return subtitle_files or []

# Function to convert size to readable format
def convert_bytes_to_readable_size(size_bytes):
    if size_bytes >= (1024 ** 4):
        size = size_bytes / (1024 ** 4)
        unit = 'TB'
    elif size_bytes >= (1024 ** 3):
        size = size_bytes / (1024 ** 3)
        unit = 'GB'
    elif size_bytes >= (1024 ** 2):
        size = size_bytes / (1024 ** 2)
        unit = 'MB'
    else:
        size = size_bytes / 1024
        unit = 'KB'
    return size, unit

# Function to check for free space
def get_free_space(dir):
    stat = os.statvfs(dir)
    free_space_bytes = stat.f_bfree * stat.f_frsize
    return convert_bytes_to_readable_size(free_space_bytes)

# Function to calculate size of the files contained in the given array
def get_total_size_of_files(files):
    total_size_bytes = sum(os.path.getsize(file) for file in files)
    return convert_bytes_to_readable_size(total_size_bytes)

def check_free_space_and_move_files(media_files, destination, real_source, cache_dir, unraid, debug, files_to_skip=None):
    media_files_filtered = filter_files(media_files, destination, real_source, cache_dir, media_to_cache)
    total_size, total_size_unit = get_total_size_of_files(media_files_filtered)
    logging.info(f"Total size of media files to be moved to {destination}: {total_size:.2f} {total_size_unit}")

    if total_size > 0:
        print(f"Total size of media files to be moved to {destination}: {total_size:.2f} {total_size_unit}")
        free_space, free_space_unit = get_free_space(destination == 'cache' and cache_dir or real_source)
        print(f"Free space on the {destination}: {free_space:.2f} {free_space_unit}")
        logging.info(f"Free space on the {destination}: {free_space:.2f} {free_space_unit}")

        if total_size * (1024 ** {'KB': 0, 'MB': 1, 'GB': 2, 'TB': 3}[total_size_unit]) > free_space * (1024 ** {'KB': 0, 'MB': 1, 'GB': 2, 'TB': 3}[free_space_unit]):
            raise ValueError("Not enough space on destination drive.")

        logging.info(f"Moving media to {destination}...")
        print(f"Moving media to {destination}...")
        move_media_files(media_files_filtered, real_source, cache_dir, unraid, debug, destination, files_to_skip)
    else:
        print(f"Nothing to move to {destination}")
        logging.info(f"Nothing to move to {destination}")

# Function to check if given path exists, is a directory and the script has writing permissions
def check_path_exists(path):
    if not os.path.exists(path):
        logging.error(f"Path {path} does not exist.")
    if not os.path.isdir(path):
        logging.error(f"Path {path} is not a directory.")
    if not os.access(path, os.W_OK):
        logging.error(f"Path {path} is not writable.")
    
def move_file(move_cmd):
    logging.info(move_cmd)
    result = subprocess.run(move_cmd, shell=True, stderr=subprocess.PIPE)
    if result.returncode != 0:
        logging.error(f"Error executing move command: Exit code: {result.returncode}")
        logging.error(f"Error message: {result.stderr.decode('utf-8')}")
    return result.returncode

def move_media_files(files, real_source, cache_dir, unraid, debug, destination, files_to_skip=None, max_concurrent_moves_array=1, max_concurrent_moves_cache=1):
    print(f"Moving media files to {destination}...")
    logging.info(f"Moving media files to {destination}...")
    if files_to_skip is None:
        files_to_skip = set()
    processed_files = set()
    move_commands = []

    for file_to_move in files:
        if file_to_move in files_to_skip or file_to_move in processed_files:
            continue

        processed_files.add(file_to_move)

        user_path, cache_path, cache_file_name, user_file_name = get_paths(file_to_move, real_source, cache_dir, unraid)

        move = get_move_command(destination, cache_file_name, user_path, user_file_name, cache_path)
        if move is not None:
            move_commands.append(move)

    execute_move_commands(debug, move_commands, max_concurrent_moves_array, max_concurrent_moves_cache, destination)

# Function to get the paths of the user and cache directories
def get_paths(file_to_move, real_source, cache_dir, unraid):
    file_to_move_path = Path(file_to_move)
    real_source_path = Path(real_source)
    cache_dir_path = Path(cache_dir)

    try:
        relative_path = file_to_move_path.relative_to(real_source_path)
    except ValueError:
        logging.warning(f"Error: file path {file_to_move_path} is not inside real source path {real_source_path}")
        print(f"Error: file path {file_to_move_path} is not inside real source path {real_source_path}")
        return None, None, None, None

    cache_path = cache_dir_path / relative_path.parent
    cache_file_name = cache_path / file_to_move_path.name

    user_path = file_to_move_path.parent

    if unraid:
        user_path = Path(str(user_path).replace("/mnt/user/", "/mnt/user0/", 1))

    user_file_name = user_path / file_to_move_path.name

    return str(user_path), str(cache_path), str(cache_file_name), str(user_file_name)


# Function to get the move command for the given file
def get_move_command(destination, cache_file_name, user_path, user_file_name, cache_path):
    move = None
    if destination == 'array':
        if not os.path.exists(user_path): 
            os.makedirs(user_path)
        if os.path.isfile(cache_file_name):
            move = f"mv -v \"{cache_file_name}\" \"{user_path}\""
    if destination == 'cache':
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)
        if not os.path.isfile(cache_file_name):
            move = f"mv -v \"{user_file_name}\" \"{cache_path}\""
    return move

# Function to execute the given move commands
def execute_move_commands(debug, move_commands, max_concurrent_moves_array, max_concurrent_moves_cache, destination):
    if debug:
        for move_cmd in move_commands:
            print(move_cmd)
            logging.info(move_cmd)
    else:
        max_concurrent_moves = max_concurrent_moves_array if destination == 'array' else max_concurrent_moves_cache
        with ThreadPoolExecutor(max_workers=max_concurrent_moves) as executor:
            results = executor.map(move_file, move_commands)
            errors = [result for result in results if result != 0]
            print(f"Finished moving files with {len(errors)} errors.")

# Function to check if internet is available
def is_connected():
    try:
        # Attempt to connect to google's DNS server
        socket.gethostbyname("www.google.com")
        return True
    except socket.error:
        return False

print("Initialising script...")
logging.info("Initialising script...")
print("Checking paths and permissions...")
logging.info("Checking paths and permissions...")
for path in [real_source, cache_dir]:
    check_path_exists(path)

# Main user's watchlist
if watchlist_toggle:
    watchlist_media_set = load_watched_media_from_cache(watchlist_cache_file)
    current_watchlist_set = set()
    if is_connected():
        # To fetch the watchlist media internet is required due to a plexapi limitation
        if (not watchlist_cache_file.exists()) or (datetime.now() - datetime.fromtimestamp(watchlist_cache_file.stat().st_mtime) > timedelta(hours=watchlist_cache_expiry)):
            print("Fetching watchlist media...")
            logging.info("Fetching watchlist media...")
            fetched_watchlist = fetch_watchlist_media(plex, valid_sections, watchlist_episodes, users_toggle=False, skip_users=None)

            for file_path in fetched_watchlist:
                current_watchlist_set.add(file_path)
                if file_path not in watchlist_media_set:
                    media_to_cache.append(file_path)

            # Remove media that no longer exists in watchlist
            watchlist_media_set.intersection_update(current_watchlist_set)

            # Add new media to the watchlist media set
            watchlist_media_set.update(media_to_cache)

            with watchlist_cache_file.open('w') as f:
                json.dump(list(watchlist_media_set), f)

        else:
            print("Loading watchlist media from cache...")
            logging.info("Loading watchlist media from cache...")
            media_to_cache.extend(watchlist_media_set)
    else:
        # handle no internet connection scenario
        print("Unable to connect to the internet, skipping fetching new watchlist media due to plexapi limitation.")
        logging.warning("Unable to connect to the internet, skipping fetching new watchlist media due to plexapi limitation.")
        print("Loading watchlist media from cache...")
        logging.info("Loading watchlist media from cache...")
        media_to_cache.extend(watchlist_media_set)

# Main user's onDeck media
media_to_cache.extend(fetch_on_deck_media(plex, valid_sections, days_to_monitor, number_episodes))

# Other users onDeck media
if users_toggle:
    for user in plex.myPlexAccount().users():
        username = user.title
        if user.get_token(plex.machineIdentifier) in skip_users:
            print(f"Skipping {username}'s onDeck media...")
            logging.info(f"Skipping {username}'s onDeck media...")
            continue
        media_to_cache.extend(fetch_on_deck_media(plex, valid_sections, days_to_monitor, number_episodes, user=user))

# Edit file paths for the above fetched media
media_to_cache = modify_file_paths(media_to_cache, plex_source, real_source, plex_library_folders, nas_library_folders)

# Fetches subtitles for the above fetched media
media_to_cache.extend(get_media_subtitles(media_to_cache, files_to_skip=files_to_skip))

# Watched media
if watched_move:
    watched_media_set = load_watched_media_from_cache(watched_cache_file)
    current_media_set = set()

    if (not watched_cache_file.exists()) or (datetime.now() - datetime.fromtimestamp(watched_cache_file.stat().st_mtime) > timedelta(hours=watched_cache_expiry)):
        print("Fetching watched media...")
        logging.info("Fetching watched media...")
        fetched_media = get_watched_media(plex, valid_sections, user=None)

        for file_path in fetched_media:
            current_media_set.add(file_path)
            if file_path not in watched_media_set:
                media_to_array.append(file_path)

        # Remove media that no longer exists in Plex
        watched_media_set.intersection_update(current_media_set)

        # Add new media to the watched media set
        watched_media_set.update(media_to_array)

        media_to_array = modify_file_paths(media_to_array, plex_source, real_source, plex_library_folders, nas_library_folders)
        media_to_array.extend(get_media_subtitles(media_to_array, files_to_skip=files_to_skip))

        with watched_cache_file.open('w') as f:
            json.dump(list(watched_media_set), f)

    else:
        print("Loading watched media from cache...")
        logging.info("Loading watched media from cache...")
        media_to_array.extend(watched_media_set)

    try:
        check_free_space_and_move_files(media_to_array, 'array', real_source, cache_dir, unraid, debug, files_to_skip)
    except Exception as e:
        logging.error(f"Error checking free space and moving media files: {str(e)}")
        exit(f"Error: {str(e)}")

# Moving the files to the cache drive
try:
    check_free_space_and_move_files(media_to_cache, 'cache', real_source, cache_dir, unraid, debug, files_to_skip)
except Exception as e:
    logging.error(f"Error checking free space and moving media files: {str(e)}")
    exit(f"Error: {str(e)}")

print("Script executed\nThank you for using my script github.com/bexem/PlexCache")
logging.info("Script executed\nThank you for using my script github.com/bexem/PlexCache")