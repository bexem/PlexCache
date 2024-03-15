import logging, subprocess

script_folder = IMPORT FROM MAIN "/mnt/user/system/plexcache/" # Folder path for the PlexCache script storing the settings, watchlist & watched cache files
logs_folder = script_folder # Change this if you want your logs in a different folder
log_level = "" # Set the desired logging level for webhook notifications. Defaults to INFO when left empty. (Options: debug, info, warning, error, critical)
max_log_files = 5 # Maximum number of log files to keep
log_file_pattern = "plexcache_log_*.log"
summary_messages = []
files_moved = False
# Define a new level called SUMMARY that is equivalent to INFO level
SUMMARY = logging.WARNING + 1
logging.addLevelName(SUMMARY, 'SUMMARY')

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
