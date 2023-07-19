# PlexCache: Automate Plex Media Management

Automate Plex media management: Efficiently transfer media from the On Deck/Watchlist to the cache, and seamlessly move watched media back to their respective locations.

## Overview

PlexCache efficiently transfers media from the On Deck/Watchlist to the cache and moves watched media back to their respective locations. This Python script reduces energy consumption by minimizing the need to spin up the array/hard drive(s) when watching recurrent media like TV series. It achieves this by moving the media from the OnDeck and watchlist for the main user and/or other users. For TV shows/anime, it also fetches the next specified number of episodes.

## Features

- Fetch a specified number of episodes from the "onDeck" for the main user and other users.
- Skip fetching onDeck media for specified users.
- Fetch a specified number of episodes from the "watchlist" for the main user and other users.
- Skip fetching watchlist media for specified users.
- Search only the specified libraries.
- Check for free space before moving any file.
- Move watched media present on the cache drive back to the array.
- Move respective subtitles along with the media moved to or from the cache.
- Filter media older than a specified number of days.
- Run in debug mode for testing.
- Use of a log file for easy debugging.
- Use caching system to avoid wastful memory usage and cpu cycles.
- Use of multitasking to optimize file transfer time.
- Exit the script if any active session or skip the currently playing media.
- Send Webhook messages according to set log level.
- Find your missing unicorn.

**Work in progress (pre-releases)**

- Use symbolic links if the script is not running on UNRAID. **(UNTESTED)**

## Setup

Please check out our [Wiki section](https://github.com/bexem/PlexCache/wiki) for the step-by-step guide on how to setup PlexCache on your system. 

## Notes

This script should be compatible with other systems, especially Linux-based ones, although I have primarily tested it on Unraid with plex as docker container running on Unraid. Work has been done to improve Windows interoperability.
While I cannot  support every case, it's worth checking the GitHub issues to see if your specific case has already been discussed.
I will still try to help out, but please note that I make no promises in providing assistance for every scenario.
**It is highly advised to use the setup script.**

## Disclaimer

This script comes without any warranties, guarantees, or magic powers. By using this script, you accept that you're responsible for any consequences that may result. The author will not be held liable for data loss, corruption, or any other problems you may encounter. So, it's on you to make sure you have backups and test this script thoroughly before you unleash its awesome power.

## Acknowledgments

I would like to express my sincere gratitude to brimur[^1] for providing the script that served as the foundation and inspiration for this project. I would also like to extend a heartfelt thank you to everyone who contributed and took the time to comment on the project. Your support and involvement mean a lot to me. ❤️

[^1]: [brimur/preCachePlexOnDeckEpiosodes.py](https://gist.github.com/brimur/95277e75ca399d5d52b61e6aa192d1cd)
