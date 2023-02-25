import json
import os
import sys
import requests
from plexapi.server import PlexServer
from plexapi.video import Episode
from plexapi.myplex import MyPlexAccount
from datetime import datetime

settings_filename = "settings.json"

def is_valid_plex_url(url): #Function to check if the given plex url is valid
    try:
        response = requests.get(url)
        if 'X-Plex-Protocol' in response.headers:
            return True
    except requests.exceptions.RequestException:
        print (response.headers)
        pass
    print (response.headers)
    return False


def setup():
    print("Configuring the script, please answer this questions: \n")
    # Ask user for input for missing settings
    while 'PLEX_URL' not in settings_data:
        url = input('\nEnter your plex server address (http://localhost:32400): ')
        try:
            if is_valid_plex_url(url):
                print('Valid Plex URL')
                settings_data['PLEX_URL'] = url
            else:
                print('Invalid Plex URL')
        except requests.exceptions.RequestException:
            print("URL is not valid.")

    while 'PLEX_TOKEN' not in settings_data:
        token = input('\nEnter your plex token: ')
        try:
            plex = PlexServer(settings_data['PLEX_URL'], token)
            libraries = plex.library.sections()
            settings_data['PLEX_TOKEN'] = token
            print('Connection successful!')
            valid_sections = []
            plex_library_folders = []
            while not valid_sections:
                for library in libraries:
                    print(f"Your plex library name: {library.title}")
                    setting3 = input("Do you want to include this library? [Y/n] (default: yes) ") or 'yes'
                    if setting3.lower() == "n":
                        continue
                    valid_sections.append(library.key)
                    if 'plex_source' not in settings_data:
                        location_index = 0 
                        location = library.locations[location_index]
                        root_folder = (os.path.abspath(os.path.join(location, os.pardir)) + "/")
                        print(f"\nPlex source path autoselected and set to: {root_folder}")
                        setting6 = root_folder
                        settings_data['plex_source'] = setting6
                    for location in library.locations:
                        plex_library_folder = ("/" + os.path.basename(location) + "/")
                        plex_library_folder = plex_library_folder.strip('/')
                        plex_library_folders.append(plex_library_folder)
                        settings_data['plex_library_folders'] = plex_library_folders
                if not valid_sections:
                    print("You must select at least one library to include. Please try again.")
            settings_data['valid_sections'] = valid_sections
        except (ValueError, TypeError, PlexAuthenticationException):
            print('Unable to connect to Plex server.')

    if 'number_episodes' not in settings_data:
        setting3 = input('\nHow many episodes (digit) do you want fetch (onDeck)? (default: 5) ') or '5'
        settings_data['number_episodes'] = setting3

    if 'users_toggle' not in settings_data:
        setting4 = input('\nDo you want to fetch onDeck media from all other users? (default: yes) ') or 'yes'
        settings_data['users_toggle'] = setting4

    if 'watchlist_toggle' not in settings_data:
        watchlist = input('\nDo you want to fetch your watchlist media? [Y/n] (default: no)') or 'no'
        if watchlist.lower() == "n" or watchlist.lower() == "no":
            settings_data['watchlist_toggle'] = watchlist
            settings_data['watchlist_episodes'] = '0'
        else:
            settings_data['watchlist_toggle'] = watchlist
            watchlist_episodes = input('How many episodes do you want fetch (watchlist) (default: 1)? ') or '1'
            settings_data['watchlist_episodes'] = watchlist_episodes

    if 'cache_dir' not in settings_data:
        cache_dir = input('\nInsert the path of your cache drive: (default: "/mnt/cache/") ').replace('"', '').replace("'", '')  or '/mnt/cache/'
        settings_data['cache_dir'] = cache_dir

    if 'real_source' not in settings_data:
        real_source = input('\nInsert the path where your media folders are located?: (default: "/mnt/user/") ').replace('"', '').replace("'", '') or '/mnt/user/'
        settings_data['real_source'] = real_source
        num_folders = len(plex_library_folders)
        # Ask the user to input a corresponding value for each element in plex_library_folders
        nas_library_folder = []
        for i in range(num_folders):
            folder_name = input("Enter the corresponding NAS/Unraid library folder for the Plex mapped folder: (Default is the same as plex as shown) '%s' " % plex_library_folders[i]) or plex_library_folders[i]
            # Remove the real_source from folder_name if it's present
            folder_name = folder_name.replace(real_source, '')
            # Remove leading/trailing slashes
            folder_name = folder_name.strip('/')
            nas_library_folder.append(folder_name)
        settings_data['nas_library_folders'] = nas_library_folder

    if 'DAYS_TO_MONITOR' not in settings_data:
        days = input('\nMaximum age of the media onDeck to be fetched? (default: 99)') or '99'
        settings_data['DAYS_TO_MONITOR'] = days

    if 'skip' not in settings_data:
        session = input('\nIf there is an active session in plex (someone is playing a media) do you want to exit the script or just skip the playing media? (default: skip) [skip/exit] ') or 'skip'
        settings_data['skip'] = session

    if 'debug' not in settings_data:
        debug = input('\nDo you want to debug the script? No data will actually be moved. (default: no) ') or 'no'
        if debug.lower() == "y":
            settings_data['debug'] = 'yes'
        else:
            settings_data['debug'] = debug

    settings_data['firststart'] = 'off'

    # Save settings to file
    with open(settings_filename, 'w') as f:
        json.dump(settings_data, f, indent=4)

    print('Setup complete! Now you should be able execute the main script.')

