import json
import os
import requests
from plexapi.server import PlexServer
from plexapi.exceptions import BadRequest

# The script will create/edit the file in the same folder the script is located, but you can change that
settings_filename = 'settings_new.json'

while True:
    if os.path.exists(settings_filename):
        try:
            with open(settings_filename, 'r') as f:
                settings_data = json.load(f)
                print("Setting file loaded successfully!\n")
                break
        except json.decoder.JSONDecodeError:
            # If the file exists but is not a valid JSON file, initialize an empty JSON object
            settings_data = {}
            print("Setting file initialized successfully!\n")
            break
    else:
        print("Settings file doesn't exist, please check the path:\n")
        print(settings_filename)
        creation = input("\nIf it correct, do you want to create the file? {Y/n] (default = no)") or 'no'
        if creation.lower() == "y" or creation.lower() == "yes":
            with open(settings_filename, 'w') as f:
                json.dump({}, f)
                settings_data = {}
                print("Setting file created successfully!\n")
            break 
        else:
            exit("Exiting as requested, setting file not created.") 

# Function to check for a valid plex url
def is_valid_plex_url(url):
    try:
        response = requests.get(url)
        if 'X-Plex-Protocol' in response.headers:
            return True
    except requests.exceptions.RequestException:
        print (response.headers)
        pass
    print (response.headers)
    return False


# Ask user for input for missing settings
def setup():
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
        except (ValueError, TypeError, BadRequest):
            print('Unable to connect to Plex server.')

    while True:
        if 'number_episodes' not in settings_data:
            number_episodes = input('\nHow many episodes (digit) do you want fetch (onDeck)? (default: 5) ') or '5'
            if number_episodes.isdigit():
                settings_data['DAYS_TO_MONITOR'] = number_episodes
                break
            else:
                print("User input is not a number")

    while True:
        if 'users_toggle' not in settings_data:
            user_toggle = input('\nDo you want to fetch onDeck media from all other users? (default: yes) ') or 'yes'
            if user_toggle.lower() == 'y' or user_toggle.lower() == 'yes':
                settings_data['users_toggle'] = user_toggle
                break
            elif user_toggle.lower() == 'n' or user_toggle.lower() == 'no':
                settings_data['users_toggle'] = user_toggle
                break
            else:
                print("Invalid choice. Please enter either yes or no")

    while True:
        if 'watchlist_toggle' not in settings_data:
            watchlist = input('\nDo you want to fetch your watchlist media? [Y/n] (default: no)') or 'no'
            if watchlist.lower() == "n" or watchlist.lower() == "no":
                settings_data['watchlist_toggle'] = watchlist
                settings_data['watchlist_episodes'] = '0'
                break
            elif watchlist.lower() == "y" or watchlist.lower() == "yes":
                settings_data['watchlist_toggle'] = watchlist
                while True:
                    watchlist_episodes = input('How many episodes do you want fetch (watchlist) (default: 1)? ') or '1'
                    if watchlist_episodes.isdigit():
                        settings_data['watchlist_episodes'] = watchlist_episodes
                        break
                    else:
                        print("User input is not a number")
                break
            else:
                print("Invalid choice. Please enter either yes or no")
        

    while True:
        if 'DAYS_TO_MONITOR' not in settings_data:
            days = input('\nMaximum age of the media onDeck to be fetched? (default: 99)') or '99'
        if days.isdigit():
            settings_data['DAYS_TO_MONITOR'] = days
            break
        else:
            print("User input is not a number")

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

    while True:
        if 'unraid' not in settings_data:
            unraid = input('\nAre you planning to run plexache.py on unraid? (default: yes) [Y/n] ')  or 'yes'
            if unraid.lower() == 'skip':
                settings_data['unraid'] = unraid
                break
            elif unraid.lower() == 'exit':
                settings_data['unraid'] = unraid
                break
            else:
                print("Invalid choice. Please enter either yes or no")

    while True:
        if 'watched_move' not in settings_data:
            watched_move = input('\nDo you want to move watched media from the cache back to the cache? (default: no) [Y/n] ')  or 'no'
            if watched_move.lower() == "y" or watched_move.lower() == "yes":
                settings_data['watched_move'] = watched_move
                break
            elif watched_move.lower() == "n" or watched_move.lower() == "no":
                settings_data['watched_move'] = watched_move
                break
            else:
                print("Invalid choice. Please enter either yes or no")

    while True:
        if 'skip' not in settings_data:
            session = input('\nIf there is an active session in plex (someone is playing a media) do you want to exit the script or just skip the playing media? (default: skip) [skip/exit] ') or 'skip'
            if session.lower() == 'skip':
                settings_data['skip'] = session
                break
            elif session.lower() == 'exit':
                settings_data['skip'] = session
                break
            else:
                print("Invalid choice. Please enter either skip or exit")

    while True:
        if 'debug' not in settings_data:
            debug = input('\nDo you want to debug the script? No data will actually be moved. (default: no) [Y/n]') or 'no'
            if debug.lower() == "y" or debug.lower() == "yes":
                settings_data['debug'] = 'yes'
                break
            elif debug.lower() == "n" or debug.lower() == "no":
                settings_data['debug'] = 'no'
                break
            else:
                print("Invalid choice. Please enter either yes or no")

    settings_data['firststart'] = 'off'

    # Save settings to file
    with open(settings_filename, 'w') as f:
        json.dump(settings_data, f, indent=4)

    print("Setup complete! You can now run the plexcache.py script. \n")
    print("If you are happy with your current settings, you can discard this script entirely. \n")
    print("So Long, and Thanks for All the Fish!")


if settings_data.get('firststart') == 'yes' or settings_data.get('firststart') != 'off':
    print("Please answer the following questions: \n")
    settings_data = {}
    setup()
else:
    print("Configuration exists, you can now run the plexcache.py script. \n")
    print("If you want to configure the settings again, manually change the variable firstart to off.")
    print("If instead you are happy with your current settings, you can discard this script entirely. \n")
    print("So Long, and Thanks for All the Fish!")
