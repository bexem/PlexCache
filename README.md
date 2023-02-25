TLDR: Move the media currently On Deck on Plex from the array to the cache (unraid).

This is a Python script designed to reduce energy consumption by minimizing the need to spin up the array/disk(s) when watching recurrent media, such as TV series. The script achieves this by moving the media from the OnDeck library of the main user and all other users, and also fetching the next set number of episodes (if the media is a TV show/anime). The script also moves the media from the main user's watchlist and, for each media, its subtitles to prevent the need to spin up the entire drive for a small amount of data.

The script is specifically designed to work with Unraid, but it can be adapted to work with other systems. 

The script fetches the mapped Plex media paths (tvseries, movies, etc.) and asks the user for the respective folders, where the actual media is stored.
The script also assumes the "settings.json" is in the same directory, but you can change it easily at the begging of the script itself, changing the value of settings_filename = "/directory-you-want/settings.json"

With the settings.json generated or manually modified, here some basic instructions on how to run the script on unraid:
A) Run it on Chronos[^3] (docker container, easily installable from the unraid app store):
* Allocate another path to the default ones, point it at "/mnt" in both the host and the container. 
- Once you are in the Chronos web interface: 
  1. Add a new script
  2. Configure how to trigger (personally using cron) the script; 
  3. Write plexapi in the Pip requirements box;
  4. Save;
  5. Press "Install pip requirements";
  6. Past the content of the plexoncache.py in the Python script box. 
  7. Save. 
  8. Execute (or wait for the script to be triggered); 
  9. Enjoy.

B) Install python directly on Unraid (probably using NerdTools[^4] plugin) but you will need to manually install the two dependency the script requires (plexapi and psutil); and run it by cron (or User Scripts plugin[^5]). I don't advise this method but it works.


Thank you to [brimur/preCachePlexOnDeckEpiosodes.py](https://gist.github.com/brimur/95277e75ca399d5d52b61e6aa192d1cd) Your script is what helped and inspired me.

[^1]: If you want to fetch more episodes, change this variable at the beginning of the script "number_episodes".
[^2]: [Official guide on how to fetch the token.](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)
[^3]: [Chronos on Github](https://github.com/simse/chronos)
[^4]: [Nerd Tools Plugin official topic on the unraid forum](https://forums.unraid.net/topic/129200-plug-in-nerdtools/)
[^5]: [User Scripts Plugin official topic on the unraid forum](https://forums.unraid.net/topic/48286-plugin-ca-user-scripts/)
