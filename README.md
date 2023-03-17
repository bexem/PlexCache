**TLDR:** Move the media currently On Deck/Watchlist on Plex from the array to the cache. 

This Python script reduces energy consumption by minimizing the need to spin up the array/disk(s) when watching recurrent media like TV series. It achieves this by moving the media from the OnDeck library of the main user, all other users, and the main user's watchlist. For TV shows/anime, it also fetches the next specified number of episodes.

The project contains two scripts: a setup script and a main script. The setup script prompts the user to specify the folders where the media is stored and fetches the mapped Plex media paths and will create the settings file, which can also be created/edited manually.
The script was initially developed for Unraid but is compatible with other systems.

# The script can:
- Fetch a specified number of episodes from the "onDeck" for the main user and other specified users, as well as the main user's watchlist.
- Skip fetching onDeck media for specified users.
- Search only the specified libraries.
- Check for free space before moving any file.
- Move watched media present on the cache drive back to the array.
- Move relative subtitles along with the media moved to or from the cache.
- Filter media older than a specified number of days.
- Run in debug mode for testing.
- Use of a log file for easy debugging.
- Exit the script if any active session or skip the currently playing media.
- Find your missing unicorn.

# Disclaimer:

Before you dive in, here's a reality check: this script comes without any warranties, guarantees, or magic powers.

By using this script, you accept that you're responsible for any consequences that may result. The author will not be held liable for data loss, corruption, or any other problems you may encounter. So, it's on you to make sure you have backups and test this script thoroughly before you unleash its awesome power.

Now, go ahead and take script for a spin.

# How to run the setup script:

The instructions below are applicable to the main operating systems:
1) Check Python Installation: 
- First, you need to check whether Python is installed on your system. On Windows, open the Command Prompt or PowerShell, and on macOS or Linux, open the Terminal. 
    Type "python --version" and hit enter. If you see a version number, then Python is already installed (skip step 2), otherwise, you need to download and install Python.
2) Install Python: 
- If Python is not installed, then go to the official Python website[^2] and download the latest version for your operating system. Follow the instructions in the installer to complete the installation.
3) Install the "plexapi" and "requests" modules: 
- Open the Command Prompt or Terminal and type "pip install plexapi requests" and hit enter. This will download and install the "plexapi" and "requests" modules.
4) Run the Python Script: 
- Once you have installed Python and the required modules, you can run the Python script. Navigate to the directory where the script is located, and open the Command Prompt or Terminal. Type "python setup.py" and hit enter. This will execute the Python script.
**Note: In some cases, you may need to use "python3" instead of "python" if you have both Python 2 and 3 installed on your system.**

# How to run the main script:

**Be sure you have the settings file configured accordingly before running the script.**

Note that the **"settings.json"** file is assumed to be located in the same directory, but this can be changed by editing the "settings_filename" variable in the script. 

1) For users of Unraid, the following instructions can be followed to execute the script:

    - A) Install Python directly on Unraid (using NerdTools[^4] plugin) and manually install the required dependencies (plexapi). Then, run the script using cron or the User Scripts plugin[^5]. However, this method is not officially recommended, but I have personally noticed some random authentication errors in chronos.
    
    - B) Execute it on Chronos[^3] (docker container), which can be installed from the Unraid app store:   
            - Allocate an additional path to the default ones and direct it to "/mnt" in both the host and the container. Also, set the container network type: to Host. 
            - Create a new script, configure how to trigger it (preferably using cron), and paste the contents of the plexoncache.py script in the Python script box, change the path of the settings_filename variable accordingly before proceeding.
            - Install the required modules by typing "plexapi" in the Pip requirements box and pressing "Install pip requirements."
            - Save the script and execute it.

2) For every other user, use the instruction of the setup script, the only difference is the "plexapi" module is the only one required.


# Thank you:
To brimur[^1], your script is what helped and inspired me in the first place, **and thank you** to every single one which contributed and even just commented about the project. ❤️


[^1]: [brimur/preCachePlexOnDeckEpiosodes.py](https://gist.github.com/brimur/95277e75ca399d5d52b61e6aa192d1cd)
[^2]: [Python Download](https://wiki.python.org/moin/BeginnersGuide/Download)
[^3]: [Chronos on Github](https://github.com/simse/chronos)
[^4]: [Nerd Tools Plugin official topic on the unraid forum](https://forums.unraid.net/topic/129200-plug-in-nerdtools/)
[^5]: [User Scripts Plugin official topic on the unraid forum](https://forums.unraid.net/topic/48286-plugin-ca-user-scripts/)
