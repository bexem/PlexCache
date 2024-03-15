- Continue the shares and pools, using the new map variable and implementing it in the main logic to make the script use the respective folder (tv:tvseries) instead of iterating all (tvseries, movies, anime).

- Use plexcache_* as naming scheme.

- Remove any windows related logic, the script needs to focus on unraid/linux.

- Add a way to know why specific media is being moved to either cache or array (maybe use a different variable when fetching and the cleaning? Or use an array for each user...).

- Introduce freespace threshold for watched media.

- If any error occurs, attach a log file in the summary.

- Implement the fixes for the folders.

- Implement duplicate handling.

- Optimize the Unraid checking for duplicate handling.

- Make sure when deleting the duplicate, the total size of the files to move is actually updated.

- Put a setting for the duplicates, some people might want to keep both.

- Remove original permissions and owner text in the logging.

- Set the permissions as settings/setup.

- Update check.

- Docker/Unraid App.

- Introduce freespace threshold for watched media.

- When an active session is detected, copy the currently playing media to the cache (if more than 20% still unplayed and not transcoding).

- Implement integrity/hash checking.

- If any error occurs, attach a log file in the summary.

- Multithread, consider adding more threads.

- Make sure watched movies have priority over watchlist stuff.

- Make the script update itself if a new Sonarr or Radarr quality release renames the file.

- Change "debug" to dry-run (probably no need for debug logging except if specified, maybe switch all the files info to debug? Or add a verbose level for logging).

- Remove empty folders left on the cache drive.

- Use a function to write the log and print on screen so that you can use the --verbose flag to also print on screen instead of just logging.

- Dry run doesn't necessarily activate the verbose mode, optimal for testing success messages.

- The function to write the log and print on screen, useful for the summary message probably.

- Add cache file mover exclusion messages if already not present.

- Implement `recentlyAddedMovies(maxresults=50)`.

- Class `plexapi.video.Movie(server, data, initpath=None, parent=None) year (int)`: Year movie was released.

- Move all files in the folder (trailer/music theme, check Plex website/documentation for all the files used).

- Check for updates.
