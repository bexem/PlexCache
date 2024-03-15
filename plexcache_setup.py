import yaml, os, requests, ntpath, posixpath, platform
from urllib.parse import urlparse
from plexapi.server import PlexServer
from plexapi.exceptions import BadRequest

# Check if the given directory exists
def check_directory_exists(folder):
    if not os.path.exists(folder):
        raise FileNotFoundError(f'Wrong path given, please edit the "{folder}" variable accordingly.')

# Read the settings containet in the settings file
def read_existing_settings(filename):
    with open(filename, 'r') as f:
        return yaml.safe_load(f)

# Write the given settings to the settings file
def write_settings(filename, data):
    with open(filename, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)

# Conver the given path to a windows compatible format
def convert_path_to_nt(value, drive_letter):
# Normalize the path to remove redundant separators and references to parent directories
    try:
        # If the path starts with '/', prepend the drive letter
        if value.startswith('/'):
            value = drive_letter.rstrip(':\\') + ':' + value
        # Replace forward slashes with backslashes
        value = value.replace(posixpath.sep, ntpath.sep)
        # Normalize the path
        return ntpath.normpath(value)
    except Exception as e:
        print(f"Error occurred while converting path to Windows compatible: {e}")
        raise

# Function to ask the user for a number and it then saves it as a setting
def prompt_user_for_number(settings_data, prompt_message, default_value, data_key, data_type=int):
    while True:
        user_input = input(prompt_message) or default_value
        if user_input.isdigit():
            settings_data[data_key] = data_type(user_input)
            break
        else:
            print("User input is not a number")

def prompt_user_for_boolean(settings_data, prompt_message, default_value, data_key):
    while True:
        user_input = input(prompt_message) or default_value
        if user_input.lower() in ['n', 'no']:
            settings_data[data_key] = False
            break
        elif user_input.lower() in ['y', 'yes']:
            settings_data[data_key] = True
            break
        else:
            print("Invalid choice. Please enter either yes or no")

def prompt_logging_level(settings_data):
    # Define available logging levels
    log_level = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if 'log_level' not in settings_data:
        print("Choose a logging level from the following options:", ", ".join(log_level))
        while True:
            chosen_level = input("Enter logging level (default: INFO): ").upper() or "INFO"
            if chosen_level in log_level:
                print(f"You've chosen the '{chosen_level}' logging level.")
                return chosen_level
            else:
                print(f"'{chosen_level}' is not a valid logging level. Please try again.")

def prompt_user_to_run_script(settings_data, data_key='bash_script_path'):
    if prompt_user_yes_no('Do you want to run a bash script at the end of each run? [y/N] '):
        script_path = input('Please enter the path to your bash script: ')
        if prompt_user_yes_no('Do you want to test if the bash script exists? [y/N] '):
            if os.path.exists(script_path):
                print('The script exists!')
                if prompt_user_yes_no('Do you want to execute/test the script now? [y/N] '):
                    try:
                        return_code = os.system(script_path)
                        if return_code != 0:
                            print(f'The script returned a non-zero exit code: {return_code}')
                            if prompt_user_yes_no('Do you want to try again? [y/N] '):
                                return prompt_user_to_run_script(settings_data, data_key)
                    except Exception as e:
                        print(f'An error occurred while executing the script: {e}')
                        if prompt_user_yes_no('Do you want to try again? [y/N] '):
                            return prompt_user_to_run_script(settings_data, data_key)
            else:
                print('The script does not exist. Please check the path and try again.')
                if prompt_user_yes_no('Do you want to try again? [y/N] '):
                    return prompt_user_to_run_script(settings_data, data_key)
        settings_data[data_key] = script_path
    else:
        print('No bash script will be executed at the end.')

def prompt_user_yes_no(prompt, default='no'):
    """Prompt user for a yes/no answer and return True for yes and False for no."""
    valid_choices = {'y': True, 'yes': True, 'n': False, 'no': False}
    answer = input(prompt) or default
    while answer.lower() not in valid_choices:
        print("Invalid choice. Please enter either yes or no.")
        answer = input(prompt) or default
    return valid_choices[answer.lower()]

