import os
import json
from plexapi.server import PlexServer
from plexapi.video import Episode
from plexapi.myplex import MyPlexAccount
from datetime import datetime

# Please insert the settings filename (and path if not in the same folder)
# Examples: 
# # "settings.json"
# # "/myfolder/settings.json"
# # "myspecialfilename.json"
# # "/myfolder/myspecialfilename.json"
settings_filename = "/mnt/user/system/PlexCache/settings_test.json"

# Check if the above file exists
if os.path.exists(settings_filename):
    with open(settings_filename, 'r') as f:
        settings_data = json.load(f)
else:
    exit("Settings file not found, please fix the variable accordingly.")

# Reads the settings file and all the settings
try:
    PLEX_URL = settings_data['PLEX_URL']
    PLEX_TOKEN = settings_data['PLEX_TOKEN']
    number_episodes = int(settings_data['number_episodes'])
    valid_sections = settings_data['valid_sections']
    users_toggle = settings_data['users_toggle']
    watchlist_toggle = settings_data['watchlist_toggle']
    watchlist_episodes = int(settings_data['watchlist_episodes'])
    DAYS_TO_MONITOR = int(settings_data['DAYS_TO_MONITOR'])
    cache_dir = settings_data['cache_dir']
    plex_source = settings_data['plex_source']
    real_source = settings_data['real_source']
    nas_library_folders = settings_data['nas_library_folders']
    plex_library_folders = settings_data['plex_library_folders']
    unraid = settings_data['unraid']
    watched_move = settings_data['watched_move']
    skip = settings_data['skip']
    debug = settings_data['debug']
except KeyError as e:
    exit(f"Error: {e} not found in settings file, please re-run the setup or manually edit the settings file.")


processed_files = []
files = []
files_to_skip = []
watched_files = []
watched_to_remove = []
media_to_move = []
plex = PlexServer(PLEX_URL, PLEX_TOKEN)
sessions = plex.sessions()

if sessions:
    if skip != "skip":
        exit('There is an active session. Exiting...')


# Function to fetch watchlist media files for the main user
def watchlist(watchlist_episodes):
    user_files = []
    account = MyPlexAccount(PLEX_TOKEN)
    watchlist = account.watchlist(filter='available')
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

# Function to fetch onDeck media files for the other users
def otherusers(user, number_episodes):
    user_plex = PlexServer(PLEX_URL, user.get_token(plex.machineIdentifier))
    user_files = []
    for video in user_plex.library.onDeck():
        if video.section().key in valid_sections:
            delta = datetime.now() - video.lastViewedAt
            if delta.days <= DAYS_TO_MONITOR:
                if isinstance(video, Episode):  # TV Series
                    for media in video.media:
                        for part in media.parts:                   
                            show = video.grandparentTitle
                            # Get the library the video belongs to
                            library_section = video.section()
                            # Get the episodes of the show in the library
                            episodes = [e for e in library_section.search(show)[0].episodes()]  # Fetches the next 5 episodes
                            next_episodes = []
                            current_season = video.parentIndex
                            user_files.append((part.file))
                            for episode in episodes:
                                if episode.parentIndex > current_season or (episode.parentIndex == current_season and episode.index > video.index) and len(next_episodes) < (number_episodes):
                                    next_episodes.append(episode)
                                if len(next_episodes) == number_episodes:
                                    break
                            for episode in next_episodes:  # Adds the episodes
                                for media in episode.media:
                                    for part in media.parts:
                                        user_files.append((part.file))
                else:  # Movies
                    for media in video.media:
                        for part in media.parts:
                            user_files.append((part.file))
    return user_files or []

# Function to fetch onDeck media files for the main user
def mainuser(number_episodes):
    user_files = []
    for video in plex.library.onDeck():
        # Apply section filter
        if video.section().key in valid_sections:
            delta = datetime.now() - video.lastViewedAt
            if int(delta.days) <= DAYS_TO_MONITOR:
                if isinstance(video, Episode):  # TV Series
                    for media in video.media:
                        for part in media.parts:
                            show = video.grandparentTitle
                            # Get the library the video belongs to
                            library_section = video.section()
                            # Get the episodes of the show in the library
                            episodes = [e for e in library_section.search(show)[0].episodes()]  # Fetches the next 5 episodes
                            next_episodes = []
                            current_season = video.parentIndex
                            files.append((part.file))
                            for episode in episodes:
                                if episode.parentIndex > current_season or (episode.parentIndex == current_season and episode.index > video.index) and len(next_episodes) < (number_episodes):
                                    next_episodes.append(episode)
                                if len(next_episodes) == number_episodes:
                                    break
                            for episode in next_episodes:  # Adds the episodes
                                for media in episode.media:
                                    for part in media.parts:
                                        files.append((part.file))
                else:  # Movies
                    for media in video.media:
                        for part in media.parts:
                            files.append((part.file))
    return user_files or []

# Function to change the paths to the correct ones
def modify_file_paths(files, plex_source, real_source, plex_library_folders, nas_library_folders):
    for i, file_path in enumerate(files):
        # Replace the plex_source with the real_source
        file_path = file_path.replace(plex_source, real_source)
        # Determine which library folder is in the file path
        for j, folder in enumerate(plex_library_folders):
            path_component = os.path.basename(file_path)
            if path_component == folder:
                # Replace the plex library folder with the corresponding NAS library folder
                file_path = file_path.replace(folder, nas_library_folders[j])
                break
        files[i] = file_path
    return files or []

# Fetches onDeck media for the main user
files.extend(mainuser(number_episodes))  
if watchlist_toggle == 'yes':
    # Fetches watchlist media for the main user
    files.extend(watchlist(watchlist_episodes))

