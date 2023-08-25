import os, json, logging, glob, socket, platform, shutil, ntpath, posixpath, re, requests, subprocess, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from plexapi.server import PlexServer
from plexapi.video import Episode
from plexapi.video import Movie
from plexapi.myplex import MyPlexAccount
from plexapi.exceptions import NotFound
from plexapi.exceptions import BadRequest

print("*** PlexCache ***")

script_folder = "/mnt/user/system/plexcache/" # Folder path for the PlexCache script storing the settings, watchlist & watched cache files
logs_folder = script_folder # Change this if you want your logs in a different folder
log_level = "" # Set the desired logging level for webhook notifications. Defaults to INFO when left empty. (Options: debug, info, warning, error, critical)
max_log_files = 5 # Maximum number of log files to keep

notification = "system" # "Unraid" or "Webhook", or "Both"; "System" instead will automatically switch to unraid if the scripts detects running on unraid
# Set the desired logging level for the notifications. 
unraid_level = "summary"  
webhook_level = "" 
# Leave empty for notifications only on ERROR. (Options: debug, info, warning, error, critical)
# You can also set it to "summary" and it will notify on error but also give you a short summary at the end of each run. 

webhook_url = ""  # Your webhook URL, leave empty for no notifications.
webhook_headers = {} # Leave empty for Discord, otherwise edit it accordingly. (Slack example: "Content-Type": "application/json" "Authorization": "Bearer YOUR_SLACK_TOKEN" })

settings_filename = os.path.join(script_folder, "plexcache_settings.json")
watchlist_cache_file = Path(os.path.join(script_folder, "plexcache_watchlist_cache.json"))
watched_cache_file = Path(os.path.join(script_folder, "plexcache_watched_cache.json"))

RETRY_LIMIT = 3
DELAY = 15  # in seconds

log_file_pattern = "plexcache_log_*.log"
summary_messages = []
files_moved = False
# Define a new level called SUMMARY that is equivalent to INFO level
SUMMARY = logging.WARNING + 1
logging.addLevelName(SUMMARY, 'SUMMARY')

start_time = time.time()  # record start time

class UnraidHandler(logging.Handler):
    SUMMARY = SUMMARY
    def __init__(self):
        super().__init__()
        self.notify_cmd_base = "/usr/local/emhttp/webGui/scripts/notify"
        if not os.path.isfile(self.notify_cmd_base) or not os.access(self.notify_cmd_base, os.X_OK):
            logging.warning(f"{self.notify_cmd_base} does not exist or is not executable. Unraid notifications will not be sent.")
            print(f"{self.notify_cmd_base} does not exist or is not executable. Unraid notifications will not be sent.")
            self.notify_cmd_base = None

    def emit(self, record):
        if self.notify_cmd_base:
            if record.levelno == SUMMARY:
                self.send_summary_unraid_notification(record)
            else: 
                self.send_unraid_notification(record)

    def send_summary_unraid_notification(self, record):
        icon = 'normal'
        notify_cmd = f'{self.notify_cmd_base} -e "PlexCache" -s "Summary" -d "{record.msg}" -i "{icon}"'
        subprocess.call(notify_cmd, shell=True)

    def send_unraid_notification(self, record):
        # Map logging levels to icons
        level_to_icon = {
            'WARNING': 'warning',
            'ERROR': 'alert',
            'INFO': 'normal',
            'DEBUG': 'normal',
            'CRITICAL': 'alert'
        }

        icon = level_to_icon.get(record.levelname, 'normal')  # default to 'normal' if levelname is not found in the dictionary

        # Prepare the command with necessary arguments
        notify_cmd = f'{self.notify_cmd_base} -e "PlexCache" -s "{record.levelname}" -d "{record.msg}" -i "{icon}"'

        # Execute the command
        subprocess.call(notify_cmd, shell=True)

class WebhookHandler(logging.Handler):
    SUMMARY = SUMMARY
    def __init__(self, webhook_url):
        super().__init__()
        self.webhook_url = webhook_url

    def emit(self, record):
        if record.levelno == SUMMARY:
            self.send_summary_webhook_message(record)
        else:
            self.send_webhook_message(record)

    def send_summary_webhook_message(self, record):
        summary = "Plex Cache Summary:\n" + record.msg
        payload = {
            "content": summary
        }
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(self.webhook_url, data=json.dumps(payload), headers=headers)
        if not response.status_code == 204:
            print(f"Failed to send summary message. Error code: {response.status_code}")

    def send_webhook_message(self, record):
        payload = {
            "content": record.msg
        }
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(self.webhook_url, data=json.dumps(payload), headers=headers)
        if not response.status_code == 204:
            print(f"Failed to send message. Error code: {response.status_code}")

def check_and_create_folder(folder):
    # Check if the folder doesn't already exist
    if not os.path.exists(folder):
        try:
            # Create the folder with necessary parent directories
            os.makedirs(folder, exist_ok=True)
        except PermissionError:
            # Exit the program if the folder is not writable
            exit(f"{folder} not writable, please fix the variable accordingly.")
    
# Check and create the script folder
check_and_create_folder(script_folder)

# Check and create the logs folder if it's different from the script folder
if logs_folder != script_folder:
    check_and_create_folder(logs_folder)

current_time = datetime.now().strftime("%Y%m%d_%H%M")  # Get the current time and format it as YYYYMMDD_HHMM
log_file = os.path.join(logs_folder, f"{log_file_pattern[:-5]}{current_time}.log")  # Create a filename based on the current time
latest_log_file = os.path.join(logs_folder, f"{log_file_pattern[:-5]}latest.log")  # Create a filename for the latest log
logger = logging.getLogger()  # Get the root logger
if log_level:
    log_level = log_level.lower()
    if log_level == "debug":
        logger.setLevel(logging.DEBUG)
    elif log_level == "info":
        logger.setLevel(logging.INFO)
    elif log_level == "warning":
        logger.setLevel(logging.WARNING)
    elif log_level == "error":
        logger.setLevel(logging.ERROR)
    elif log_level == "critical":
        logger.setLevel(logging.CRITICAL)
    else:
        print(f"Invalid webhook_level: {log_level}. Using default level: ERROR")
        logger.setLevel(logging.INFO)

# Configure the rotating file handler
handler = RotatingFileHandler(log_file, maxBytes=20*1024*1024, backupCount=max_log_files)  # Create a rotating file handler
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))  # Set the log message format
logger.addHandler(handler)  # Add the file handler to the logger

# Create or update the symbolic link to the latest log file
if os.path.exists(latest_log_file):
    os.remove(latest_log_file)  # Remove the existing link if it exists