# Load existing settings data from file (if it exists)
if os.path.exists(settings_filename):
    try:
        with open(settings_filename, 'r') as f:
            settings_data = json.load(f)
    except json.decoder.JSONDecodeError:
        # If the file exists but is not a valid JSON file, initialize an empty JSON object
        settings_data = {}
    if settings_data.get('firststart') == 'yes':
        settings_data = {}
        setup()
    elif settings_data.get('firststart') == 'off':
        print("Settings file loaded successfully. Proceding...\n")
        settings_data = json.load(f)           
    else:
        settings_data = {}
        setup()
else:
    sys.exit("File not found, plex configure the variable settings_filename properly. Exiting...")


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
skip = settings_data['skip']
debug = settings_data['debug']

processed_files = []
files = []
files_to_skip = []
plex = PlexServer(PLEX_URL, PLEX_TOKEN)
sessions = plex.sessions()

if sessions:
    if skip != "skip":
        print('There is an active session. Exiting...')
        exit()


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
            if section_id == 1:
                user_files.append((file.media[0].parts[0].file))
            if section_id == 2:
                if file.TYPE == 'show':
                    episodes = file.episodes()
                    count = 0  # Initialize counter variable
                    if count >= watchlist_episodes:
                        break
                    if len(episodes) > 0:
                        for episode in episodes[:watchlist_episodes]:
                            if len(episode.media) > 0 and len(episode.media[0].parts) > 0:
                                count += 1  # Increment the counter variable
                                user_files.append((episode.media[0].parts[0].file))
    return user_files or []


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
                                if episode.parentIndex > current_season or (episode.parentIndex == current_season and episode.index > video.index) and len(next_episodes) <= (number_episodes):
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
                                if episode.parentIndex > current_season or (episode.parentIndex == current_season and episode.index > video.index) and len(next_episodes) <= (number_episodes):
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


files.extend(mainuser(number_episodes))  # Main user

if watchlist_toggle == 'yes':
    files.extend(watchlist(watchlist_episodes))

if users_toggle == 'yes':
    for user in plex.myPlexAccount().users():  # All the other users
        files.extend(otherusers(user, number_episodes))


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
        disk_file_name = user_file_name.replace("/mnt/user/", "/mnt/user0/")  # Thanks to dada051 suggestion
        if debug == "yes":
            print("****Debug is ON, no file will be moved****")
            print("Moving", disk_file_name, "--> TO -->", cache_path)
            print("Cache file path:", cache_path)
            print("User file name:", user_file_name)
            print("Disk file name:", disk_file_name)
            print("Cache file name:", cache_file_name)
            print("********************************")
        else:
            print("**************************************")
            print(os.path.basename(fileToCache))
            print("File not in the cache drive, beginning the moving process")
            move = f"mv -v \"{disk_file_name}\" \"{cache_path}\""
            os.system(move)
            print("______________________________________")

print("Script executed.")
