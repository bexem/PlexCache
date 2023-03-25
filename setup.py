import json, os, requests
from plexapi.server import PlexServer
from plexapi.exceptions import BadRequest

# The script will create/edit the file in the same folder the script is located, but you can change that
script_folder="./"
settings_filename = os.path.join(script_folder, "settings.json")
        
# Function to check for a valid plex url
def is_valid_plex_url(url):
    try:
        response = requests.get(url)
        if 'X-Plex-Protocol' in response.headers:
            return True
    except requests.exceptions.RequestException:
        print (response.headers)
    print (response.headers)
    return False


# Ask user for input for missing settings
def setup():
    while 'PLEX_URL' not in settings_data:
        print("It is advised to use internet accessible plex domain if planning to fetch other users media and watchlist.")
        url = input('\nEnter your plex server address (Example: http://localhost:32400 or https://plex.mydomain.ext): ')
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
                    include = input("Do you want to include this library? [Y/n] (default: yes) ") or 'yes'
                    if include.lower() in ['n', 'no']:
                        continue
                    elif include.lower() in ['y', 'yes']:
                        valid_sections.append(library.key)
                        if 'plex_source' not in settings_data:
                            location_index = 0 
                            location = library.locations[location_index]
                            root_folder = (os.path.abspath(os.path.join(location, os.pardir)) + "/")
                            print(f"\nPlex source path autoselected and set to: {root_folder}")
                            settings_data['plex_source'] = root_folder
                        for location in library.locations:
                            plex_library_folder = ("/" + os.path.basename(location) + "/")
                            plex_library_folder = plex_library_folder.strip('/')
                            plex_library_folders.append(plex_library_folder)
                            settings_data['plex_library_folders'] = plex_library_folders
                    else:
                        print("Invalid choice. Please enter either yes or no")
                if not valid_sections:
                    print("You must select at least one library to include. Please try again.")
            settings_data['valid_sections'] = valid_sections
        except (ValueError, TypeError, BadRequest):
            print('Unable to connect to Plex server.')

    while True:
        if 'number_episodes' not in settings_data:
            number_episodes = input('\nHow many episodes (digit) do you want fetch (onDeck)? (default: 5) ') or '5'
            if number_episodes.isdigit():
                settings_data['number_episodes'] = int(number_episodes)
                break
            else:
                print("User input is not a number")

    while True:
        if 'users_toggle' not in settings_data:
            fetch_all_users = input('\nDo you want to fetch onDeck media from all other users? (default: yes) ') or 'yes'
            skip_users = []
            if fetch_all_users.lower() in ['y', 'yes']:
                settings_data['users_toggle'] = True
                skip_users_choice = input('\nWould you like to skip some of the users? [Y/n] (default: no) ') or 'no'
                if skip_users_choice.lower() in ['y', 'yes']:
                    for user in plex.myPlexAccount().users():
                        username = user.title
                        while True:
                            answer = input(f'\nDo you want to skip this user? {username} [Y/n] (default: no) ') or 'no'
                            if answer.lower() in ['y', 'yes']:
                                token = user.get_token(plex.machineIdentifier)
                                skip_users.append(token)
                                print("\n", username, " will be skipped.")
                                break
                            elif answer.lower() in ['n', 'no']:
                                break
                            else:
                                print("Invalid choice. Please enter either yes or no")
                                continue
                    settings_data['skip_users'] = skip_users
                elif skip_users_choice.lower() in ['n', 'no']:
                    settings_data['skip_users'] = []
                else:
                    print("Invalid choice. Please enter either yes or no")
                    continue
            elif fetch_all_users.lower() in ['n', 'no']:
                settings_data['users_toggle'] = False
            else:
                print("Invalid choice. Please enter either yes or no")
                continue
            break

    while True:
        if 'watchlist_toggle' not in settings_data:
            watchlist = input('\nDo you want to fetch your watchlist media? [Y/n] (default: no) ') or 'no'
            if watchlist.lower() in ['n', 'no']:
                settings_data['watchlist_toggle'] = False
                settings_data['watchlist_episodes'] = '0'
                settings_data['watchlist_cache_expiry'] = '1'
                break
            elif watchlist.lower() in ['y', 'yes']:
                settings_data['watchlist_toggle'] = True
                while True:
                    watchlist_episodes = input('How many episodes do you want fetch (watchlist) (default: 1)? ') or '1'
                    if watchlist_episodes.isdigit():
                        settings_data['watchlist_episodes'] = int(watchlist_episodes)
                        break
                    else:
                        print("User input is not a number")
                while True:
                    if 'watchlist_cache_expiry' not in settings_data:
                        hours = input('\nDefine the watchlist cache expiry duration in hours (default: 6) ') or '6'
                        if hours.isdigit():
                            settings_data['watchlist_cache_expiry'] = int(hours)
                            break
                        else:
                            print("User input is not a number")
                break
            else:
                print("Invalid choice. Please enter either yes or no")

    while True:
        if 'days_to_monitor' not in settings_data:
            days = input('\nMaximum age of the media onDeck to be fetched? (default: 99) ') or '99'
            if days.isdigit():
                settings_data['days_to_monitor'] = int(days)
                break
            else:
                print("User input is not a number")
        else:
            break

    if 'cache_dir' not in settings_data:
        cache_dir = input('\nInsert the path of your cache drive: (default: "/mnt/cache/") ').replace('"', '').replace("'", '') or '/mnt/cache/'
        while True:
            test_path = input('\nDo you want to test the given path? [Y/n] (default: yes) ') or 'yes'
            if test_path.lower() in ['y', 'yes']:
                if os.path.exists(cache_dir):
                    print('The path appears to be valid. Settings saved.')
                    break
                else:
                    print('The path appears to be invalid.')
                    edit_path = input('\nDo you want to edit the path? [Y/n] (default: yes) ') or 'yes'
                    if edit_path.lower() in ['y', 'yes']:
                        cache_dir = input('\nInsert the path of your cache drive: (default: "/mnt/cache/") ').replace('"', '').replace("'", '') or '/mnt/cache/'
                    elif edit_path.lower() in ['n', 'no']:
                        break
                    else:
                        print("Invalid choice. Please enter either yes or no")
            elif test_path.lower() in ['n', 'no']:
                break
            else:
                print("Invalid choice. Please enter either yes or no")
        settings_data['cache_dir'] = cache_dir

    if 'real_source' not in settings_data:
        real_source = input('\nInsert the path where your media folders are located?: (default: "/mnt/user/") ').replace('"', '').replace("'", '') or '/mnt/user/'
        while True:
            test_path = input('\nDo you want to test the given path? [Y/n] (default: yes) ') or 'yes'
            if test_path.lower() in ['y', 'yes']:
                if os.path.exists(real_source):
                    print('The path appears to be valid. Settings saved.')
                    break
                else:
                    print('The path appears to be invalid.')
                    edit_path = input('\nDo you want to edit the path? [Y/n] (default: yes) ') or 'yes'
                    if edit_path.lower() in ['y', 'yes']:
                        real_source = input('\nInsert the path where your media folders are located?: (default: "/mnt/user/") ').replace('"', '').replace("'", '') or '/mnt/user/'
                    elif edit_path.lower() in ['n', 'no']:
                        break
                    else:
                        print("Invalid choice. Please enter either yes or no")
            elif test_path.lower() in ['n', 'no']:
                break
            else:
                print("Invalid choice. Please enter either yes or no")
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
            if unraid.lower() in ['y', 'yes']:
                settings_data['unraid'] = True
                break
            elif unraid.lower() in ['n', 'no']:
                settings_data['unraid'] = False
                break
            else:
                print("Invalid choice. Please enter either yes or no")

    while True:
        if 'watched_move' not in settings_data:
            watched_move = input('\nDo you want to move watched media from the cache back to the cache? (default: no) [Y/n] ')  or 'no'
            if watched_move.lower() in ['y', 'yes']:
                settings_data['watched_move'] = True
                while True:
                    if 'watched_cache_expiry' not in settings_data:
                        hours = input('\nDefine the watched media cache expiry duration in hours (default: 24) ') or '24'
                        if days.isdigit():
                            settings_data['watchlist_cache_expiry'] = int(hours)
                            break
                        else:
                            print("User input is not a number")
                break
            elif watched_move.lower() in ['n', 'no']:
                settings_data['watched_move'] = False
                break
            else:
                print("Invalid choice. Please enter either yes or no")

    while True:
        if 'skip' not in settings_data:
            session = input('\nIf there is an active session in plex (someone is playing a media) do you want to exit the script or just skip the playing media? (default: skip) [skip/exit] ') or 'skip'
            if session.lower() == 'skip':
                settings_data['skip'] = True
                break
            elif session.lower() == 'exit':
                settings_data['skip'] = False
                break
            else:
                print("Invalid choice. Please enter either skip or exit")

    while True:
        if 'max_concurrent_moves_cache' not in settings_data:
            number = input('\nHow many files do you want to move from the array to the cache at the same time? (default: 5) ') or '5'
            if number.isdigit():
                settings_data['max_concurrent_moves_cache'] = int(number)
                break
            else:
                print("User input is not a number")
        else:
            break

    while True:
        if 'max_concurrent_moves_array' not in settings_data:
            number = input('\nHow many files do you want to move from the cache to the array at the same time? (default: 2) ') or '2'
            if number.isdigit():
                settings_data['max_concurrent_moves_array'] = int(number)
                break
            else:
                print("User input is not a number")
        else:
            break

    while True:
        if 'debug' not in settings_data:
            debug = input('\nDo you want to debug the script? No data will actually be moved. (default: no) [Y/n] ') or 'no'
            if debug.lower() in ['y', 'yes']:
                settings_data['debug'] = True
                break
            elif debug.lower() in ['n', 'no']:
                settings_data['debug'] = False
                break
            else:
                print("Invalid choice. Please enter either yes or no")

    settings_data['firststart'] = False

    # Save settings to file
    with open(settings_filename, 'w') as f:
        json.dump(settings_data, f, indent=4)

    print("Setup complete! You can now run the plexcache.py script. \n")
    print("If you are happy with your current settings, you can discard this script entirely. \n")
    print("So Long, and Thanks for All the Fish!")

