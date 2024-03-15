import yaml, platform, os, posixpath, ntpath, re

def load_yaml_settings(settings_filename):
# Loads settings from a given YAML file.
    try:
        with open(settings_filename, 'r') as yaml_file:
            yaml_data = yaml.safe_load(yaml_file)

        # Extract the settings from the yaml_data
        settings = {
            'exit_if_active_session': yaml_data.get('exit_if_active_session', False),
            
            'max_concurrent_moves_array': yaml_data.get('max_concurrent_moves_array', 0),
            'max_concurrent_moves_cache': yaml_data.get('max_concurrent_moves_cache', 0),
            'log_level': yaml_data.get('logging_level', 'INFO'),
            'log_folder': yaml_data.get('log_folder', 'script_folder'),
            'mover_ignore_list_file': yaml_data.get('mover_ignore_list_file', ''),

            'bash_script_path': yaml_data.get('bash_script_path', ''),
            'summary_message': yaml_data.get('summary_message', True),

            'plexapi_retry_limit': yaml_data.get('plexapi_retry_limit', 3),
            'plexapi_delay': yaml_data.get('plexapi_delay', 15),

            'plex_url': yaml_data.get('plex_url', ''),
            'plex_token': yaml_data.get('plex_token', ''),
            
            'plex_users_skip_ondeck': yaml_data.get('plex_users_skip_ondeck', []),
            'plex_users_skip_watchlist': yaml_data.get('plex_users_skip_watchlist', []),
            'plex_watchlist_users': yaml_data.get('plex_watchlist_users', []),
            
            'cache_watched_expiry': yaml_data.get('cache_watched_expiry', 0),
            'plex_watched': yaml_data.get('plex_watched', False),

            'plex_source_drive': yaml_data.get('plex_source_drive', None),
            'plex_source': yaml_data.get('plex_source', ''),

            'plex_libraries_allowed': yaml_data.get('plex_libraries_allowed', []),
            'plex_media_age': yaml_data.get('plex_media_age', 0),

            'plex_ondeck_users': yaml_data.get('plex_ondeck_users', True),
            'plex_ondeck_n_episodes': yaml_data.get('plex_ondeck_n_episodes', 0),
            
            'plex_watchlist': yaml_data.get('plex_watchlist', False),
            'plex_watchlist_n_episodes': yaml_data.get('plex_watchlist_n_episodes', 0),
            'cache_watchlist_expiry': yaml_data.get('cache_watchlist_expiry', 0),

            'cache_dir_drive': yaml_data.get('cache_dir_drive', None),
            'cache_dir': yaml_data.get('cache_dir', ''),

            'nas_folder_root_drive': yaml_data.get('nas_folder_root_drive', None),
            'nas_folder_root': yaml_data.get('nas_folder_root', ''),
            'nas_to_plex_folder_libraries': yaml_data.get('nas_to_plex_folder_libraries', [])

        }
        
        return settings

    except FileNotFoundError:
        raise ValueError(f"The file '{settings_filename}' was not found.")
    except yaml.YAMLError as exc:
        raise ValueError(f"Error in YAML configuration: {exc}")

