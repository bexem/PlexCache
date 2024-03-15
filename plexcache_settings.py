import yaml, platform, os, posixpath, ntpath, re

def load_yaml_settings(settings_filename):
    """Loads settings from a given YAML file."""
    try:
        with open(settings_filename, 'r') as yaml_file:
            yaml_data = yaml.safe_load(yaml_file)
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
    """Updates specific settings in the YAML file."""
    try:
        with open(filename, 'r') as f:
            data = yaml.safe_load(f)
        for key, value in updates.items():
            if key in data:
                data[key] = value
        with open(filename, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
    except FileNotFoundError:
        raise ValueError(f"The file '{filename}' was not found.")
    except yaml.YAMLError as exc:
        raise ValueError(f"Error in YAML configuration: {exc}")


def check_os():
    """Checks the operating system."""
    os_name = platform.system()
    if os_name == 'Linux' and os.path.exists('/mnt/user0/'):
        return "Unraid"
    if os.path.exists('/.dockerenv'):
        return "Docker"
    if os_name == "Windows":
        return "Windows"
    return "Posix"


def initialize(settings_filename):
    """Initializes the script settings."""
    global bash_script_path, cache_dir, cache_watched_expiry, cache_watchlist_expiry, exit_if_active_session
    global log_folder, log_level, max_concurrent_moves_array, max_concurrent_moves_cache, nas_to_plex_folder_libraries
    global nas_folder_root, plex_libraries_allowed, plex_media_age, plex_ondeck_n_episodes, plex_source
    global plex_token, plex_url, plex_ondeck_users, plex_users_skip_ondeck, plex_users_skip_watchlist
    global plex_watched, plex_watchlist, plex_watchlist_n_episodes, summary_message, plex_source_drive
    global os_type, plexapi_delay, plexapi_retry_limit, mover_ignore_list_file

    os_type = check_os()
    settings = load_yaml_settings(settings_filename)

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
    nas_folder_root_drive = settings.get('nas_folder_root_drive')
    nas_folder_root = sanitize.remove_trailing_slashes(settings['nas_folder_root'])
    nas_folder_root = sanitize.convert_path(nas_folder_root, 'nas_folder_root', settings, nas_folder_root_drive)
    nas_folder_root = sanitize.add_trailing_slashes(settings['nas_folder_root'])

    sanitized_settings = {
        'plex_source': plex_source,
        'cache_dir': cache_dir,
        'nas_folder_root': nas_folder_root
    }
    write_settings(settings_filename, sanitized_settings)

    nas_to_plex_folder_libraries = settings['nas_to_plex_folder_libraries']
    plex_library_folders = list(nas_to_plex_folder_libraries.keys())
    nas_library_folders = list(nas_to_plex_folder_libraries.values())
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
    @staticmethod
    def check_folder(folder):
        """Checks if a folder exists."""
        if not os.path.exists(folder):
            exit(f"{folder} does not exist, please fix the settings accordingly.")

    @staticmethod
    def check_and_create_folder(folder):
        """Checks if a folder exists and creates it if it doesn't."""
        if not os.path.exists(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except PermissionError:
                exit(f"{folder} not writable, please fix the settings accordingly.")

    @staticmethod
    def remove_trailing_slashes(value):
        """Removes trailing slashes from a path."""
        try:
            stripped_value = value.rstrip('/\\')
            if ':' in value and not stripped_value:
                return stripped_value + "\\"
            return stripped_value
        except Exception as e:
            print(f"Error occurred while removing trailing slashes: {e}")
            raise

    @staticmethod
    def add_trailing_slashes(value):
        """Adds trailing slashes to a path."""
        try:
            if ':' not in value:
                value = value.rstrip('/').lstrip('/')
                value = "/" + value + "/"
            return value
        except Exception as e:
            print(f"Error occurred while adding trailing slashes: {e}")
            raise

    @staticmethod
    def remove_all_slashes(value_list):
        """Removes all slashes from a list of paths."""
        try:
            return [value.strip('/\\') for value in value_list]
        except Exception as e:
            print(f"Error occurred while removing all slashes: {e}")
            raise

    @staticmethod
    def convert_path_to_nt(value, drive_letter):
        """Converts a path to Windows format."""
        try:
            if value.startswith('/'):
                value = drive_letter.rstrip(':\\') + ':' + value
            value = value.replace(posixpath.sep, ntpath.sep)
            return ntpath.normpath(value)
        except Exception as e:
            print(f"Error occurred while converting path to Windows compatible: {e}")
            raise

    @staticmethod
    def convert_path_to_posix(value):
        """Converts a path to POSIX format."""
        try:
            drive_letter = re.search(r'^[A-Za-z]:', value)
            if drive_letter:
                drive_letter = drive_letter.group() + '\\'
            else:
                drive_letter = None
            value = re.sub(r'^[A-Za-z]:', '', value)
            value = value.replace(ntpath.sep, posixpath.sep)
            return posixpath.normpath(value), drive_letter
        except Exception as e:
            print(f"Error occurred while converting path to Posix compatible: {e}")
            raise

    @staticmethod
    def convert_path(value, key, settings_data, drive_letter=None):
        """Converts a path based on the operating system."""
        try:
            if os.name in ['posix']:
                value, drive_letter = sanitize.convert_path_to_posix(value)
                if drive_letter:
                    settings_data[f"{key}_drive"] = drive_letter
            else:
                if drive_letter is None:
                    drive_letter = 'C:\\'
                    print(f"Drive letter for {value} not found, using the default one {drive_letter}")
                value = sanitize.convert_path_to_nt(value, drive_letter)
            return value
        except Exception as e:
            print(f"Error occurred while converting path: {e}")
            raise