def get_users_to_skip(plex):
    """Return a list of tokens for users to skip."""
    skip_tokens = []
    for user in plex.myPlexAccount().users():
        username = user.title
        token = user.get_token(plex.machineIdentifier)
        if prompt_user_yes_no(f'Do you want to skip fetching the onDeck media for {username}? [y/N] '):
            skip_tokens.append(token)
            print(f"onDeck media for {username} will be skipped.")
    return skip_tokens

# Function to check for a valid plex url
DEFAULT_PLEX_PORT = 32400

def is_valid_plex_url(url):
    try:
        response = requests.get(url)
        return 'X-Plex-Protocol' in response.headers
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return False

def validate_plex_url(input_url):
    parsed_url = urlparse(input_url)
    scheme = parsed_url.scheme
    netloc = parsed_url.netloc or input_url  # Fallback to input_url if netloc is empty
    port = parsed_url.port
    
    ports_to_try = [port] if port else [None, DEFAULT_PLEX_PORT]
    
    for port in ports_to_try:
        url_with_port = f"{netloc}:{port}" if port else netloc
        
        if scheme:
            complete_url = f"{scheme}://{url_with_port}"
            if is_valid_plex_url(complete_url):
                return complete_url
        else:
            for try_scheme in ['https', 'http']:
                complete_url = f"{try_scheme}://{url_with_port}"
                if is_valid_plex_url(complete_url):
                    return complete_url
    return None

def get_nas_folder_libraries(num_folders, plex_library_folders, options=None, file_list_no_ext=None):
    nas_to_plex_folder_libraries = []
    for i in range(num_folders):
        if options is not None and file_list_no_ext is not None:
            print("\n".join(f"{opt + 1} for {share}" for opt, share in enumerate(file_list_no_ext)))
            while True:
                try:
                    user_choice = int(input(f"Enter the corresponding Unraid share for the Plex mapped folder: '{plex_library_folders[i]}' "))
                    if 1 <= user_choice <= len(options):
                        folder_name = file_list_no_ext[user_choice - 1]
                        break
                    else:
                        print("Invalid choice. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")
        else:
            folder_name = input(f"Enter the corresponding NAS/Unraid library folder for the Plex mapped folder: (Default is the same as plex as shown) '{plex_library_folders[i]}' ") or plex_library_folders[i]
        
        folder_name = folder_name.strip('/')
        nas_to_plex_folder_libraries.append(folder_name)
    return nas_to_plex_folder_libraries

def add_libraries(libraries, operating_system, settings_data):
    plex_libraries_allowed = []
    plex_library_folders = []
    
    # Helper function to add individual library
    def add_library(library):
        plex_libraries_allowed.append(library.key)
        if 'plex_source' not in settings_data:
            location_index = 0
            location = library.locations[location_index]
            if not operating_system.lower() == 'Windows':
                root_folder = (os.path.dirname(location))
            else:
                location = convert_path_to_nt(location)
                root_folder = (ntpath.splitdrive(location)[0])
            print(f"Plex source path autoselected and set to: {root_folder}")
            settings_data['plex_source'] = root_folder
        for location in library.locations:
            if not operating_system.lower() == 'Windows':
                plex_library_folder = ("/" + os.path.basename(location)).strip('/')
            else:
                plex_library_folder = os.path.basename(location).split('\\')[-1]
            plex_library_folders.append(plex_library_folder)
        settings_data['plex_library_folders'] = plex_library_folders

    # Ask user to include all libraries
    if prompt_user_yes_no("Do you want to include all libraries? [Y/n] ", 'yes'):
        for library in libraries:
            add_library(library)
    else:
        for library in libraries:
            print(f"Your plex library name: {library.title}")
            if prompt_user_yes_no("Do you want to include this library? [Y/n] ", 'yes'):
                add_library(library)

    return plex_libraries_allowed, plex_library_folders

