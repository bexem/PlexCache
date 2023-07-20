import json, os, requests, ntpath, posixpath
from urllib.parse import urlparse
from plexapi.server import PlexServer
from plexapi.exceptions import BadRequest

# The script will create/edit the file in the same folder the script is located, but you can change that
script_folder="."
settings_filename = os.path.join(script_folder, "plexcache_settings.json")
        
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

# Check if the given directory exists
def check_directory_exists(folder):
    if not os.path.exists(folder):
        raise FileNotFoundError(f'Wrong path given, please edit the "{folder}" variable accordingly.')

# Read the settings containet in the settings file
def read_existing_settings(filename):
    with open(filename, 'r') as f:
        return json.load(f)

# Write the given settings to the settings file
def write_settings(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# Convert the given path to linux/posix format 
def convert_path_to_posix(path):
    path = path.replace(ntpath.sep, posixpath.sep)
    return posixpath.normpath(path)

# Conver the given path to a windows compatible format
def convert_path_to_nt(path):
    path = path.replace(posixpath.sep, ntpath.sep)
    return ntpath.normpath(path)

# Function to ask the user for a number and it then saves it as a setting
def prompt_user_for_number(prompt_message, default_value, data_key, data_type=int):
    while True:
        user_input = input(prompt_message) or default_value
        if user_input.isdigit():
            settings_data[data_key] = data_type(user_input)
            break
        else:
            print("User input is not a number")

# Ask user for input for missing settings
def setup():
    settings_data['firststart'] = False

    # Check if the given url is a valid plex server address
    def is_valid_plex_url(url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False
        
    # Asks the user for the plex server address
    while 'PLEX_URL' not in settings_data:
        url = input('\nEnter your plex server address (Example: http://localhost:32400 or https://plex.mydomain.ext): ')
        if not url.strip():  # Check if url is not empty
            print("URL is not valid. It cannot be empty.")
            continue
        try:
            if is_valid_plex_url(url):
                print('Valid Plex URL')
                settings_data['PLEX_URL'] = url
            else:
                print('Invalid Plex URL')
        except requests.exceptions.RequestException:
            print("URL is not valid.")

    # Ask the user for the plex token, it then tests it
    # If successfull it will ask for libraries 
    while 'PLEX_TOKEN' not in settings_data:
        token = input('\nEnter your plex token: ')
        if not token.strip():  # Check if token is not empty
            print("Token is not valid. It cannot be empty.")
            continue
        try:
            plex = PlexServer(settings_data['PLEX_URL'], token)
            user = plex.myPlexAccount().username  # Fetching user information
            print(f"Connection successful! Currently connected as {user}")
            libraries = plex.library.sections()  # This line should raise a BadRequest exception if the token is invalid
            # if the above line doesn't raise an exception, then the token is valid.
            settings_data['PLEX_TOKEN'] = token
            operating_system = plex.platform
            print(f"\nPlex is running on {operating_system}")
            valid_sections = []
            plex_library_folders = []
            while not valid_sections:
                for library in libraries:
                    print(f"\nYour plex library name: {library.title}")
                    include = input("Do you want to include this library? [Y/n]  ") or 'yes'
                    if include.lower() in ['n', 'no']:
                        continue
                    elif include.lower() in ['y', 'yes']:
                        valid_sections.append(library.key)
                        if 'plex_source' not in settings_data:
                            location_index = 0 
                            location = library.locations[location_index]
                            if operating_system.lower() == 'linux':
                                location_index = 0 
                                location = library.locations[location_index]
                                root_folder = (os.path.dirname(location))
                            else:
                                location = convert_path_to_nt(location)
                                root_folder = (ntpath.splitdrive(location)[0])  # Fix for plex_source
                            print(f"\nPlex source path autoselected and set to: {root_folder}")
                            settings_data['plex_source'] = root_folder
                        for location in library.locations:
                            if operating_system.lower() == 'linux':
                                plex_library_folder = ("/" + os.path.basename(location))
                                plex_library_folder = plex_library_folder.strip('/')
                            else:
                                plex_library_folder = os.path.basename(location)
                                plex_library_folder = plex_library_folder.split('\\')[-1]
                            plex_library_folders.append(plex_library_folder)
                            settings_data['plex_library_folders'] = plex_library_folders
                    else:
                        print("Invalid choice. Please enter either yes or no")
                if not valid_sections:
                    print("You must select at least one library to include. Please try again.")
            settings_data['valid_sections'] = valid_sections
        except (BadRequest, requests.exceptions.RequestException):  # Catch BadRequest if the token is invalid
            print('Unable to connect to Plex server. Please check your token.')
        except ValueError:
            print('Token is not valid. It cannot be empty.')
        except TypeError:
            print('An unexpected error occurred.')

    # Asks for how many episodes 
    while 'number_episodes' not in settings_data:
        prompt_user_for_number('\nHow many episodes (digit) do you want fetch (onDeck)? (default: 5) ', '5', 'number_episodes')

    # Asks for how many days  
    while 'days_to_monitor' not in settings_data:
        prompt_user_for_number('\nMaximum age of the media onDeck to be fetched? (default: 99) ', '99', 'days_to_monitor')

    # Asks for the watchlist media and if yes it will then ask for an expiry date for the cache file
    while 'watchlist_toggle' not in settings_data:
        watchlist = input('\nDo you want to fetch your watchlist media? [y/N] ') or 'no'
        if watchlist.lower() in ['n', 'no']:
            settings_data['watchlist_toggle'] = False
            settings_data['watchlist_episodes'] = 0
            settings_data['watchlist_cache_expiry'] = 1
        elif watchlist.lower() in ['y', 'yes']:
            settings_data['watchlist_toggle'] = True
            prompt_user_for_number('\nHow many episodes do you want fetch (watchlist) (default: 1)? ', '1', 'watchlist_episodes')
            prompt_user_for_number('\nDefine the watchlist cache expiry duration in hours (default: 6) ', '6', 'watchlist_cache_expiry')
        else:
            print("Invalid choice. Please enter either yes or no")

    # Enable all other users and if to skip specific user for the watchlist and/or ondeck media
    while 'users_toggle' not in settings_data:
        skip_users = []
        skip_ondeck = []
        skip_watchlist = []
        fetch_all_users = input('\nDo you want to fetch onDeck/watchlist media from other users?  [Y/n] ') or 'yes'
        if fetch_all_users.lower() not in ['y', 'yes', 'n', 'no']:
            print("Invalid choice. Please enter either yes or no")
            continue
        if fetch_all_users.lower() in ['y', 'yes']:
            settings_data['users_toggle'] = True
            skip_users_choice = input('\nWould you like to skip some of the users? [y/N]') or 'no'
            if skip_users_choice.lower() not in ['y', 'yes', 'n', 'no']:
                print("Invalid choice. Please enter either yes or no")
                continue
            if skip_users_choice.lower() in ['y', 'yes']:
                for user in plex.myPlexAccount().users():
                    username = user.title
                    while True:
                        answer = input(f'\nDo you want to skip this user? {username} [y/N] ') or 'no'
                        if answer.lower() not in ['y', 'yes', 'n', 'no']:
                            print("Invalid choice. Please enter either yes or no")
                            continue                
                        if answer.lower() in ['y', 'yes']:
                            token = user.get_token(plex.machineIdentifier)
                            skip_users.append(token)
                            print("\n", username, " will be skipped.")

                            answer_ondeck = input(f'\nDo you want to skip fetching the onDeck media for {username}? [y/N] ') or 'no'
                            if answer_ondeck.lower() in ['y', 'yes']:
                                skip_ondeck.append(token)
                                print(f"\nonDeck media for {username} will be skipped.")

                            answer_watchlist = input(f'\nDo you want to skip fetching the watchlist media for {username}? [y/N] ') or 'no'
                            if answer_watchlist.lower() in ['y', 'yes']:
                                skip_watchlist.append(token)
                                print(f"\nWatchlist media for {username} will be skipped.")
                        break
        else:
            settings_data['users_toggle'] = False
        settings_data['skip_users'] = skip_users
        settings_data['skip_ondeck'] = skip_ondeck
        settings_data['skip_watchlist'] = skip_watchlist

    # If enable the script will move the files back from the cache to the array
    while 'watched_move' not in settings_data:
        watched_move = input('\nDo you want to move watched media from the cache back to the array? [y/N] ') or 'no'
        if watched_move.lower() in ['n', 'no']:
            settings_data['watched_move'] = False
            settings_data['watched_cache_expiry'] = 48
        elif watched_move.lower() in ['y', 'yes']:
            settings_data['watched_move'] = True
            prompt_user_for_number('\nDefine the wwatched cache expiry duration in hours (default: 48) ', '48', 'watched_cache_expiry')
        else:
            print("Invalid choice. Please enter either yes or no")

    # Asks for the cache/fast drives path and asks if you want to test the given path
    if 'cache_dir' not in settings_data:
        cache_dir = input('\nInsert the path of your cache drive: (default: "/mnt/cache") ').replace('"', '').replace("'", '') or '/mnt/cache'
        while True:
            test_path = input('\nDo you want to test the given path? [y/N]  ') or 'no'
            if test_path.lower() in ['y', 'yes']:
                if os.path.exists(cache_dir):
                    print('The path appears to be valid. Settings saved.')
                    break
                else:
                    print('The path appears to be invalid.')
                    edit_path = input('\nDo you want to edit the path? [y/N]  ') or 'no'
                    if edit_path.lower() in ['y', 'yes']:
                        cache_dir = input('\nInsert the path of your cache drive: (default: "/mnt/cache") ').replace('"', '').replace("'", '') or '/mnt/cache'
                    elif edit_path.lower() in ['n', 'no']:
                        break
                    else:
                        print("Invalid choice. Please enter either yes or no")
            elif test_path.lower() in ['n', 'no']:
                break
            else:
                print("Invalid choice. Please enter either yes or no")
        settings_data['cache_dir'] = cache_dir

    # Asks for the array/slow drives path and asks if you want to test the given path
    if 'real_source' not in settings_data:
        real_source = input('\nInsert the path where your media folders are located?: (default: "/mnt/user") ').replace('"', '').replace("'", '') or '/mnt/user'
        while True:
            test_path = input('\nDo you want to test the given path? [y/N]  ') or 'no'
            if test_path.lower() in ['y', 'yes']:
                if os.path.exists(real_source):
                    print('The path appears to be valid. Settings saved.')
                    break
                else:
                    print('The path appears to be invalid.')
                    edit_path = input('\nDo you want to edit the path? [y/N]  ') or 'no'
                    if edit_path.lower() in ['y', 'yes']:
                        real_source = input('\nInsert the path where your media folders are located?: (default: "/mnt/user") ').replace('"', '').replace("'", '') or '/mnt/user'
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
            folder_name = input(f"\nEnter the corresponding NAS/Unraid library folder for the Plex mapped folder: (Default is the same as plex as shown) '{plex_library_folders[i]}' ") or plex_library_folders[i]
            folder_name = folder_name.replace(real_source, '')
            folder_name = folder_name.strip('/')
            nas_library_folder.append(folder_name)
        settings_data['nas_library_folders'] = nas_library_folder

    # Asks if to stop the script or continue if active session
    while 'exit_if_active_session' not in settings_data:
        session = input('\nIf there is an active session in plex (someone is playing a media) do you want to exit the script (Yes) or just skip the playing media (No)? [y/N] ') or 'no'
        if session.lower() in ['n', 'no']:
            settings_data['exit_if_active_session'] = False
        elif session.lower() in ['y', 'yes']:
            settings_data['exit_if_active_session'] = True
        else:
            print("Invalid choice. Please enter either yes or no")

    # Concurrent moving process
    if 'max_concurrent_moves_cache' not in settings_data:
        prompt_user_for_number('\nHow many files do you want to move from the array to the cache at the same time? (default: 5) ', '5', 'max_concurrent_moves_cache')

    # Concurrent moving process
    if 'max_concurrent_moves_array' not in settings_data:
        prompt_user_for_number('\nHow many files do you want to move from the cache to the array at the same time? (default: 2) ', '2', 'max_concurrent_moves_array')

    # Activates the debug mode
    while 'debug' not in settings_data:
        debug = input('\nDo you want to debug the script? No data will actually be moved. [y/N] ') or 'no'
        if debug.lower() in ['n', 'no']:
            settings_data['debug'] = False
        elif debug.lower() in ['y', 'yes']:
            settings_data['debug'] = True
        else:
            print("Invalid choice. Please enter either yes or no")

    write_settings(settings_filename, settings_data)

    print("Setup complete! You can now run the plexcache.py script. \n")
    print("If you are happy with your current settings, you can discard this script entirely. \n")
    print("\nThank you for using bexem's script: \nhttps://github.com/bexem/PlexCache")
    print("So Long, and Thanks for All the Fish!")

check_directory_exists(script_folder)

# Checks if the file exist, if not it will check if the path is accessible, if so it will ask to create the file and then initialise the file.
if os.path.exists(settings_filename):
    try:
        settings_data = read_existing_settings(settings_filename)
        print("Settings file exists, loading...!\n")
        
        if settings_data.get('firststart'):
            print("First start unset or set to yes:\nPlease answer the following questions: \n")
            settings_data = {}
            setup()
        else:
            print("Configuration exists and appears to be valid, you can now run the plexcache.py script.\n")
            print("If you want to configure the settings again, manually change the variable 'firststart' to 'True' or delete the file entirely.\n")
            print("If instead you are happy with your current settings, you can discard this script entirely.\n")
            print("\nThank you for using bexem's script: \nhttps://github.com/bexem/PlexCache")
            print("So Long, and Thanks for All the Fish!")
    except json.decoder.JSONDecodeError:
        print("Setting file initialized successfully!\n")
        settings_data = {}
        setup()
else:
    print(f"Settings file {settings_filename} doesn't exist, please check the path:\n")
    creation = input("\nIf the path is correct, do you want to create the file? [Y/n] ") or 'yes'
    if creation.lower() in ['y', 'yes']:
        print("Setting file created successfully!\n")
        settings_data = {}
        setup()
    elif creation.lower() in ['n', 'no']:
        exit("Exiting as requested, setting file not created.")
    else:
        print("Invalid choice. Please enter either 'yes' or 'no'")