os.symlink(log_file, latest_log_file)  # Create a new link to the latest log file
def clean_old_log_files(logs_folder, log_file_pattern, max_log_files):
    # Find all log files that match the specified pattern in the logs folder
    existing_log_files = glob.glob(os.path.join(logs_folder, log_file_pattern))
    # Sort the log files based on their last modification time
    existing_log_files.sort(key=os.path.getmtime)
    # Remove log files until the number of remaining log files is within the desired limit
    while len(existing_log_files) > max_log_files:
        # Remove the oldest log file from the list and delete it from the filesystem
        os.remove(existing_log_files.pop(0))

# Call the function to clean old log files
clean_old_log_files(logs_folder, log_file_pattern, max_log_files)

def check_os():
    # Check the operating system
    os_name = platform.system()

    # Define information about different operating systems
    os_info = {
        'Linux': {'path': "/mnt/user0/", 'msg': 'Script is currently running on Linux.'},
        'Darwin': {'path': None, 'msg': 'Script is currently running on macOS (untested).'},
        'Windows': {'path': None, 'msg': 'Script is currently running on Windows.'}
    }

    # Check if the operating system is recognized
    if os_name not in os_info:
        logging.critical('This is an unrecognized system. Exiting...')
        exit("Error: Unrecognized system.")

    # Determine if the system is Linux
    is_linux = True if os_name != 'Windows' else False

    # Check if the system is Unraid (specific to Linux)
    is_unraid = os.path.exists(os_info[os_name]['path']) if os_info[os_name]['path'] else False

    # Modify the information message if the system is Unraid
    if is_unraid:
        os_info[os_name]['msg'] += ' The script is also running on Unraid.'

    # Check if script is running inside a Docker container
    is_docker = os.path.exists('/.dockerenv')
    if is_docker:
        os_info[os_name]['msg'] += ' The script is running inside a Docker container.'
        
    # Log the information about the operating system
    logging.info(os_info[os_name]['msg'])

    return is_unraid, is_linux, is_docker

# Call the check_os() function and store the returned values
unraid, os_linux, is_docker = check_os()

# Create and add the webhook handler to the logger
if notification.lower() == "unraid" or notification.lower() == "system":
    if unraid and not is_docker:
        notification = "unraid"
    else:
        notification = ""
if notification.lower() == "both":
    if unraid and is_docker:
        notification = "webhook"

if notification.lower() == "both" or notification.lower() == "unraid":
    unraid_handler = UnraidHandler()
    if unraid_level:
        unraid_level = unraid_level.lower()
        if unraid_level == "debug":
            unraid_handler.setLevel(logging.DEBUG)
        elif unraid_level == "info":
            unraid_handler.setLevel(logging.INFO)
        elif unraid_level == "warning":
            unraid_handler.setLevel(logging.WARNING)
        elif unraid_level == "error":
            unraid_handler.setLevel(logging.ERROR)
        elif unraid_level == "critical":
            unraid_handler.setLevel(logging.CRITICAL)
        elif unraid_level.lower() == "summary":
            unraid_handler.setLevel(SUMMARY)
        else:
            print(f"Invalid unraid_level: {unraid_level}. Using default level: ERROR")
            unraid_handler.setLevel(logging.ERROR)
    else:
        unraid_handler.setLevel(logging.ERROR)
    logger.addHandler(unraid_handler)  # Add the unraid handler to the logger

# Create and add the webhook handler to the logger
if notification.lower() == "both" or notification.lower() == "webhook":
    if webhook_url:
        webhook_handler = WebhookHandler(webhook_url)
        if webhook_level:
            webhook_level = webhook_level.lower()
            if webhook_level == "debug":
                webhook_handler.setLevel(logging.DEBUG)
            elif webhook_level == "info":
                webhook_handler.setLevel(logging.INFO)
            elif webhook_level == "warning":
                webhook_handler.setLevel(logging.WARNING)
            elif webhook_level == "error":
                webhook_handler.setLevel(logging.ERROR)
            elif webhook_level == "critical":
                webhook_handler.setLevel(logging.CRITICAL)
            elif webhook_level.lower() == "summary":
                webhook_handler.setLevel(SUMMARY)
            else:
                print(f"Invalid webhook_level: {webhook_level}. Using default level: ERROR")
                webhook_handler.setLevel(logging.ERROR)
        else:
            webhook_handler.setLevel(logging.ERROR)
        logger.addHandler(webhook_handler)  # Add the webhook handler to the logger

logging.info("*** PlexCache ***")

# Remove "/" or "\" from a given path
def remove_trailing_slashes(value):
    try:
        # Check if the value is a string
        if isinstance(value, str):
            # Check if the value contains a ':' and if the value with trailing slashes removed is empty
            if ':' in value and value.rstrip('/\\') == '':
                # Return the value with trailing slashes removed and add a backslash at the end
                return value.rstrip('/') + "\\"
            else:
                # Return the value with trailing slashes removed
                return value.rstrip('/\\')
        # Return the value if it is not a string
        return value
    except Exception as e:
        # Log an error if an exception occurs and raise it
        logging.error(f"Error occurred while removing trailing slashes: {e}")
        raise

# Add "/" or "\" to a given path
def add_trailing_slashes(value):
    try:
        # Check if the value does not contain a ':', indicating it's a Windows-style path
        if ':' not in value:
            # Add a leading "/" if the value does not start with it
            if not value.startswith("/"):
                value = "/" + value
            # Add a trailing "/" if the value does not end with it
            if not value.endswith("/"):
                value = value + "/"
        # Return the modified value
        return value
    except Exception as e:
        # Log an error if an exception occurs and raise it
        logging.error(f"Error occurred while adding trailing slashes: {e}")
        raise

# Removed all "/" "\" from a given path
def remove_all_slashes(value_list):
    try:
        # Iterate over each value in the list and remove leading and trailing slashes
        return [value.strip('/\\') for value in value_list]
    except Exception as e:
        logging.error(f"Error occurred while removing all slashes: {e}")
        raise

# Convert the given path to a windows compatible path
def convert_path_to_nt(value, drive_letter):
    try:
        if value.startswith('/'):
            # Add the drive letter to the beginning of the path
            value = drive_letter.rstrip(':\\') + ':' + value
        # Replace forward slashes with backslashes
        value = value.replace(posixpath.sep, ntpath.sep)
        # Normalize the path to remove redundant separators and references to parent directories
        return ntpath.normpath(value)
    except Exception as e:
        logging.error(f"Error occurred while converting path to Windows compatible: {e}")
        raise

# Convert the given path to a linux/posix compatible path
# If a drive letter is present, it will save it in the settings file.
def convert_path_to_posix(value):
    try:
        # Save the drive letter if exists
        drive_letter = re.search(r'^[A-Za-z]:', value)  # Check for a drive letter at the beginning of the path
        if drive_letter:
            drive_letter = drive_letter.group() + '\\'  # Extract the drive letter and add a backslash
        else:
            drive_letter = None
        # Remove drive letter if exists
        value = re.sub(r'^[A-Za-z]:', '', value)  # Remove the drive letter from the path
        # Replace backslashes with slashes
        value = value.replace(ntpath.sep, posixpath.sep)  # Replace backslashes with forward slashes
        return posixpath.normpath(value), drive_letter  # Normalize the path and return it along with the drive letter
    except Exception as e:
        logging.error(f"Error occurred while converting path to Posix compatible: {e}")
        raise

