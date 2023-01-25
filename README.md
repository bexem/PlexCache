TLDR: Move the media currently On Deck on Plex from the array to the cache (unraid).

This is a script in Python made to help me saving some energy by reducing the need to spin up the array/disk(s) when watching recurrent media, such as a TV series.
The script moves not only the media (Movies and Shows) that is "On Deck" but also the next 5[^1] episodes of each TV Series (and/or Anime) to the cache (SSD) drive, which is faster and more power-efficient than the regular disk. 
Additionally, it will also move the subtitles to prevent the need to spin up the entire drive for a small amount of data. 
This script is designed to work with Unraid, but can be adapted for use with other systems. 

While I am still new to Python and the code may not be the most efficient, it has been working seamlessly for several days (and counting).

To use the script there are different ways but DO NOT forget to change the plex url and token[^2] variables accordingly. 

A) Run it on Chronos[^3] (docker container, easily installable from the unraid app store):
* Allocate another path to the default ones, point it at "/mnt" in both the host and the container. 
- Once you are in the Chronos web interface: 
  1. Add a new script
  2. Configure how to trigger (personally using cron) the script; 
  3. List the two requirements (plexapi and psutil) in the Pip requirements box;
  4. Save;
  5. Press "Install pip requirements";
  6. Past the content of the plexondeckcache.py in the Python script box. 
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