def write_settings(filename, updates):
# Updates specific settings in the YAML file.
    try:
        # Load existing settings
        with open(filename, 'r') as f:
            data = yaml.safe_load(f)

        # Update the settings
        for key, value in updates.items():
            if key in data:
                data[key] = value

        # Write the updated settings back to the file
        with open(filename, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
    except FileNotFoundError:
        raise ValueError(f"The file '{filename}' was not found.")
    except yaml.YAMLError as exc:
        raise ValueError(f"Error in YAML configuration: {exc}")

def initialize(settings_filename):
    global bash_script_path, cache_dir, cache_watched_expiry, cache_watchlist_expiry, exit_if_active_session
    global log_folder, log_level, max_concurrent_moves_array, max_concurrent_moves_cache, nas_to_plex_folder_libraries
    global nas_folder_root, plex_libraries_allowed, plex_media_age, plex_ondeck_n_episodes, plex_source
    global plex_token, plex_url, plex_ondeck_users, plex_users_skip_ondeck, plex_users_skip_watchlist
    global plex_watched, plex_watchlist, plex_watchlist_n_episodes, summary_message, plex_source_drive
    global os_type, plexapi_delay, plexapi_retry_limit, mover_ignore_list_file

    def check_os():
        os_name = platform.system()
        # Check for Unraid
        if os_name == 'Linux' and os.path.exists('/mnt/user0/'):
            return "Unraid"
        # Check for Docker (Though this will not specify the host OS)
        if os.path.exists('/.dockerenv'):
            return "Docker"
        # Check for Windows
        if os_name == "Windows":
            return "Windows"
        # Default to Posix for all other Linux and Unix-like systems
        return "Posix"
    os_type = check_os()

    settings = load_yaml_settings(settings_filename)

    # Unpack the settings to individual variables

    plex_url = settings['plex_url']
    plex_token = settings['plex_token']

    plex_ondeck_n_episodes = settings['plex_ondeck_n_episodes']
    plex_libraries_allowed = settings['plex_libraries_allowed']
    plex_media_age = settings['plex_media_age']
    plex_ondeck_users = settings['plex_ondeck_users']
    plex_users_skip_ondeck = settings['plex_users_skip_ondeck']

    plex_users_skip_watchlist = settings['plex_users_skip_watchlist']
    plex_watchlist_users = settings['plex_watchlist_users']
    plex_watchlist = settings['plex_watchlist']
    plex_watchlist_n_episodes = settings['plex_watchlist_n_episodes']
    cache_watchlist_expiry = settings['cache_watchlist_expiry']

    cache_watched_expiry = settings['cache_watched_expiry']
    plex_watched = settings['plex_watched']

    plex_source_drive = settings.get('plex_source_drive')
    plex_source = sanitize.add_trailing_slashes(settings['plex_source'])

    cache_dir_drive = settings.get('cache_dir_drive')
    cache_dir = sanitize.remove_trailing_slashes(settings['cache_dir'])
    cache_dir = sanitize.convert_path(cache_dir, 'cache_dir', settings, cache_dir_drive)
    cache_dir = sanitize.add_trailing_slashes(settings['cache_dir'])
    #sanitize.check_folder(cache_dir)

    nas_folder_root_drive = settings.get('nas_folder_root_drive')
    nas_folder_root = sanitize.remove_trailing_slashes(settings['nas_folder_root'])
    nas_folder_root = sanitize.convert_path(nas_folder_root, 'nas_folder_root', settings, nas_folder_root_drive)
    nas_folder_root = sanitize.add_trailing_slashes(settings['nas_folder_root'])
    #sanitize.check_folder(nas_folder_root)

    # Writing the current settings as they change depending on which os the script is running
    sanitized_settings = {
        'plex_source': plex_source,
        'cache_dir': cache_dir,
        'nas_folder_root': nas_folder_root
    }
    write_settings(settings_filename, sanitized_settings)

    nas_to_plex_folder_libraries = settings['nas_to_plex_folder_libraries']

    plex_library_folders = []  # Now an empty list to populate from the dictionary
    nas_library_folders = []  # Now an empty list to populate from the dictionary

    for item in nas_to_plex_folder_libraries:
        key, value = item.split(" : ")
        nas_to_plex_folder_libraries[key.strip()] = value.strip()
        plex_library_folders.append(key.strip())
        nas_library_folders.append(value.strip())

    # Checking if folders exists in the slow storage and in the cache drive
    for folder in nas_library_folders:
        nas_complete_path = os.path.join(nas_folder_root, folder)
        cache_complete_path = os.path.join(cache_dir, folder)
        #sanitize.check_folder(nas_complete_path)
        #sanitize.check_folder(cache_complete_path)

    max_concurrent_moves_array = settings['max_concurrent_moves_array']
    max_concurrent_moves_cache = settings['max_concurrent_moves_cache']
    mover_ignore_list_file = settings['mover_ignore_list_file']

    log_level = settings['log_level']
    log_folder = settings['log_folder']
    sanitize.check_and_create_folder(log_folder)
    
    bash_script_path = settings['bash_script_path']
    summary_message = settings['summary_message']

    plexapi_retry_limit = settings['plexapi_retry_limit']
    plexapi_delay = settings['plexapi_delay']
    exit_if_active_session = settings['exit_if_active_session']


class sanitize:
    def check_folder(folder):
        # Check if the folder doesn't exist
        if not os.path.exists(folder):
            exit(f"{folder} does not exist, please fix the settings accordingly.")

    def check_and_create_folder(folder):
        # Check if the folder doesn't already exist
        if not os.path.exists(folder):
            try:
                # Create the folder with necessary parent directories
                os.makedirs(folder, exist_ok=True)
            except PermissionError:
                # Exit the program if the folder is not writable
                exit(f"{folder} not writable, please fix the settings accordingly.")

    def remove_trailing_slashes(value):
        try:
            if isinstance(value, str):
                # Check if the value is a string
                stripped_value = value.rstrip('/\\')
                if ':' in value and not stripped_value:
                    # Check if the value contains a ':' and if the value with trailing slashes removed is empty
                    # Return the value with trailing slashes removed and add a backslash at the end 
                    return stripped_value + "\\"
                return stripped_value
        except Exception as e:
            # Log an error if an exception occurs and raise it
            print(f"Error occurred while removing trailing slashes: {e}")
            raise

    # Add "/" or "\" to a given path
    def add_trailing_slashes(value):
        try:
            # Check if the value does not contain a ':', indicating it's a Windows-style path
            if ':' not in value:
                # Add a leading "/" and adds a trailing "/" 
                value = value.rstrip('/').lstrip('/')
                value = "/" + value + "/"
            return value
        except Exception as e:
            # Log an error if an exception occurs and raise it
            print(f"Error occurred while adding trailing slashes: {e}")
            raise

    # Removes all "/" "\" from a given path
    def remove_all_slashes(value_list):
        try:
            # Iterate over each value in the list and remove leading and trailing slashes
            return [value.strip('/\\') for value in value_list]
        except Exception as e:
            print(f"Error occurred while removing all slashes: {e}")
            raise

    # Convert the given path to a windows compatible path
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

    # Convert the given path to a linux/posix compatible path
    # If a drive letter is present, it will save it in the settings file.
    def convert_path_to_posix(value):
        try:
            # Save the drive letter if exists
            drive_letter = re.search(r'^[A-Za-z]:', value)  
            # Check for a drive letter at the beginning of the path
            if drive_letter:
                drive_letter = drive_letter.group() + '\\'  
                # Extract the drive letter and add a backslash
            else:
                drive_letter = None
            # Remove drive letter if exists
            value = re.sub(r'^[A-Za-z]:', '', value)  
            # Remove the drive letter from the path
            value = value.replace(ntpath.sep, posixpath.sep)  
            # Replace backslashes with forward slashes
            return posixpath.normpath(value), drive_letter  
            # Normalize the path and return it along with the drive letter
        except Exception as e:
            print(f"Error occurred while converting path to Posix compatible: {e}")
            raise

    # Convert path accordingly to the operating system the script is running
    # It assigns drive_letter = 'C:\\' if no drive was ever given/saved
    def convert_path(value, key, settings_data, drive_letter=None):
        try:
            # Normalize paths converting backslashes to slashes
            if os.name in ['posix']:  # Check if the operating system is Linux
                value, drive_letter = sanitize.convert_path_to_posix(value)  # Convert path to POSIX format
                if drive_letter:
                    settings_data[f"{key}_drive"] = drive_letter  # Save the drive letter in the settings data
            else:
                if drive_letter is None:
                    drive_letter = 'C:\\'  # Set the default drive letter to 'C:\'
                    print(f"Drive letter for {value} not found, using the default one {drive_letter}")
                value = sanitize.convert_path_to_nt(value, drive_letter)  # Convert path to Windows format
            return value
        except Exception as e:
            print(f"Error occurred while converting path: {e}")
            raise