# Convert path accordingly to the operating system the script is running
# It assigns drive_letter = 'C:\\' if no drive was ever given/saved
def convert_path(value, key, settings_data, drive_letter=None):
    try:
        # Normalize paths converting backslashes to slashes
        if os_linux:  # Check if the operating system is Linux
            value, drive_letter = convert_path_to_posix(value)  # Convert path to POSIX format
            if drive_letter:
                settings_data[f"{key}_drive"] = drive_letter  # Save the drive letter in the settings data
        else:
            if drive_letter is None:
                if debug:
                    print(f"Drive letter for {value} not found, using the default one 'C:\\'")
                logging.warning(f"Drive letter for {value} not found, using the default one 'C:\\'")
                drive_letter = 'C:\\'  # Set the default drive letter to 'C:\'
            value = convert_path_to_nt(value, drive_letter)  # Convert path to Windows format

        return value
    except Exception as e:
        logging.error(f"Error occurred while converting path: {e}")
        raise

# Check if the settings file exists
if os.path.exists(settings_filename):
    # Loading the settings file
    with open(settings_filename, 'r') as f:
        settings_data = json.load(f)
else:
    logging.critical("Settings file not found, please fix the variable accordingly.")
    exit("Settings file not found, please fix the variable accordingly.")

# Reads the settings file and all the settings
try:
    # Extracting the 'firststart' flag from the settings data
    firststart = settings_data.get('firststart')
    if firststart:
        debug = True
        print("First start is set to true, setting debug mode temporarily to true.")
        logging.warning("First start is set to true, setting debug mode temporarily to true.")
        del settings_data['firststart']
    else:
        debug = settings_data.get('debug')
        if firststart is not None:
            del settings_data['firststart']

    # Extracting various settings from the settings data
    PLEX_URL = settings_data['PLEX_URL']
    PLEX_TOKEN = settings_data['PLEX_TOKEN']
    number_episodes = settings_data['number_episodes']
    valid_sections = settings_data['valid_sections']
    days_to_monitor = settings_data['days_to_monitor']
    users_toggle = settings_data['users_toggle']

    # Checking and assigning 'skip_ondeck' and 'skip_watchlist' values
    skip_ondeck = settings_data.get('skip_ondeck')
    skip_watchlist = settings_data.get('skip_watchlist')

    skip_users = settings_data.get('skip_users')
    if skip_users is not None:
        skip_ondeck = settings_data.get('skip_ondeck', skip_users)
        skip_watchlist = settings_data.get('skip_watchlist', skip_users)
        del settings_data['skip_users']
    else:
        skip_ondeck = settings_data.get('skip_ondeck', [])
        skip_watchlist = settings_data.get('skip_watchlist', [])

    watchlist_toggle = settings_data['watchlist_toggle']
    watchlist_episodes = settings_data['watchlist_episodes']
    watchlist_cache_expiry = settings_data['watchlist_cache_expiry']

    watched_cache_expiry = settings_data['watched_cache_expiry']
    watched_move = settings_data['watched_move']

    plex_source_drive = settings_data.get('plex_source_drive')
    plex_source = add_trailing_slashes(settings_data['plex_source'])

    cache_dir_drive = settings_data.get('cache_dir_drive')
    cache_dir = remove_trailing_slashes(settings_data['cache_dir'])
    cache_dir = convert_path(cache_dir, 'cache_dir', settings_data, cache_dir_drive)
    cache_dir = add_trailing_slashes(settings_data['cache_dir'])

    real_source_drive = settings_data.get('real_source_drive')
    real_source = remove_trailing_slashes(settings_data['real_source'])
    real_source = convert_path(real_source, 'real_source', settings_data, real_source_drive)
    real_source = add_trailing_slashes(settings_data['real_source'])

    nas_library_folders = remove_all_slashes(settings_data['nas_library_folders'])
    plex_library_folders = remove_all_slashes(settings_data['plex_library_folders'])

    exit_if_active_session = settings_data.get('exit_if_active_session')
    if exit_if_active_session is None:
        exit_if_active_session = not settings_data.get('skip')
        del settings_data['skip']

    max_concurrent_moves_array = settings_data['max_concurrent_moves_array']
    max_concurrent_moves_cache = settings_data['max_concurrent_moves_cache']

    deprecated_unraid = settings_data.get('unraid')
    if deprecated_unraid is not None:
        del settings_data['unraid']
except KeyError as e:
    # Error handling for missing key in settings file
    logging.critical(f"Error: {e} not found in settings file, please re-run the setup or manually edit the settings file.")
    exit(f"Error: {e} not found in settings file, please re-run the setup or manually edit the settings file.")

try:
    # Save the updated settings data back to the file
    with open(settings_filename, 'w') as f:
        settings_data['cache_dir'] = cache_dir
        settings_data['real_source'] = real_source
        settings_data['plex_source'] = plex_source
        settings_data['nas_library_folders'] = nas_library_folders
        settings_data['plex_library_folders'] = plex_library_folders
        settings_data['skip_ondeck'] = skip_ondeck
        settings_data['skip_watchlist'] = skip_watchlist
        settings_data['exit_if_active_session'] = exit_if_active_session
        json.dump(settings_data, f, indent=4)
except Exception as e:
    logging.error(f"Error occurred while saving settings data: {e}")
    raise

# Initialising necessary arrays
processed_files = []
files_to_skip = []
media_to = []
media_to_cache = []
media_to_array = []
move_commands = []

# Connect to the Plex server
try:
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
except Exception as e:
    logging.critical(f"Error connecting to the Plex server: {e}")
    exit(f"Error connecting to the Plex server: {e}")

# Check if any active session
sessions = plex.sessions()  # Get the list of active sessions
if sessions:  # Check if there are any active sessions
    if exit_if_active_session:  # Check if the 'exit_if_active_session' boolean is set to true
        logging.warning('There is an active session. Exiting...')
        exit('There is an active session. Exiting...')
    else:
        for session in sessions:  # Iterate over each active session
            try:
                media = str(session.source())  # Get the source of the session
                media_id = media[media.find(":") + 1:media.find(":", media.find(":") + 1)]  # Extract the media ID from the source
                media_item = plex.fetchItem(int(media_id))  # Fetch the media item using the media ID
                media_title = media_item.title  # Get the title of the media item
                media_type = media_item.type  # Get the media type (e.g., show, movie)
                if media_type == "episode":  # Check if the media type is an episode
                    show_title = media_item.grandparentTitle  # Get the title of the show
                    print(f"Active session detected, skipping: {show_title} - {media_title}")  # Print a message indicating the active session with show and episode titles
                    logging.warning(f"Active session detected, skipping: {show_title} - {media_title}")  # Log a warning message about the active session with show and episode titles
                elif media_type == "movie":  # Check if the media type is a movie
                    print(f"Active session detected, skipping: {media_title}")  # Print a message indicating the active session with the movie title
                    logging.warning(f"Active session detected, skipping: {media_title}")  # Log a warning message about the active session with the movie title
                media_path = media_item.media[0].parts[0].file  # Get the file path of the media item
                logging.info(f"Skipping: {media_path}")
                files_to_skip.append(media_path)  # Add the file path to the list of files to skip
            except Exception as e:
                logging.error(f"Error occurred while processing session: {session} - {e}")  # Log an error message if an exception occurs while processing the session