if users_toggle == 'yes':
    # Fetches onDeck media for the other users
    for user in plex.myPlexAccount().users():  
        files.extend(otherusers(user, number_episodes))

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
        # Get the full path of the media item
        media_path = media_item.media[0].parts[0].file
        files_to_skip.append(media_path)


# For the media to be moved
modify_file_paths(files, plex_source, real_source, plex_library_folders, nas_library_folders)
# For the watched media
modify_file_paths(watched_files, plex_source, real_source, plex_library_folders, nas_library_folders)


if watched_move == 'yes':
    #Fetches watched media
    for user in plex.myPlexAccount().users():  # All the other users
        user_plex = PlexServer(PLEX_URL, user.get_token(plex.machineIdentifier))
        for section_id in valid_sections:
            section = plex.library.sectionByID(section_id)
            for video in section.search(unwatched=False):
                if video.TYPE == 'show':
                    for episode in video.episodes():
                        for media in episode.media:
                            for part in media.parts:
                                if episode.isPlayed:
                                    watched_files.append(part.file)  
                else:
                    watched_files.append(video.media[0].parts[0].file)
    # Moves watched media from the cache drive to the slow drives
    for file in watched_files:
        media_file_path = os.path.dirname(file)
        user_path = media_file_path.replace(plex_source, real_source)
        cache_path = user_path.replace(real_source, cache_dir)
        user_file_name = user_path + "/" + os.path.basename(file)
        cache_file_name = cache_path + "/" + os.path.basename(file)
        if not os.path.exists(user_path):  # If the path that will end up containing the media file does not exist, this lines will create it
            os.makedirs(user_path)
        if os.path.isfile(cache_file_name):
            if unraid == 'yes':
                disk_file_name = user_file_name.replace("/mnt/user/", "/mnt/user0/")  # Thanks to dada051 suggestion
            else:
                disk_file_name = user_file_name
            if debug == "yes":
                print("Debug mode is ON:")
                print("Moving", cache_path, "--> TO -->", disk_file_name)
                print("______________________________________")
            else:
                print("Watched media is present in the cache drive, beginning the moving process")
                #move = f"mv -v \"{disk_file_name}\" \"{cache_path}\""
                #os.system(move)
                print("______________________________________")
            watched_to_remove.append(file)
    watched_size = sum(os.path.getsize(file) for file in watched_to_remove)

for file in files:
    media_file_path = os.path.dirname(file)
    user_path = media_file_path.replace(plex_source, real_source)
    cache_path = user_path.replace(real_source, cache_dir)
    cache_file_name = cache_path + "/" + os.path.basename(file)
    if not os.path.isfile(cache_file_name):
        media_to_move.append(file)

#Check for free space before attempting to move the files
total_size = sum(os.path.getsize(file) for file in media_to_move)
free_space = os.statvfs(cache_dir).f_bfree * os.statvfs(cache_dir).f_frsize
print(f"Free space on cache drive: {free_space / (1024**3):.2f} GB")
print(f"Total size of media files: {total_size / (1024**3):.2f} GB")
if watched_move == 'yes':
    total_size -= watched_size
    print(f"Total size of media files minus the watched media: {total_size / (1024**3):.2f} GB")
if total_size > free_space:
    exit("Error: Not enough space on destination drive.")


# Search for subtitle files (any file with similar file name but different extension)
processed_files = set()
for count, fileToCache in enumerate(files):
    if fileToCache in processed_files:
        continue
    processed_files.add(fileToCache)
    directory_path = os.path.dirname(fileToCache)
    if fileToCache in files_to_skip:
        print("Those files are currently used, skipping...")
        print(fileToCache)
        continue
    directory_path = directory_path.replace(plex_source, real_source)
    file_name, file_ext = os.path.splitext(os.path.basename(fileToCache))
    files_in_dir = os.listdir(directory_path)
    subtitle_files = [os.path.join(directory_path, file) for file in files_in_dir if file.startswith(file_name) and file != file_name+file_ext]
    if subtitle_files:
        for subtitle in subtitle_files:
            if subtitle not in files:
                files.append(subtitle)

# Correct all paths locating the file in the unraid array and move the files to the cache drive
processed_files = set()
for count, fileToCache in enumerate(files):
    if fileToCache in processed_files:
        continue
    if fileToCache in files_to_skip:
        continue
    media_file_path = os.path.dirname(fileToCache)
    user_path = media_file_path.replace(plex_source, real_source)
    cache_path = user_path.replace(real_source, cache_dir)
    user_file_name = user_path + "/" + os.path.basename(fileToCache)
    cache_file_name = cache_path + "/" + os.path.basename(fileToCache)
    if not os.path.exists(cache_path):  # If the path that will end up containing the media file does not exist, this lines will create it
        os.makedirs(cache_path)
    if not os.path.isfile(cache_file_name):
        if unraid == 'yes':
            disk_file_name = user_file_name.replace("/mnt/user/", "/mnt/user0/")  # Thanks to dada051 suggestion
        else:
            disk_file_name = user_file_name
        if debug == "yes":
            print("Debug is ON, File does not exists on the cache")
            print("Moving", disk_file_name, "--> TO -->", cache_path)
            print("Cache file path:", cache_path)
            print("User file name:", user_file_name)
            print("Disk file name:", disk_file_name)
            print("Cache file name:", cache_file_name)
            print("********************************")
        else:
            print("File not in the cache drive, beginning the moving process:")
            move = f"mv -v \"{disk_file_name}\" \"{cache_path}\""
            os.system(move)
            print("______________________________________")
    else:
        if debug == "yes":
            print("Debug is ON, File already exists on the cache")
            print("Cache file path:", cache_path)
            print("Cache file name:", cache_file_name)
            print("********************************")

print("Script executed.")
# Thank you for using my script github.com/bexem/PlexOnDeckCache