# Ask user for input for missing settings
def setup(settings_filename):
    # Reset settings
    settings_data = {}

    # Asks for the url
    while 'plex_url' not in settings_data:
        url_input = input('Enter your plex server address (Example: localhost:32400 or https://plex.mydomain.ext): ').strip()
        
        if not url_input:
            print("URL cannot be empty.")
            continue
        
        validated_url = validate_plex_url(url_input)
        
        if validated_url:
            print(f"Valid Plex URL. Proceeding...")
            settings_data['plex_url'] = validated_url
        else:
            print("Invalid Plex URL")

    # Ask the user for the plex token, it then tests it
    # If successfull it will ask for libraries 
    while 'plex_token' not in settings_data:
        token = input('Enter your plex token: ')
        if not token.strip():  # Check if token is not empty
            print("Token is not valid. It cannot be empty.")
            continue
        try:
            plex = PlexServer(settings_data['plex_url'], token)
            user = plex.myPlexAccount().username  # Fetching user information
            print(f"Connection successful! Currently connected as {user}")
            libraries = plex.library.sections()  # This line should raise a BadRequest exception if the token is invalid
            # if the above line doesn't raise an exception, then the token is valid.
            settings_data['plex_token'] = token
            operating_system = plex.platform
            print(f"Plex is running on {operating_system}")
            plex_libraries_allowed, plex_library_folders = add_libraries(libraries, operating_system, settings_data)
            settings_data['plex_libraries_allowed'] = plex_libraries_allowed
        except (BadRequest, requests.exceptions.RequestException): 
            print('Unable to connect to Plex server. Please check your token.')
        except ValueError:
            print('Token is not valid. It cannot be empty.')
        except TypeError:
            print('An unexpected error occurred.')

    # Asks for how many episodes 
    while 'plex_ondeck_n_episodes' not in settings_data:
        prompt_user_for_number(settings_data, 'How many episodes do you want fetch (onDeck)? (default: 5) ', '5', 'plex_ondeck_n_episodes')

    # Asks for how many days  
    while 'plex_media_age' not in settings_data:
        prompt_user_for_number(settings_data, 'Maximum age of the media onDeck to be fetched? (default: 99) ', '99', 'plex_media_age')

    # Enable all other users and if to skip specific user for the watchlist and/or ondeck media
    while 'plex_ondeck_users' not in settings_data:
        plex_users_skip_ondeck = []
        if prompt_user_yes_no('Do you want to fetch onDeck media from other users?  [Y/n] ', 'yes'):
            settings_data['plex_ondeck_users'] = True
            if prompt_user_yes_no('Would you like to skip some of the users? [y/N] '):
                plex_users_skip_ondeck = get_users_to_skip(plex)
        else:
            settings_data['plex_ondeck_users'] = False
        settings_data['plex_users_skip_ondeck'] = plex_users_skip_ondeck

    # Asks for the watchlist media and if yes it will then ask for an expiry date for the cache file
    while 'plex_watchlist' not in settings_data:
        plex_users_skip_watchlist = []
        if prompt_user_yes_no('Do you want to fetch your watchlist media? [Y/n] ', 'yes'):
            settings_data['plex_watchlist'] = True
            prompt_user_for_number(settings_data, 'How many episodes do you want fetch (watchlist) (default: 3)? ', '3', 'plex_watchlist_n_episodes')
            prompt_user_for_number(settings_data, 'Define the watchlist cache expiry duration in hours (default: 12) ', '12', 'cache_watchlist_expiry')
            if prompt_user_yes_no('Do you want to fetch watchlist media from other users?  [Y/n] ', 'yes'):
                settings_data['plex_watchlist_users'] = True
                if prompt_user_yes_no('Would you like to skip some of the users? [y/N] '):
                    plex_users_skip_watchlist = get_users_to_skip(plex)
        else:
            settings_data['plex_watchlist_users'] = False
            settings_data['plex_watchlist'] = False
            settings_data['plex_watchlist_n_episodes'] = 0
            settings_data['cache_watchlist_expiry'] = 1
        settings_data['plex_users_skip_watchlist'] = plex_users_skip_watchlist

    # If enable the script will move the files back from the cache to the array
    while 'plex_watched' not in settings_data:
        if prompt_user_yes_no('Do you want to move watched media from the cache back to the array? [y/N] '):
            settings_data['plex_watched'] = True
            prompt_user_for_number(settings_data, 'Define the wwatched cache expiry duration in hours (default: 48) ', '48', 'cache_watched_expiry')
        else:
            settings_data['plex_watched'] = False
            settings_data['cache_watched_expiry'] = 48

    # Asks for the cache/fast drives path and asks if you want to test the given path
    if 'cache_dir' not in settings_data:
        if platform.system() == 'Linux' and os.path.exists('/mnt/user0/') and os.path.exists('/boot/config/pools/'):
            file_list = os.listdir('/boot/config/pools')
            file_list_no_ext = [os.path.splitext(file)[0] for file in file_list]
            print("Choose the cache pool you want to use:")
            for options, pool in enumerate(file_list_no_ext):
                print(f"{options + 1} for {pool}")
            while True:
                try:
                    user_choice = int(input("Your choice: "))
                    if 1 <= user_choice <= len(options):
                        cache_dir = file_list_no_ext[user_choice - 1]
                        break
                    else:
                        print("Invalid choice. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")
        else:
            cache_dir = input('Insert the path of your cache drive: (default: "/mnt/cache") ').replace('"', '').replace("'", '') or '/mnt/cache'
            while True:
                if prompt_user_yes_no('Do you want to test the given path? [y/N] '):
                    if os.path.exists(cache_dir):
                        print('The path appears to be valid. Settings saved.')
                        break
                    else:
                        print('The path appears to be invalid.')
                        if prompt_user_yes_no('Do you want to edit the path? [y/N]  '):
                            cache_dir = input('Insert the path of your cache drive: (default: "/mnt/cache") ').replace('"', '').replace("'", '') or '/mnt/cache'
                        else:
                            break
                else:
                    break
        settings_data['cache_dir'] = cache_dir

    # Asks for the array/slow drives path and asks if you want to test the given path
    if 'nas_folder_root' not in settings_data:
        if platform.system() == 'Linux' and os.path.exists('/mnt/user0/') and os.path.exists('/mnt/user/'):
            nas_folder_root = "/mnt/user"
        else:
            nas_folder_root = input('Insert the path where your media folders are located?: (default: "/mnt/user") ').replace('"', '').replace("'", '') or '/mnt/user'
            while True:
                if prompt_user_yes_no('Do you want to test the given path? [y/N] '):
                    if os.path.exists(nas_folder_root):
                        print('The path appears to be valid. Settings saved.')
                        break
                    else:
                        print('The path appears to be invalid.')
                        if prompt_user_yes_no('Do you want to edit the path? [y/N]  '):
                            nas_folder_root = input('Insert the path where your media folders are located?: (default: "/mnt/user") ').replace('"', '').replace("'", '') or '/mnt/user'
                        else:
                            break
                else:
                    break
        settings_data['nas_folder_root'] = nas_folder_root

    if 'nas_to_plex_folder_libraries' not in settings_data:
        num_folders = len(plex_library_folders)
        is_linux_and_unraid = platform.system() == 'Linux' and os.path.exists('/mnt/user0/') and os.path.exists('/boot/config/shares/')

        options = None
        file_list_no_ext = None
        if is_linux_and_unraid:
            file_list = os.listdir('/boot/config/shares/')
            file_list_no_ext = [os.path.splitext(file)[0] for file in file_list]
            options = range(len(file_list_no_ext))

        nas_to_plex_folder_libraries = get_nas_folder_libraries(num_folders, plex_library_folders, options, file_list_no_ext)
        settings_data['nas_to_plex_folder_libraries'] = nas_to_plex_folder_libraries

    # Asks if to stop the script or continue if active session
    if 'exit_if_active_session' not in settings_data:
        # To be removed in favour of session detection and due to the FUSE system unraid use, possibly copy the current playing file to the cache for increased buffering speed for long media.
        # Maybe checking how far of the end of the media currently played and only copy if more than 20% left to watch.
        prompt_user_for_boolean(settings_data, 'If there is an active session in plex (someone is playing a media) do you want to exit the script (Yes) or just skip the playing media (No)? [y/N] ', 'no', 'exit_if_active_session')

    # Concurrent moving process
    if 'max_concurrent_moves_cache' not in settings_data:
        prompt_user_for_number(settings_data, 'How many files do you want to move from the array to the cache at the same time? (default: 5) ', '5', 'max_concurrent_moves_cache')

    # Concurrent moving process
    if 'max_concurrent_moves_array' not in settings_data:
        prompt_user_for_number(settings_data, 'How many files do you want to move from the cache to the array at the same time? (default: 2) ', '2', 'max_concurrent_moves_array')
        
    if platform.system() == 'Linux' and os.path.exists('/mnt/user0/') and os.path.exists('/boot/config/plugins/ca.mover.tuning'):
        print("You are using Unraid and the CA Mover Tuning plugin has been detected.")
        if prompt_user_yes_no('Would you like to create a file containing the list of media the plugin will ignore from being moved off the cache pool? [Y/n] ', 'yes'):
            if prompt_user_yes_no('Would you like to append the list to an existing file (Yes) or create a new one? (No) [y/N] '):
                while True:
                    existing_file_path = input("Enter the path of the existing text file you'd like to append to: ")
                    if os.path.exists(existing_file_path) and existing_file_path.lower().endswith('.txt'):
                        print("The path appears to be valid. Settings saved.")
                        settings_data['mover_ignore_list_file'] = existing_file_path
                        break
                    else:
                        print("The path appears to be invalid or the file is not a text file.")
                        if not prompt_user_yes_no('Do you want to edit the path? [y/N] '):
                            break
            else:
                default_file_path = os.path.join(os.path.dirname(settings_filename), 'plexcache_mover_exclusions.txt')
                print(f"Creating a new file at {default_file_path}")
                settings_data['mover_ignore_list_file'] = default_file_path
    else:
        settings_data['mover_ignore_list_file'] = ""

    settings_data['plexapi_retry_limit'] = 3 # times
    settings_data['plexapi_delay'] = 15 # seconds

    settings_data['log_level'] = prompt_logging_level(settings_data)

    # Asks for the log folder path and asks if you want to test the given path
    if 'log_folder' not in settings_data:
        default_log_folder = os.path.join(os.path.dirname(settings_filename), 'logs')
        log_folder = input(f'Insert the path for the script log folder: (default: "{default_log_folder}") ').replace('"', '').replace("'", '') or default_log_folder
        while True:
            if prompt_user_yes_no('Do you want to test the given path? [y/N] '):
                if os.path.exists(log_folder):
                    print('The path appears to be valid. Settings saved.')
                    break
                else:
                    print('The path appears to be invalid.')
                    if prompt_user_yes_no('Do you want to edit the path? [y/N] '):
                        log_folder = input(f'Insert the path for the log folder: (default: "{default_log_folder}") ').replace('"', '').replace("'", '') or default_log_folder
                    else:
                        break
            else:
                break
        settings_data['log_folder'] = log_folder

    if 'bash_script_path' not in settings_data:
        prompt_user_to_run_script(settings_data)

    # Asks if to stop the script or continue if active session
    if 'summary_message' not in settings_data:
        prompt_user_for_boolean(settings_data, 'Would you like to receive a summary message at the end of each run? [y/N] ', 'no', 'summary_message')

    write_settings(settings_filename, settings_data)

    print("Setup complete!")
    print("If you want to configure the settings again, run the main script using --setup as argument, or delete/rename the settings file.")


def initialise(settings_filename):
    settings_filename = settings_filename if settings_filename else os.path.join(os.path.dirname(os.path.abspath(__file__)), "plexcache_settings.yaml")
    check_directory_exists(os.path.dirname(settings_filename))
    # Checks if the file exists, if not it will check if the path is accessible. 
    # If so, it will ask to create the file and then initialize the file.
    if os.path.exists(settings_filename):
        try:
            #settings_data = read_existing_settings(settings_filename)
            if prompt_user_yes_no('Settings file already exists, do you want to re-run the setup? [y/N] '):
                setup(settings_filename) 
        except yaml.YAMLError:
            print("Error reading the settings file. nuking the settings file...")
            setup(settings_filename)
    else:
        setup(settings_filename)