else:
    logging.info('No active sessions found. Proceeding...')  # Log an info message indicating no active sessions were found, and proceed with the code execution

# Check if debug mode is active
if debug:
    print("Debug mode is active, NO FILE WILL BE MOVED.")
    logging.getLogger().setLevel(logging.DEBUG)
    logging.warning("Debug mode is active, NO FILE WILL BE MOVED.")
    logging.info(f"Real source: {real_source}")
    logging.info(f"Cache dir: {cache_dir}")
    logging.info(f"Plex source: {plex_source}")
    logging.info(f"NAS folders: ({nas_library_folders}")
    logging.info(f"Plex folders: {plex_library_folders}")
else:
    logging.getLogger().setLevel(logging.INFO)

# Main function to fetch onDeck media files
def fetch_on_deck_media_main(plex, valid_sections, days_to_monitor, number_episodes, users_toggle, skip_ondeck):
    try:
        users_to_fetch = [None]  # Start with main user (None)

        if users_toggle:
            users_to_fetch += plex.myPlexAccount().users()
            # Filter out the users present in skip_ondeck
            users_to_fetch = [user for user in users_to_fetch if (user is None) or (user.get_token(plex.machineIdentifier) not in skip_ondeck)]

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_on_deck_media, plex, valid_sections, days_to_monitor, number_episodes, user) for user in users_to_fetch}
            for future in as_completed(futures):
                try:
                    yield from future.result()
                except Exception as e:
                    print(f"An error occurred in fetch_on_deck_media: {e}")
                    logging.error(f"An error occurred while fetching onDeck media for a user: {e}")

    except Exception as e:
        print(f"An error occurred in fetch_on_deck_media: {e}")
        logging.error(f"An error occurred in fetch_on_deck_media_main: {e}")

def fetch_on_deck_media(plex, valid_sections, days_to_monitor, number_episodes, user=None):
    try:
        username, plex = get_plex_instance(plex, user)  # Get the username and Plex instance
        if not plex:  # Check if Plex instance is available
            return []  # Return an empty list

        print(f"Fetching {username}'s onDeck media...")  # Print a message indicating that onDeck media is being fetched
        logging.info(f"Fetching {username}'s onDeck media...")  # Log the message indicating that onDeck media is being fetched
        
        on_deck_files = []  # Initialize an empty list to store onDeck files
        # Get all sections available for the user
        available_sections = [section.key for section in plex.library.sections()]

        # Intersect available_sections and valid_sections
        filtered_sections = list(set(available_sections) & set(valid_sections))

        for video in plex.library.onDeck():  # Iterate through the onDeck videos in the Plex library
            section_key = video.section().key  # Get the section key of the video
            if not filtered_sections or section_key in filtered_sections:  # Check if filtered_sections is empty or the video belongs to a valid section
                delta = datetime.now() - video.lastViewedAt  # Calculate the time difference between now and the last viewed time of the video
                if delta.days <= days_to_monitor:  # Check if the video was viewed within the specified number of days
                    if isinstance(video, Episode):  # Check if the video is an episode
                        process_episode_ondeck(video, number_episodes, on_deck_files)  # Process the episode and add it to the onDeck files list
                    elif isinstance(video, Movie):  # Check if the video is a movie
                        process_movie_ondeck(video, on_deck_files)  # Process the movie and add it to the onDeck files list

        return on_deck_files  # Return the list of onDeck files

    except Exception as e:  # Handle any exceptions that occur
        print(f"An error occurred while fetching onDeck media: {e}")  # Print an error message indicating the exception
        logging.error(f"An error occurred while fetching onDeck media: {e}")  # Log an error message indicating the exception
        return []  # Return an empty list

# Function to fetch the Plex instance
def get_plex_instance(plex, user):
    if user:
        username = user.title  # Get the username
        try:
            return username, PlexServer(PLEX_URL, user.get_token(plex.machineIdentifier))  # Return username and PlexServer instance with user token
        except Exception as e:
            print(f"Error: Failed to Fetch {username} onDeck media. Error: {e}")  # Print error message if failed to fetch onDeck media for the user
            logging.error(f"Error: Failed to Fetch {username} onDeck media. Error: {e}")  # Log the error
            return None, None
    else:
        username = plex.myPlexAccount().title  # Get the username from the Plex account
        return username, PlexServer(PLEX_URL, PLEX_TOKEN)  # Return username and PlexServer instance with account token

# Function to process the onDeck media files
def process_episode_ondeck(video, number_episodes, on_deck_files):
    for media in video.media:
        on_deck_files.extend(part.file for part in media.parts)  # Add file paths of media parts to onDeck files list
    show = video.grandparentTitle  # Get the title of the show
    library_section = video.section()  # Get the library section of the video
    episodes = list(library_section.search(show)[0].episodes())  # Search the library section for episodes of the show
    current_season = video.parentIndex  # Get the index of the current season
    next_episodes = get_next_episodes(episodes, current_season, video.index, number_episodes)  # Get the next episodes based on the current episode and season
    for episode in next_episodes:
        for media in episode.media:
            on_deck_files.extend(part.file for part in media.parts)  # Add file paths of media parts of the next episodes to onDeck files list
            for part in media.parts:
                logging.info(f"OnDeck found: {(part.file)}")  # Log the file path of the onDeck media part

# Function to process the onDeck movies files
def process_movie_ondeck(video, on_deck_files):
    for media in video.media:
        on_deck_files.extend(part.file for part in media.parts)  # Add file paths of media parts to onDeck files list
        for part in media.parts:
            logging.info(f"OnDeck found: {(part.file)}")  # Log the file path of the onDeck media part

# Function to get the next episodes
def get_next_episodes(episodes, current_season, current_episode_index, number_episodes):
    next_episodes = []
    for episode in episodes:
        if (episode.parentIndex > current_season or (episode.parentIndex == current_season and episode.index > current_episode_index)) and len(next_episodes) < number_episodes:
            next_episodes.append(episode)  # Add the episode to the next_episodes list if it comes after the current episode
        if len(next_episodes) == number_episodes:
            break  # Stop iterating if the desired number of next episodes is reached
    return next_episodes  # Return the list of next episodes

