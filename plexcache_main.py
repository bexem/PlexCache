# Install dependencies to execute the rest of the script
import plexcache_dependencies
dependencies.install_dependencies(dependencies.get_missing_dependencies())

import argparse, os, time

# Import the other parts of the script
import plexcache_setup, plexcache_settings

start_time = time.time()  # record start time

script_folder = os.path.dirname(os.path.abspath(__file__))
# settings_filename will be overshadowed by the --config "/your/path/settings.yaml" argument, when used.
settings_filename = os.path.join(script_folder, "plexcache_settings.yaml")

def prompt_user_for_boolean(prompt_message, default_value):
    while True:
        user_input = input(prompt_message) or default_value
        if user_input.lower() in ['n', 'no']:
            user_input = False
            return user_input
        elif user_input.lower() in ['y', 'yes']:
            user_input = True
            return user_input
        else:
            print("Invalid choice. Please enter either yes or no")

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

def main():
    global settings_filename

    parser = argparse.ArgumentParser(description="PlexCache help menu:")
    
    parser.add_argument("--settings-file", required=False, default=settings_filename, help="Path to the settings file")

    parser.add_argument("--setup", action="store_true", 
                        help="Run the Setup, it will help you creating a new settings file")
    
    parser.add_argument("--config", type=str, 
                        help="Specify the path to the configuration file")
    
    parser.add_argument("--log", type=str, 
                        help="Specify a log folder to write logs to")
    
    parser.add_argument("--verbose", action="store_true", 
                        help="Increase output verbosity")
    
    parser.add_argument("--quiet", action="store_true", 
                        help="Reduce output verbosity and temporarely disable notifications")

    parser.add_argument("--dryrun", action="store_true", 
                        help="Like verbose but it will NOT move or copy files")

    args = parser.parse_args()

    # Example of using the arguments
    if args.config:
        print(f"Using configuration file: {args.config}")
        settings_filename = args.config

    if args.setup:
        plexcache_setup.initialise(settings_filename)

    # Rest of your main script code goes here
    if os.path.exists(settings_filename):
        print("Loading the settings...")
        plexcache_settings.initialize(settings_filename)
    else:
        print(f"Settings file not found: {settings_filename}")
        if prompt_user_for_boolean('Do you want to run the Setup? [Y/n] ', 'yes'):
            plexcache_setup.initialise(settings_filename)
            plexcache_settings.initialize(settings_filename)
        else:
            exit(f"Exiting...")

    if args.log:
        print(f"Logs will be written to: {args.log}")
        settings.log_folder = args.log

    if args.verbose:
        print("Verbose mode is ON")

    if args.quiet:
        print("Quiet mode is ON")

    if args.dryrun:
        debug = True
        print("Dry running: NO FILE WILL BE MOVED.")
    else:
        debug = False

    print("Initial steps done, now executing rest of the main function...")

    print(f"Settings file: {plexcache_settings_filename}")
    print(f"Logs: {plexcache_settings.log_folder}")
    print(f"Current OS: {plexcache_settings.os_type}")
    print(f"Current script folder: {script_folder}")
    print(f"Current log folder: {plexcache_settings.log_folder}")

    if not settings.mover_ignore_list_file == '':
        print(f"Current mover ignore list file: {plexcache_settings.log_folder}")
    elif settings.mover_ignore_list_file.startswith("plexcache"):
        print(f"Appending list to mover ignore list file: {plexcache_settings.log_folder}")
    else:
        print("You don't have the mover ignore list setup")

if __name__ == "__main__":
    main()

    end_time = time.time()  # record end time
    execution_time_seconds = end_time - start_time  # calculate execution time
    execution_time = convert_time(execution_time_seconds)

    print(f"Main is Done, taken: {execution_time}")


