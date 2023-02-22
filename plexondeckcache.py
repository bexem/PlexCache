import os
import psutil
import subprocess
from subprocess import check_call
from itertools import chain
from plexapi.server import PlexServer
from plexapi.video import Episode
from datetime import datetime

##################################################################
# Plex URL and TOKEN                                             #
##################################################################
PLEX_URL = 'https://plex.yourdomain.domain'
PLEX_TOKEN = 'tokentokentoken'
plex = PlexServer(PLEX_URL, PLEX_TOKEN)
sessions = plex.sessions()

##################################################################
# Number of episodes                                             #
##################################################################
number_episodes = 5

##################################################################
# Set the Sections we want to evaluate.                          #
##################################################################
valid_sections = [1,2]

##################################################################
# How many days of On Deck do we want to consider?               #
##################################################################
DAYS_TO_MONITOR = 999

##################################################################
# Directories                                                    #
##################################################################
cache_dir = '/mnt/cache/'
plex_source = "/media/"
real_source = "/mnt/user/"

##################################################################
# Do you want to stop the script if session is active            #
# or just skip the active iles?                                  #
# Set it to "no" if you want to exit the script                  #
##################################################################
skip = "yes"

#***************************DEBUG**********************************
# No files will be moved if set to "yes"
debug = "yes"
#******************************************************************

processed_files = []
files = []
files_to_skip = []

if sessions:
    if skip != "yes":
        print('There is an active session. Exiting...')
        exit()

def otherusers(user, number_episodes):
    user_plex = PlexServer(PLEX_URL, user.get_token(plex.machineIdentifier))
    user_files = []
    for video in user_plex.library.onDeck():
        if video.section().key in valid_sections:
            delta = datetime.now() - video.lastViewedAt
            if delta.days <= DAYS_TO_MONITOR:
                if isinstance(video, Episode): #TV Series
                    for media in video.media:
                        for part in media.parts:
                            show = video.grandparentTitle 
                            # Get the library the video belongs to
                            library_section = video.section()
                            # Get the episodes of the show in the library
                            episodes = [e for e in library_section.search(show)[0].episodes()] #Fetches the next 5 episodes
                            next_episodes = []
                            current_season = video.parentIndex
                            user_files.append((part.file))
                            for episode in episodes: 
                                if episode.parentIndex > current_season or (episode.parentIndex == current_season and episode.index > video.index) and len(next_episodes) < number_episodes:
                                    next_episodes.append(episode) 
                                if len(next_episodes) == number_episodes:
                                    break
                            for episode in next_episodes: #Adds the episodes to the list
                                for media in episode.media:
                                    for part in media.parts:
                                        user_files.append((part.file))        
                else: #Movies
                    for media in video.media:
                        for part in media.parts:
                            user_files.append((part.file))
    return user_files or []

def mainuser(number_episodes):
    user_files = []
    for video in plex.library.onDeck():
        # Apply section filter
        if video.section().key in valid_sections:
            delta = datetime.now() - video.lastViewedAt
            if delta.days <= DAYS_TO_MONITOR:
                if isinstance(video, Episode): #TV Series
                    for media in video.media:
                        for part in media.parts:
                            show = video.grandparentTitle 
                            # Get the library the video belongs to
                            library_section = video.section()
                            # Get the episodes of the show in the library
                            episodes = [e for e in library_section.search(show)[0].episodes()] #Fetches the next 5 episodes
                            next_episodes = []
                            current_season = video.parentIndex
                            files.append((part.file))
                            for episode in episodes: 
                                if episode.parentIndex > current_season or (episode.parentIndex == current_season and episode.index > video.index) and len(next_episodes) < number_episodes:
                                    next_episodes.append(episode) 
                                if len(next_episodes) == number_episodes:
                                    break
                            for episode in next_episodes: #Adds the episodes to the list
                                for media in episode.media:
                                    for part in media.parts:
                                        files.append((part.file)) 
                else: #Movies
                    for media in video.media:
                        for part in media.parts:
                            files.append((part.file))
    return user_files or []

files.extend(mainuser(number_episodes)) #Main user

for user in plex.myPlexAccount().users(): #All the other users
    files.extend(otherusers(user, number_episodes))

if sessions:
    for session in sessions:
        # Set the media ID
        media = str(session.source())
        media_id = media[media.find(":") + 1:media.find(":", media.find(":") + 1)]
        # Find the media item with the specified ID
        media_item = plex.fetchItem(int(media_id))
        # Get the title of the media item
        media_title = media_item.title
        # Get the full path of the media item
        media_path = media_item.media[0].parts[0].file
        files_to_skip.append(media_path)

#Search for subtitle files (any file with similar file name but different extension)
processed_files = set()
for count, fileToCache in enumerate(files): 
    if fileToCache in processed_files:
        continue
    processed_files.add(fileToCache)
    directory_path = os.path.dirname(fileToCache)
    if fileToCache in files_to_skip:
        print("Those files are currently used, skipping...")
        print(fileToCache)
        continue
    directory_path = directory_path.replace(plex_source, real_source)
    file_name, file_ext = os.path.splitext(os.path.basename(fileToCache))
    files_in_dir = os.listdir(directory_path)
    subtitle_files = [os.path.join(directory_path, file) for file in files_in_dir if file.startswith(file_name) and file != file_name+file_ext]
    if subtitle_files:
        for subtitle in subtitle_files:
            if subtitle not in files:
                files.append(subtitle)

#Correct all paths locating the file in the unraid array and move the files to the cache drive                
processed_files = set()
for count, fileToCache in enumerate(files): 
    if fileToCache in processed_files:
        continue
    if fileToCache in files_to_skip:
        continue
    media_file_path = os.path.dirname(fileToCache)
    user_path = media_file_path.replace(plex_source, real_source)
    cache_path = user_path.replace(real_source, cache_dir)
    user_file_name = user_path + "/" + os.path.basename(fileToCache)
    cache_file_name = cache_path + "/" + os.path.basename(fileToCache)
    if not os.path.exists(cache_path): #If the path that will end up containing the media file does not exist, this lines will create it
        os.makedirs(cache_path)
    if not os.path.isfile(cache_file_name): 
        disk_file_name = user_file_name.replace("/mnt/user/", "/mnt/user0/") #Thanks to dada051 suggestion
        if debug == "yes":
            print("****Debug is ON, no file will be moved****")
            print("Moving", disk_file_name, "--> TO -->", cache_path)
            print("Cache file path:", cache_path)
            print("User file name:", user_file_name)
            print("Disk file name:", disk_file_name)
            print("Cache file name:", cache_file_name)
            print("********************************")
        else:
            print("_____________************_____________")
            print("File not in the cache drive, beginning the moving process")
            move = f"mv -v \"{disk_file_name}\" \"{cache_path}\""
            os.system(move)
            print("______________________________________")

print("Script executed.")