# Function to search for a file in the Plex server
def search_plex(plex, title):
    results = plex.search(title)
    return results[0] if len(results) > 0 else None

def fetch_watchlist_media(plex, valid_sections, watchlist_episodes, users_toggle, skip_watchlist):

    def get_watchlist(token, user=None, retries=0):
        # Retrieve the watchlist for the specified user's token.
        account = MyPlexAccount(token=token)
        try:
            if user:
                account = account.switchHomeUser(f'{user.title}')
            return account.watchlist(filter='released')
        except (BadRequest, NotFound) as e:
            if "429" in str(e) and retries < RETRY_LIMIT:  # Rate limit exceeded
                logging.warning(f"Rate limit exceeded. Retrying {retries + 1}/{RETRY_LIMIT}. Sleeping for {DELAY} seconds...")
                time.sleep(DELAY)
                return get_watchlist(token, user, retries + 1)
            elif isinstance(e, NotFound):
                logging.warning(f"Failed to switch to user {user.title if user else 'Unknown'}. Skipping...")
                return []
            else:
                raise e


    def process_show(file, watchlist_episodes):
        #Process episodes of a TV show file up to a specified number.
        episodes = file.episodes()
        count = 0
        for episode in episodes[:watchlist_episodes]:
            if len(episode.media) > 0 and len(episode.media[0].parts) > 0:
                count += 1
                if not episode.isPlayed:
                    yield episode.media[0].parts[0].file

    def process_movie(file):
        #Process a movie file.
        if not file.isPlayed:
            yield file.media[0].parts[0].file

    def fetch_user_watchlist(user):
        current_username = plex.myPlexAccount().title if user is None else user.title
        available_sections = [section.key for section in plex.library.sections()]
        filtered_sections = list(set(available_sections) & set(valid_sections))

        if user and user.get_token(plex.machineIdentifier) in skip_watchlist:
            logging.info(f"Skipping {current_username}'s watchlist media...")
            return []

        logging.info(f"Fetching {current_username}'s watchlist media...")
        try:
            watchlist = get_watchlist(PLEX_TOKEN, user)
            results = []

            for item in watchlist:
                file = search_plex(plex, item.title)
                if file and (not filtered_sections or (file.librarySectionID in filtered_sections)):
                    if file.TYPE == 'show':
                        results.extend(process_show(file, watchlist_episodes))
                    else:
                        results.extend(process_movie(file))
            return results
        except Exception as e:
            logging.error(f"Error fetching watchlist for {current_username}: {str(e)}")
            return []

    users_to_fetch = [None]  # Start with main user (None)
    if users_toggle:
        users_to_fetch += plex.myPlexAccount().users()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_user_watchlist, user) for user in users_to_fetch}
        for future in as_completed(futures):
            retries = 0
            while retries < RETRY_LIMIT:
                try:
                    yield from future.result()
                    break
                except Exception as e:
                    if "429" in str(e):  # rate limit error
                        logging.warning(f"Rate limit exceeded. Retrying in {DELAY} seconds...")
                        time.sleep(DELAY)
                        retries += 1
                    else:
                        logging.error(f"Error fetching watchlist media: {str(e)}")
                        break

# Function to fetch watched media files
def get_watched_media(plex, valid_sections, last_updated, user=None):
    def fetch_user_watched_media(plex_instance, username):
        try:
            print(f"Fetching {username}'s watched media...")
            logging.info(f"Fetching {username}'s watched media...")

            # Get all sections available for the user
            all_sections = [section.key for section in plex_instance.library.sections()]

            # Check if valid_sections is specified. If not, consider all available sections as valid.
            if 'valid_sections' in globals() and valid_sections:
                available_sections = list(set(all_sections) & set(valid_sections))
            else:
                available_sections = all_sections

            # Filter sections the user has access to
            user_accessible_sections = [section for section in available_sections if section in all_sections]

            for section_key in user_accessible_sections:
                section = plex_instance.library.sectionByID(section_key)  # Get the section object using its key

                # Search for videos in the section
                for video in section.search(unwatched=False):
                    # Skip if the video was last viewed before the last_updated timestamp
                    if video.lastViewedAt and last_updated and video.lastViewedAt < datetime.fromtimestamp(last_updated):
                        continue

                    # Process the video and yield the file path
                    yield from process_video(video)
        except Exception as e:
            print(f"An error occurred in fetch_user_watched_media: {e}")
            logging.error(f"An error occurred in fetch_user_watched_media: {e}")

    def process_video(video):
        if video.TYPE == 'show':
            # Iterate through each episode of a show video
            for episode in video.episodes():
                yield from process_episode(episode)
        else:
            # Get the file path of the video
            file_path = video.media[0].parts[0].file
            yield file_path

    def process_episode(episode):
        # Iterate through each media and part of an episode
        for media in episode.media:
            for part in media.parts:
                if episode.isPlayed:
                    # Get the file path of the played episode
                    file_path = part.file
                    yield file_path

    # Create a ThreadPoolExecutor
    with ThreadPoolExecutor() as executor:
        main_username = plex.myPlexAccount().title
        
        # Start a new task for the main user
        futures = [executor.submit(fetch_user_watched_media, plex, main_username)]
        
        if users_toggle:
            for user in plex.myPlexAccount().users():
                username = user.title
                user_token = user.get_token(plex.machineIdentifier)
                user_plex = PlexServer(PLEX_URL, user_token)

                # Start a new task for each other user
                futures.append(executor.submit(fetch_user_watched_media, user_plex, username))
        
        # As each task completes, yield the results
        for future in as_completed(futures):
            try:
                yield from future.result()
            except Exception as e:
                print(f"An error occurred in get_watched_media: {e}")
                logging.error(f"An error occurred in get_watched_media: {e}")

# Function to load watched media from cache
def load_media_from_cache(cache_file):
    if cache_file.exists():
        with cache_file.open('r') as f:
            try:
                data = json.load(f)
                if isinstance(data, dict):
                    return set(data.get('media', [])), data.get('timestamp')
                elif isinstance(data, list):
                    # cache file contains just a list of media, without timestamp
                    return set(data), None
            except json.JSONDecodeError:
                # Clear the file and return an empty set
                with cache_file.open('w') as f:
                    f.write(json.dumps({'media': [], 'timestamp': None}))
                return set(), None
    return set(), None