if not os.path.exists(script_folder):
    exit('Wrong path given, please edit the "script_folder" variable accordingly.')

while True:
    if os.path.exists(settings_filename):
        try:
            with open(settings_filename, 'r') as f:
                settings_data = json.load(f)
                print(settings_filename)
                print("Settings file exists, loading...!\n")
                if not settings_data.get('firststart'):
                    print("First start unset or set to yes:\nPlease answer the following questions: \n")
                    settings_data = {}
                    setup()
                else:
                    print("Configuration exists, you can now run the plexcache.py script. \n")
                    print("If you want to configure the settings again, manually change the variable firstart to off.")
                    print("If instead you are happy with your current settings, you can discard this script entirely. \n")
                    print("So Long, and Thanks for All the Fish!")
                break
        except json.decoder.JSONDecodeError:
            # If the file exists but is not a valid JSON file, initialize an empty JSON object
            settings_data = {}
            print("Setting file initialized successfully!\n")
            break
    else:
        print("Settings file doesn't exist, please check the path:\n")
        print(settings_filename)
        creation = input("\nIf the name is correct, do you want to create the file? {Y/n] (default = yes) ") or 'yes'
        if creation.lower() in ['y', 'yes']:
            with open(settings_filename, 'w') as f:
                json.dump({}, f)
                settings_data = {}
                print("Setting file created successfully!\n")
            break 
        elif creation.lower() in ['n', 'no']:
            exit("Exiting as requested, setting file not created.")
        else:
            print("Invalid choice. Please enter either yes or no")