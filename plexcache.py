import os, json, logging, glob, subprocess
from pathlib import Path
from plexapi.server import PlexServer
from plexapi.video import Episode
from plexapi.video import Movie
from plexapi.myplex import MyPlexAccount
from datetime import datetime, timedelta

script_folder="/mnt/user/system/PlexCache/"
settings_filename = os.path.join(script_folder, "settings.json")
log_file_pattern = "plexcache_script_*.log"
max_log_files = 5
log_file_prefix = log_file_pattern[:-5]
if not os.path.exists(script_folder):
    os.makedirs(script_folder)
existing_log_files = glob.glob(os.path.join(script_folder, log_file_pattern))
# Check if the number of log files exceeds the limit
if len(existing_log_files) >= max_log_files:
    # Sort the log files by creation time
    existing_log_files.sort(key=os.path.getctime)
    # Remove the oldest log file(s)
    for i in range(len(existing_log_files) - max_log_files + 1):
        os.remove(existing_log_files[i])
# Create a new log file for the current session
current_time = datetime.now().strftime("%Y%m%d_%H%M")
log_file = os.path.join(script_folder, f"{log_file_pattern[:-5]}{current_time}.log")
# Set up logging
logging.basicConfig(filename=log_file, filemode='w', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Check if the above file exists
if os.path.exists(settings_filename):
    with open(settings_filename, 'r') as f:
        settings_data = json.load(f)
else:
    logging.error("Settings file not found, please fix the variable accordingly.")
    exit("Settings file not found, please fix the variable accordingly.")

# Reads the settings file and all the settings
try:
    PLEX_URL = settings_data['PLEX_URL']
    PLEX_TOKEN = settings_data['PLEX_TOKEN']
    number_episodes = int(settings_data['number_episodes'])
    valid_sections = settings_data['valid_sections']
    users_toggle = settings_data['users_toggle']
    skip_users = settings_data['skip_users']
    watchlist_toggle = settings_data['watchlist_toggle']
    watchlist_episodes = int(settings_data['watchlist_episodes'])
    days_to_monitor = int(settings_data['days_to_monitor'])
    cache_dir = settings_data['cache_dir']
    plex_source = settings_data['plex_source']
    real_source = settings_data['real_source']
    nas_library_folders = settings_data['nas_library_folders']
    plex_library_folders = settings_data['plex_library_folders']
    unraid = settings_data['unraid']
    watched_move = settings_data['watched_move']
    watchlist_cache_expiry = int(settings_data['watchlist_cache_expiry'])
    skip = settings_data['skip']
    debug = settings_data['debug']
except KeyError as e:
    logging.error(f"Error: {e} not found in settings file, please re-run the setup or manually edit the settings file.")
    exit(f"Error: {e} not found in settings file, please re-run the setup or manually edit the settings file.")


watchlist_cache_file = Path(os.path.join(script_folder, "watchlist_cache.json"))
processed_files = []
fileToCache = []
files_to_skip = []
watched_files = []
watched_to_remove = []
media_to_cache = []
media_to_array = []
plex = PlexServer(PLEX_URL, PLEX_TOKEN)
sessions = plex.sessions()
if sessions:
    if skip != "skip":
        logging.warning('There is an active session. Exiting...')
        exit('There is an active session. Exiting...')

if debug in ['y', 'yes']:
    print("Debug mode is active, no file will be moved.")
    logging.info("Debug mode is active, no file will be moved.")

def fetch_on_deck_media(plex, valid_sections, days_to_monitor, number_episodes, user=None):
    if user:
        username = str(user).split(":")[-1].rstrip(">")
        try:
            plex = PlexServer(PLEX_URL, user.get_token(plex.machineIdentifier))
        except Exception:
            print(f"Error: Failed to Fetch {username} onDeck media")
            logging.error(f"Error: Failed to Fetch {username} onDeck media")
            return []
    else:
        plex = PlexServer(PLEX_URL, PLEX_TOKEN)
        main_username = plex.myPlexAccount().title
        print(f"Fetching {main_username}'s onDeck media...")
        logging.info(f"Fetching {main_username}'s onDeck media...")
    on_deck_files = []
    for video in plex.library.onDeck():
        if video.section().key in valid_sections:
            delta = datetime.now() - video.lastViewedAt
            if isinstance(video, Episode) and delta.days <= days_to_monitor:
                for media in video.media:
                    on_deck_files.extend(part.file for part in media.parts)
                show = video.grandparentTitle
                library_section = video.section()
                episodes = list(library_section.search(show)[0].episodes())
                current_season = video.parentIndex
                next_episodes = []
                for episode in episodes:
                    if (episode.parentIndex > current_season or (episode.parentIndex == current_season and episode.index > video.index)) and len(next_episodes) < number_episodes:
                        next_episodes.append(episode)
                    if len(next_episodes) == number_episodes:
                        break
                for episode in next_episodes:
                    for media in episode.media:
                        on_deck_files.extend(part.file for part in media.parts)
            elif isinstance(video, Movie) and delta.days <= days_to_monitor:
                for media in video.media:
                    on_deck_files.extend(part.file for part in media.parts)
    return on_deck_files

# Function to fetch watchlist media files for the main user
def fetch_watchlist_media(plex, valid_sections, watchlist_episodes):
    main_username = plex.myPlexAccount().title
    print(f"Fetching {main_username}'s watchlist media...")
    logging.info(f"Fetching {main_username}'s watchlist media...")
    user_files = []
    account = MyPlexAccount(PLEX_TOKEN)
    watchlist = account.watchlist(filter='released')
    for item in watchlist:
        # Search for the file in the Plex library
        results = plex.search(item.title)
        # Check if the file is available in the library
        if len(results) > 0:
            # Access the first result object
            file = results[0]
            # Get the section id for the file
            section_id = file.librarySectionID
            if section_id in valid_sections:
                if file.TYPE == 'show':
                    episodes = file.episodes()
                    count = 0  # Initialize counter variable
                    if count >= watchlist_episodes:
                        break
                    if len(episodes) > 0:
                        for episode in episodes[:watchlist_episodes]:
                            if len(episode.media) > 0 and len(episode.media[0].parts) > 0:
                                count += 1  # Increment the counter variable
                                if not episode.isPlayed:
                                    user_files.append((episode.media[0].parts[0].file))
                else:
                    user_files.append((file.media[0].parts[0].file))
    return user_files or []

def get_watched_media(plex, valid_sections, user=None):
    watched_files = []
    def fetch_user_watched_media(user_plex, username, token=None):
        nonlocal watched_files
        print(f"Fetching {username}'s watched media...")
        logging.info(f"Fetching {username}'s watched media...")
        try:
            for section_id in valid_sections:
                section = plex.library.sectionByID(section_id)
                for video in section.search(unwatched=False):
                    if video.TYPE == 'show':
                        for episode in video.episodes():
                            for media in episode.media:
                                watched_files.extend(part.file for part in media.parts if episode.isPlayed)
                    else:
                        watched_files.append(video.media[0].parts[0].file)
        except Exception:
            print(f"Error: Failed to Fetch {username}'s watched media")
            logging.info(f"Error: Failed to Fetch {username}'s watched media")
    # Fetch main user's watched media
    main_username = plex.myPlexAccount().title
    fetch_user_watched_media(plex, main_username)
    # Fetch other users' watched media
    for user in plex.myPlexAccount().users():
        username = str(user).split(":")[-1].rstrip(">")
        user_token = user.get_token(plex.machineIdentifier)
        user_plex = PlexServer(PLEX_URL, user_token)
        fetch_user_watched_media(user_plex, username, token=user_token)
    return watched_files

# Function to change the paths to the correct ones
def modify_file_paths(files, plex_source, real_source, plex_library_folders, nas_library_folders):
    print("Editing file paths...")
    logging.info("Editing file paths...")
    for i, file_path in enumerate(files):
        # Replace the plex_source with the real_source
        file_path = file_path.replace(plex_source, real_source)
        # Determine which library folder is in the file path
        for j, folder in enumerate(plex_library_folders):
            if folder in file_path:
                # Replace the plex library folder with the corresponding NAS library folder
                file_path = file_path.replace(folder, nas_library_folders[j])
                break
        files[i] = file_path
    return files or []

# Function to fetch the subtitles
def get_media_subtitles(media_files, files_to_skip=None):
    if files_to_skip is None:
        files_to_skip = set()
    print("Fetching subtitles...")
    logging.info("Fetching subtitles...")
    processed_files = set()
    for file in media_files:
        if file in files_to_skip:
            continue
        if file in processed_files:
            continue
        processed_files.add(file)
        directory_path = os.path.dirname(file)
        file_name, file_ext = os.path.splitext(os.path.basename(file))
        files_in_dir = os.listdir(directory_path)
        subtitle_files = [os.path.join(directory_path, file) for file in files_in_dir if file.startswith(file_name) and file != file_name+file_ext]
        if subtitle_files:
            for subtitle in subtitle_files:
                if subtitle not in media_files:
                    media_files.append(subtitle)
    return media_files or []

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

def get_free_space(dir):
    stat = os.statvfs(dir)
    free_space_bytes = stat.f_bfree * stat.f_frsize
    return convert_bytes_to_readable_size(free_space_bytes)

def get_total_size_of_files(files):
    total_size_bytes = sum(os.path.getsize(file) for file in files)
    return convert_bytes_to_readable_size(total_size_bytes)

def move_media_files(files, real_source, cache_dir, unraid, debug, destination, files_to_skip=None):
    if files_to_skip is None:
        files_to_skip = set()
    print(f"Moving media files to {destination}...")
    logging.info(f"Moving media files to {destination}...")
    processed_files = set()
    for fileToMove in files:
        if fileToMove in files_to_skip:
            continue
        if fileToMove in processed_files:
            continue
        processed_files.add(fileToMove)
        user_path = os.path.dirname(fileToMove)
        cache_path = user_path.replace(real_source, cache_dir)
        user_file_name = user_path + "/" + os.path.basename(fileToMove)
        cache_file_name = cache_path + "/" + os.path.basename(fileToMove)
        move = None
        if unraid in ['y', 'yes']:
            user_path = user_path.replace("/mnt/user/", "/mnt/user0/")  # Thanks to dada051 suggestion
        if destination == 'array':
            if not os.path.exists(user_path):  # Create destination folder if doesn't exists
                os.makedirs(user_path)
            if os.path.isfile(cache_file_name):
                if fileToMove in fileToCache:
                    logging.info(f"Skipping {os.path.basename(fileToMove)} because is also in the files to be moved to cache.")
                    continue
                move = f"mv -v \"{cache_file_name}\" \"{user_path}\""
        if destination == 'cache':
            if not os.path.exists(cache_path):  # Create destination folder if doesn't exists
                os.makedirs(cache_path)
            if not os.path.isfile(cache_file_name):
                move = f"mv -v \"{user_file_name}\" \"{cache_path}\""
        if debug in ['y', 'yes']:
            if move != None:
                print(move)
                logging.info(move)
        else:
            if move != None:
                logging.info(move)
                result = subprocess.run(move, shell=True, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    logging.error(f"Error executing move command: Exit code: {result.returncode}")
                    logging.error(f"Error message: {result.stderr.decode('utf-8')}")

# Fetches the current playing media
if sessions:
    for session in sessions:
        # Set the media ID
        media = str(session.source())
        media_id = media[media.find(":") + 1:media.find(":", media.find(":") + 1)]
        # Find the media item with the specified ID
        media_item = plex.fetchItem(int(media_id))
        # Get the title of the media item
        media_title = media_item.title
        print(f"Active session detected, skipping: {media_title}")
        logging.info(f"Active session detected, skipping: {media_title}")
        # Get the full path of the media item
        media_path = media_item.media[0].parts[0].file
        files_to_skip.append(media_path)

# Fetch onDeck media
fileToCache.extend(fetch_on_deck_media(plex, valid_sections, days_to_monitor, number_episodes))
if users_toggle in ['y', 'yes']:
    for user in plex.myPlexAccount().users():
        username = str(user)
        username = username.split(":")[-1].rstrip(">")
        if user.get_token(plex.machineIdentifier) in skip_users:
            print(f"Skipping {username}'s onDeck media...")
            logging.info(f"Skipping {username}'s onDeck media...")
            continue
        print(f"Fetching {username}'s onDeck media...")
        logging.info(f"Fetching {username}'s onDeck media...")
        fileToCache.extend(fetch_on_deck_media(plex, valid_sections, days_to_monitor, number_episodes, user=user))

# Fetch watchlist media
if watchlist_toggle in ['y', 'yes']:
    if watchlist_cache_file.exists() and (datetime.now() - datetime.fromtimestamp(watchlist_cache_file.stat().st_mtime) <= timedelta(hours=watchlist_cache_expiry)):
        logging.info("Loading watchlist media from cache...")
        with watchlist_cache_file.open('r') as f:
            fileToCache.extend(json.load(f))
    else:
        logging.info("Fetching watchlist media...")
        watchlist_media = fetch_watchlist_media(plex, valid_sections, watchlist_episodes)
        fileToCache.extend(watchlist_media)
        with watchlist_cache_file.open('w') as f:
            json.dump(watchlist_media, f)

modify_file_paths(fileToCache, plex_source, real_source, plex_library_folders, nas_library_folders)
fileToCache.extend(get_media_subtitles(fileToCache, files_to_skip=files_to_skip))

if watched_move in ['y', 'yes']:
    watched_files = get_watched_media(plex, valid_sections)
    modify_file_paths(watched_files, plex_source, real_source, plex_library_folders, nas_library_folders)
    watched_files.extend(get_media_subtitles(watched_files, files_to_skip=files_to_skip))
    processed_files = set()
    for file in fileToCache:
        if file in processed_files:
            continue
        processed_files.add(file) 
        cache_path = os.path.dirname(file).replace(real_source, cache_dir)
        cache_file_name = cache_path + "/" + os.path.basename(file)
        if os.path.isfile(cache_file_name):
            media_to_array.append(file)
    try:
        free_space, free_space_unit = get_free_space(real_source)
        total_size, total_size_unit = get_total_size_of_files(media_to_array)
        print(f"Free space on the array: {free_space:.2f} {free_space_unit}")
        print(f"Total size of watched media files to be moved to the array: {total_size:.2f} {total_size_unit}")
        logging.info(f"Free space on the array: {free_space:.2f} {free_space_unit}")
        logging.info(f"Total size of watched media files to be moved to the array: {total_size:.2f} {total_size_unit}")
        if total_size * (1024 ** {'KB': 0, 'MB': 1, 'GB': 2, 'TB': 3}[total_size_unit]) > free_space * (1024 ** {'KB': 0, 'MB': 1, 'GB': 2, 'TB': 3}[free_space_unit]):
            raise ValueError("Not enough space on destination drive.")
    except Exception as e:
        logging.error(f"Error checking free space: {str(e)}")
        exit(f"Error: {str(e)}")
    try:
        logging.info("Moving watched media...")
        print("Moving watched media...")
        move_media_files(watched_files, real_source, cache_dir, unraid, debug, destination='array', files_to_skip=files_to_skip)
    except Exception as e:
        logging.error(f"Error moving media files: {str(e)}")
        exit(f"Error: {str(e)}")

try:
    logging.info("Skipping files already in the cache drive")
    print("Skipping files already in the cache drive")
    processed_files = set()
    for file in fileToCache:
        if file in processed_files:
            continue
        processed_files.add(file)   
        cache_path = os.path.dirname(file).replace(real_source, cache_dir)
        cache_file_name = cache_path + "/" + os.path.basename(file)
        if not os.path.isfile(cache_file_name):
            media_to_cache.append(file)
    free_space, free_space_unit = get_free_space(cache_dir)
    total_size, total_size_unit = get_total_size_of_files(media_to_cache)
    print(f"Free space on the array: {free_space:.2f} {free_space_unit}")
    print(f"Total size of watched media files to be moved to the array: {total_size:.2f} {total_size_unit}")
    logging.info(f"Free space on the array: {free_space:.2f} {free_space_unit}")
    logging.info(f"Total size of watched media files to be moved to the array: {total_size:.2f} {total_size_unit}")
    if total_size * (1024 ** {'KB': 0, 'MB': 1, 'GB': 2, 'TB': 3}[total_size_unit]) > free_space * (1024 ** {'KB': 0, 'MB': 1, 'GB': 2, 'TB': 3}[free_space_unit]):
        raise ValueError("Not enough space on destination drive.")
except Exception as e:
    logging.error(f"Error checking free space: {str(e)}")
    exit(f"Error: {str(e)}")

try:
    logging.info("Moving media to the cache...")
    print("Moving media to the cache...")
    move_media_files(fileToCache, real_source, cache_dir, unraid, debug, destination='cache', files_to_skip=files_to_skip)
except Exception as e:
    logging.error(f"Error moving media files: {str(e)}")
    exit(f"Error: {str(e)}")

print("Script executed\nThank you for using my script github.com/bexem/PlexCache")
logging.info("Script executed\nThank you for using my script github.com/bexem/PlexCache")