# Modify the files paths from the paths given by plex to link actual files on the running system
def modify_file_paths(files, plex_source, real_source, plex_library_folders, nas_library_folders):
    # Print and log a message indicating that file paths are being edited
    print("Editing file paths...")
    logging.info("Editing file paths...")

    # If no files are provided, return an empty list
    if files is None:
        return []

    # Filter the files based on those that start with the plex_source path
    files = [file_path for file_path in files if file_path.startswith(plex_source)]

    # Iterate over each file path and modify it accordingly
    for i, file_path in enumerate(files):
        # Log the original file path
        logging.info(f"Original path: {file_path}")

        # Replace the plex_source with the real_source in the file path
        file_path = file_path.replace(plex_source, real_source, 1) # Replace the plex_source with the real_source, thanks to /u/planesrfun

        # Determine which library folder is in the file path
        for j, folder in enumerate(plex_library_folders):
            if folder in file_path:
                # Replace the plex library folder with the corresponding NAS library folder
                file_path = file_path.replace(folder, nas_library_folders[j])
                break

        # Update the modified file path in the files list
        files[i] = file_path

        # Log the edited file path
        logging.info(f"Edited path: {file_path}")

    # Return the modified file paths or an empty list
    return files or []

def get_media_subtitles(media_files, files_to_skip=None, subtitle_extensions=[".srt", ".vtt", ".sbv", ".sub", ".idx"]):
    print("Fetching subtitles...") 
    logging.info("Fetching subtitles...")
    
    files_to_skip = set() if files_to_skip is None else set(files_to_skip)
    processed_files = set()
    all_media_files = media_files.copy()
    
    for file in media_files:
        if file in files_to_skip or file in processed_files:
            continue
        processed_files.add(file)
        
        directory_path = os.path.dirname(file)
        if os.path.exists(directory_path): 
            subtitle_files = find_subtitle_files(directory_path, file, subtitle_extensions)  
            all_media_files.extend(subtitle_files)  
            for subtitle_file in subtitle_files:  
                logging.info(f"Subtitle found: {subtitle_file}")  
    
    return all_media_files or []

def find_subtitle_files(directory_path, file, subtitle_extensions):
    file_name, _ = os.path.splitext(os.path.basename(file))

    try:
        subtitle_files = [
            entry.path
            for entry in os.scandir(directory_path)
            if entry.is_file() and entry.name.startswith(file_name) and entry.name != file and entry.name.endswith(tuple(subtitle_extensions))
        ]
    except PermissionError as e:
        logging.error(f"Cannot access directory {directory_path}. Permission denied. Error: {e}")
        subtitle_files = []
    except OSError as e:
        logging.error(f"Cannot access directory {directory_path}. Error: {e}")
        subtitle_files = []

    return subtitle_files or []

# Function to convert size to readable format
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
    
    # Return the size and corresponding unit
    return size, unit

# Function to check for free space
def get_free_space(dir):
    if not os.path.exists(dir):
        logging.error(f"Invalid path, unable to calculate free space for: {dir}.")
        return 0
    stat = os.statvfs(dir)  # Get the file system statistics for the specified directory
    free_space_bytes = stat.f_bfree * stat.f_frsize  # Calculate the free space in bytes
    return convert_bytes_to_readable_size(free_space_bytes)  # Convert the free space to a human-readable format

# Function to calculate size of the files contained in the given array
def get_total_size_of_files(files):
    total_size_bytes = sum(os.path.getsize(file) for file in files)  # Calculate the total size of the files in bytes
    return convert_bytes_to_readable_size(total_size_bytes)  # Convert the total size to a human-readable format

# Function to filter the files, based on the destination
def filter_files(files, destination, real_source, cache_dir, media_to_cache, files_to_skip):
    # Log a message indicating that media files are being filtered for the specified destination
    logging.info(f"Filtering media files {destination}...")

    if not len(files_to_skip) == 0:
        files_to_skip = modify_file_paths(files_to_skip, plex_source, real_source, plex_library_folders, nas_library_folders)

    try:
        # If media_to_cache is not provided, initialize it as an empty list
        if media_to_cache is None:
            media_to_cache = []

        # Set to keep track of processed files
        processed_files = set()

        # List to store media files based on the destination
        media_to = []

        if files is None or len(files) == 0:
            return []

        # Iterate over each file
        for file in files:
            # If the file has already been processed, skip to the next file
            if file in processed_files or file in files_to_skip:
                continue

            # Add the file to the set of processed files
            processed_files.add(file)

            # Get the cache file name using the file's path, real_source, and cache_dir
            cache_file_name = get_cache_paths(file, real_source, cache_dir)[1]

            # Check the destination and decide whether to add the file to media_to list
            if destination == 'array' and should_add_to_array(file, cache_file_name, media_to_cache):
                media_to.append(file)
                logging.info(f"Adding file to array: {file}")
            elif destination == 'cache' and should_add_to_cache(cache_file_name):
                media_to.append(file)
                logging.info(f"Adding file to cache: {file}")

        # Return the filtered media files for the destination or an empty list
        return media_to or []

    except Exception as e:
        # Log an error if an exception occurs during the filtering process
        logging.error(f"Error occurred while filtering media files: {str(e)}")
        return []

# Check if the file is already present in the array
def should_add_to_array(file, cache_file_name, media_to_cache):
    # If the file is in media_to_cache or the cache file doesn't exist, return False
    if file in media_to_cache or not os.path.isfile(cache_file_name):
        if file in media_to_cache:
            logging.info(f"File '{file}' was not added to the array because it's already scheduled to be moved to the cache (found in 'media_to_cache'). Skipped for now.")
        return False
    return True  # Otherwise, the file should be added to the array

# Check if the file is already present in the cache
def should_add_to_cache(cache_file_name):
    return not os.path.isfile(cache_file_name)  # Return True if the cache_file_name is not a file (i.e., it does not exist in the cache), False otherwise

# Check for free space before executing moving process
def check_free_space_and_move_files(media_files, destination, real_source, cache_dir, unraid, debug):
    global files_moved, summary_messages
    media_files_filtered = filter_files(media_files, destination, real_source, cache_dir, media_to_cache, files_to_skip)  # Filter the media files based on certain criteria
    total_size, total_size_unit = get_total_size_of_files(media_files_filtered)  # Get the total size of the filtered media files
    if total_size > 0:  # If there are media files to be moved
        logging.info(f"Total size of media files to be moved to {destination}: {total_size:.2f} {total_size_unit}")  # Log the total size of media files
        print(f"Total size of media files to be moved to {destination}: {total_size:.2f} {total_size_unit}")  # Print the total size of media files
        if files_moved:
            summary_messages.append(f"Total size of media files moved to {destination}: {total_size:.2f} {total_size_unit}")
        else:
            summary_messages = [f"Total size of media files moved to {destination}: {total_size:.2f} {total_size_unit}"]
            files_moved = True
        free_space, free_space_unit = get_free_space(destination == 'cache' and cache_dir or real_source)  # Get the free space on the destination drive
        print(f"Free space on the {destination}: {free_space:.2f} {free_space_unit}")  # Print the free space on the destination drive
        logging.info(f"Free space on the {destination}: {free_space:.2f} {free_space_unit}")  # Log the free space on the destination drive
        if total_size * (1024 ** {'KB': 0, 'MB': 1, 'GB': 2, 'TB': 3}[total_size_unit]) > free_space * (1024 ** {'KB': 0, 'MB': 1, 'GB': 2, 'TB': 3}[free_space_unit]):
            # If the total size of media files is greater than the free space on the destination drive
            if not debug:
                exit(f"Not enough space on {destination} drive.")
                logging.critical(f"Not enough space on {destination} drive..")
            else:
                print(f"Not enough space on {destination} drive.")
                logging.error(f"Not enough space on {destination} drive..")
        logging.info(f"Moving media to {destination}...")  # Log the start of the media moving process
        print(f"Moving media to {destination}...")  # Print the start of the media moving process
        move_media_files(media_files_filtered, real_source, cache_dir, unraid, debug, destination, max_concurrent_moves_array, max_concurrent_moves_cache)  # Move the media files to the destination
    else:
        print(f"Nothing to move to {destination}")  # If there are no media files to move, print a message
        logging.info(f"Nothing to move to {destination}")  # If there are no media files to move, log a message
        if not files_moved:
            summary_messages = ["There were no files to move to any destination."]
        else:
            summary_messages.append("")

