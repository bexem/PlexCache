import json
import os
import sys
import requests
from plexapi.server import PlexServer

settings_filename = "settings.json"

print("This is the setup script for plexcache.py")

# Load existing settings data from file (if it exists)
if os.path.exists(settings_filename):
    try:
        with open(settings_filename, 'r') as f:
            settings_data = json.load(f)
            print("Settings file opened successfully.")
    except json.decoder.JSONDecodeError:
        # If the file exists but is not a valid JSON file, initialize an empty JSON object
        settings_data = {}
        print("Settings file initialised successfully.")
else:
    sys.exit("File not found, plex configure the variable settings_filename properly. Exiting...")

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


if settings_data.get('firststart') == 'yes':
    settings_data = {}
    setup()
else:
    print("Configuration exists and seems to be valid, now you should be able execute the main script.\n")