# Function to check if given path exists, is a directory and the script has writing permissions
def check_path_exists(path):
    # Check if the path exists
    if not os.path.exists(path):
        logging.critical(f"Path {path} does not exist.")
        exit(f"Path {path} does not exist.")
    
    # Check if the path is a directory
    if not os.path.isdir(path):
        logging.critical(f"Path {path} is not a directory.")
        exit(f"Path {path} is not a directory.")
    
    # Check if the script has writing permissions for the path
    if not os.access(path, os.W_OK):
        logging.critical(f"Path {path} is not writable.")
        exit(f"Path {path} is not writable.")

# Function to move files, it executes the given move command   
def move_file(move_cmd):
    try:
        # Move the file using the given move command
        shutil.move(*move_cmd)
        logging.info(f"Moved file from {move_cmd[0]} to {move_cmd[1]}")
        return 0
    except Exception as e:
        # Log an error if there's an exception while moving the file
        logging.error(f"Error moving file: {str(e)}")
        return 1

# Created the move command that gets executed from the function above
def move_media_files(files, real_source, cache_dir, unraid, debug, destination, max_concurrent_moves_array, max_concurrent_moves_cache):
    # Print and log the destination directory
    print(f"Moving media files to {destination}...")
    logging.info(f"Moving media files to {destination}...")
    
    # Initialize the set of files to skip and the set of processed files
    processed_files = set()
    move_commands = []

    # Iterate over each file to move
    for file_to_move in files:
        # Skip the file if it has already been processed
        if file_to_move in processed_files:
            continue
        
        # Add the file to the set of processed files
        processed_files.add(file_to_move)
        
        # Get the user path, cache path, cache file name, and user file name
        user_path, cache_path, cache_file_name, user_file_name = get_paths(file_to_move, real_source, cache_dir, unraid)
        
        # Get the move command for the current file
        move = get_move_command(destination, cache_file_name, user_path, user_file_name, cache_path)
        
        # If a move command is obtained, append it to the list of move commands
        if move is not None:
            move_commands.append(move)
    
    # Execute the move commands
    execute_move_commands(debug, move_commands, max_concurrent_moves_array, max_concurrent_moves_cache, destination)

# Function to get the paths of the user and cache directories
def get_paths(file_to_move, real_source, cache_dir, unraid):
    # Get the user path
    user_path = os.path.dirname(file_to_move)
    
    # Get the relative path from the real source directory
    relative_path = os.path.relpath(user_path, real_source)
    
    # Get the cache path by joining the cache directory with the relative path
    cache_path = os.path.join(cache_dir, relative_path)
    
    # Get the cache file name by joining the cache path with the base name of the file to move
    cache_file_name = os.path.join(cache_path, os.path.basename(file_to_move))
    
    # Modify the user path if unraid is True
    if unraid:
        user_path = user_path.replace("/mnt/user/", "/mnt/user0/", 1)

    # Get the user file name by joining the user path with the base name of the file to move
    user_file_name = os.path.join(user_path, os.path.basename(file_to_move))
    
    return user_path, cache_path, cache_file_name, user_file_name

# Locates the given file in the cache
def get_cache_paths(file, real_source, cache_dir):
    # Get the cache path by replacing the real source directory with the cache directory
    cache_path = os.path.dirname(file).replace(real_source, cache_dir, 1)
    
    # Get the cache file name by joining the cache path with the base name of the file
    cache_file_name = os.path.join(cache_path, os.path.basename(file))
    
    return cache_path, cache_file_name

# Function to get the move command for the given file
def get_move_command(destination, cache_file_name, user_path, user_file_name, cache_path):
    move = None
    if destination == 'array':
        if not os.path.exists(user_path):  # Check if the user path doesn't exist
            os.makedirs(user_path)  # Create the user path directory
        if os.path.isfile(cache_file_name):  # Check if the cache file exists
            move = (cache_file_name, user_path)  # Set the move command to move the cache file to the user path
    if destination == 'cache':
        if not os.path.exists(cache_path):  # Check if the cache path doesn't exist
            os.makedirs(cache_path)  # Create the cache path directory
        if not os.path.isfile(cache_file_name):  # Check if the cache file doesn't exist
            move = (user_file_name, cache_path)  # Set the move command to move the user file to the cache path
    return move

# Function to execute the given move commands
def execute_move_commands(debug, move_commands, max_concurrent_moves_array, max_concurrent_moves_cache, destination):
    if debug:
        for move_cmd in move_commands:
            print(move_cmd)  # Print the move command
            logging.info(move_cmd)  # Log the move command
    else:
        max_concurrent_moves = max_concurrent_moves_array if destination == 'array' else max_concurrent_moves_cache
        with ThreadPoolExecutor(max_workers=max_concurrent_moves) as executor:
            results = executor.map(move_file, move_commands)  # Move the files using multiple threads
            errors = [result for result in results if result != 0]  # Collect any non-zero error codes
            print(f"Finished moving files with {len(errors)} errors.")  # Print the number of errors encountered during file moves
            logging.info(f"Finished moving files with {len(errors)} errors.")

def convert_time(execution_time_seconds):
    # Calculate days, hours, minutes, and seconds
    days, remainder = divmod(execution_time_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Create a human-readable string for the result
    result_str = ""
    if days > 0:
        result_str += f"{int(days)} day{'s' if days > 1 else ''}, "
    if hours > 0:
        result_str += f"{int(hours)} hour{'s' if hours > 1 else ''}, "
    if minutes > 0:
        result_str += f"{int(minutes)} minute{'s' if minutes > 1 else ''}, "
    if seconds > 0:
        result_str += f"{int(seconds)} second{'s' if seconds > 1 else ''}"

    return result_str.rstrip(", ")

# Function to check if internet is available
def is_connected():
    try:
        socket.gethostbyname("www.google.com")
        return True
    except socket.error:
        return False

# Checks if the paths exists and are accessible
for path in [real_source, cache_dir]:
    check_path_exists(path)

# Fetch OnDeck Media
media_to_cache.extend(fetch_on_deck_media_main(plex, valid_sections, days_to_monitor, number_episodes, users_toggle, skip_ondeck))

# Edit file paths for the above fetched media
media_to_cache = modify_file_paths(media_to_cache, plex_source, real_source, plex_library_folders, nas_library_folders)

# Fetches subtitles for the above fetched media
media_to_cache.extend(get_media_subtitles(media_to_cache, files_to_skip=files_to_skip))

skip_cache = "--skip-cache" in sys.argv

# Watchlist logic:
# It will check if there is internet connection as plexapi requires to use a method which uses their server rather than plex
# If internet is not available or the cache is within the expiry date, it will use the cached file.
if watchlist_toggle:
    try:
        # Load previously watched media from cache and get the last update time
        watchlist_media_set, last_updated = load_media_from_cache(watchlist_cache_file)
        current_watchlist_set = set()

        if is_connected():
            # To fetch the watchlist media, internet connection is required due to a plexapi limitation

            # Check if the cache file doesn't exist, debug mode is enabled, or cache has expired
            if skip_cache or (not watchlist_cache_file.exists()) or (debug) or (datetime.now() - datetime.fromtimestamp(watchlist_cache_file.stat().st_mtime) > timedelta(hours=watchlist_cache_expiry)):
                print("Fetching watchlist media...")
                logging.info("Fetching watchlist media...")

                # Fetch the watchlist media from Plex server
                fetched_watchlist = fetch_watchlist_media(plex, valid_sections, watchlist_episodes, users_toggle=users_toggle, skip_watchlist=skip_watchlist)

                # Add new media paths to the cache
                for file_path in fetched_watchlist:
                    current_watchlist_set.add(file_path)
                    if file_path not in watchlist_media_set:
                        media_to_cache.append(file_path)

                # Remove media that no longer exists in the watchlist
                watchlist_media_set.intersection_update(current_watchlist_set)

                # Add new media to the watchlist media set
                watchlist_media_set.update(media_to_cache)

                # Modify file paths and add subtitles
                media_to_cache = modify_file_paths(media_to_cache, plex_source, real_source, plex_library_folders, nas_library_folders)
                media_to_cache.extend(get_media_subtitles(media_to_cache, files_to_skip=files_to_skip))

                # Update the cache file with the updated watchlist media set
                with watchlist_cache_file.open('w') as f:
                    json.dump({'media': list(media_to_cache), 'timestamp': datetime.now().timestamp()}, f)
            else:
                # Load watchlist media from cache
                print("Loading watchlist media from cache...")
                logging.info("Loading watchlist media from cache...")
                media_to_cache.extend(watchlist_media_set)
        else:
            # Handle no internet connection scenario
            print("Unable to connect to the internet, skipping fetching new watchlist media due to plexapi limitation.")
            logging.warning("Unable to connect to the internet, skipping fetching new watchlist media due to plexapi limitation.")
            
            # Load watchlist media from cache
            print("Loading watchlist media from cache...")
            logging.info("Loading watchlist media from cache...")
            media_to_cache.extend(watchlist_media_set)
    except Exception as e:
        # Handle any exceptions that occur while processing the watchlist
        print("An error occurred while processing the watchlist.")
        logging.error("An error occurred while processing the watchlist: %s", str(e))

# Watched media logic
if watched_move:
    try:
        # Load watched media from cache
        watched_media_set, last_updated = load_media_from_cache(watched_cache_file)
        current_media_set = set()

        # Check if cache file doesn't exist or debug mode is enabled
        if skip_cache or not watched_cache_file.exists() or debug or (datetime.now() - datetime.fromtimestamp(watched_cache_file.stat().st_mtime) > timedelta(hours=watched_cache_expiry)):
            print("Fetching watched media...")
            logging.info("Fetching watched media...")

            # Get watched media from Plex server
            fetched_media = get_watched_media(plex, valid_sections, last_updated, users_toggle)
            
            # Add fetched media to the current media set
            for file_path in fetched_media:
                current_media_set.add(file_path)

                # Check if file is not already in the watched media set
                if file_path not in watched_media_set:
                    media_to_array.append(file_path)

            # Add new media to the watched media set
            watched_media_set.update(media_to_array)
            
            # Modify file paths and add subtitles
            media_to_array = modify_file_paths(media_to_array, plex_source, real_source, plex_library_folders, nas_library_folders)
            media_to_array.extend(get_media_subtitles(media_to_array, files_to_skip))

            # Save updated watched media set to cache file
            with watched_cache_file.open('w') as f:
                json.dump({'media': list(media_to_array), 'timestamp': datetime.now().timestamp()}, f)

        else:
            print("Loading watched media from cache...")
            logging.info("Loading watched media from cache...")
            # Add watched media from cache to the media array
            media_to_array.extend(watched_media_set)

    except Exception as e:
        # Handle any exceptions that occur while processing the watched media
        print("An error occurred while processing the watched media.")
        logging.error("An error occurred while processing the watched media: %s", str(e))

    try:
        # Check free space and move files
        check_free_space_and_move_files(media_to_array, 'array', real_source, cache_dir, unraid, debug)
    except Exception as e:
        if not debug:
            logging.critical(f"Error checking free space and moving media files to the cache: {str(e)}")
            exit(f"Error: {str(e)}")
        else:
            logging.error(f"Error checking free space and moving media files to the cache: {str(e)}")
            print(f"Error: {str(e)}")

# Moving the files to the cache drive
try:
    check_free_space_and_move_files(media_to_cache, 'cache', real_source, cache_dir, unraid, debug)
except Exception as e:
    if not debug:
        logging.critical(f"Error checking free space and moving media files to the cache: {str(e)}")
        exit(f"Error: {str(e)}")
    else:
        logging.error(f"Error checking free space and moving media files to the cache: {str(e)}")
        print(f"Error: {str(e)}")

end_time = time.time()  # record end time
execution_time_seconds = end_time - start_time  # calculate execution time
execution_time = convert_time(execution_time_seconds)

summary_messages.append(f"The script took approximately {execution_time} to execute.")
summary_message = '  '.join(summary_messages)

logger.log(SUMMARY, summary_message)

print(f"Execution time of the script: {execution_time}")
logging.info(f"Execution time of the script: {execution_time}")

print("Thank you for using bexem's script: \nhttps://github.com/bexem/PlexCache")
logging.info("Thank you for using bexem's script: https://github.com/bexem/PlexCache")
logging.info("Also special thanks to: - /u/teshiburu2020 - /u/planesrfun - /u/trevski13 - /u/extrobe - /u/dsaunier-sunlight")
logging.info("*** The End ***")
logging.shutdown()
print("*** The End ***")