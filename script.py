import os
import eyed3
import urllib3
import config as const
from classes import *


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
eyed3.log.setLevel("ERROR")


def check_and_rename(filepath: str, ext: str) -> None:
    if const.RENAME_SOURCE_FILES:
        file = FileHandler(filepath)
        file.extension_to(ext)
        print("Source file has been renamed")

def perform_download(track_id: int, folder_path: str, filename: str) -> None:
    print("FLAC is being downloaded")
    downloader = Downloader(track_id, folder_path, filename)
    downloader.with_progress_bar()



def song_handling() -> Action:
    while True:
        print("Does this song match your request?")
        print("    1. Download")
        print("    2. Skip")
        print("    3. Exit")
        print("    4. Quit")
        user_input = str(input("Enter your choice: "))
        if user_input == '1':
            return Action.download
        elif user_input == '2':
            return Action.skip
        elif user_input == '3':
            return Action.exit
        elif user_input == '4':
            return Action.quit
        else:
            print("Invalid input. Please enter '1' or '2' or '3'.")

def process_and_handle_songs(source_file_path: str, flac_folder_path: str) -> None:
    song = SongHandler(source_file_path)
    artist_local, title_local = song.extract()
    songs = song.request()
    name_local = f"{artist_local} - {title_local}"

    if not songs:
        print("Could not find", name_local)
        return
    
    for item in songs:
        song.set_info(item)
        print("    Found:", song.filename)
        name_json = f"{song.artist} - {song.title}"

        if Analyzer.has_exception(song.title):
            print("An exception! Heading to the next one...\n")
            continue

        if File.exists(song.filename, flac_folder_path):
            print("File already exists. Skipping...\n")
            check_and_rename(source_file_path, "mp3f")
            continue

        if (Analyzer.has_cyrillic(name_local) or Analyzer.has_cyrillic(name_json)):
            song_action = song_handling()
            
            if song_action == Action.download:
                perform_download(song.track_id, flac_folder_path, song.filename)                
                check_and_rename(source_file_path, "mp3f")
                break
            elif song_action == Action.skip:
                print("Skipping this song\n")
                continue
            elif song_action == Action.exit:
                print("Exited successfully")
                break
            elif song_action == Action.quit:
                print("Program has been successfully terminated")
                exit()
            else:
                raise ValueError("Error occurred") 
            
        else:
            if Analyzer.is_similar(name_local, name_json):
                perform_download(song.track_id, flac_folder_path, song.filename)      
                check_and_rename(source_file_path, "mp3f")
            else:
                print("Songs do not match\n")

def main():
    source_files = os.listdir(const.SOURCE_FOLDER)
    
    for file in source_files:
        if file.endswith("." + const.SOURCE_EXTENSION):
            mp3_filepath = os.path.join(const.SOURCE_FOLDER, file)
            try:
                process_and_handle_songs(mp3_filepath, const.FLAC_FOLDER)
            except Exception as e:
                error_message = f"An error occurred while processing {mp3_filepath}: {str(e)}"
                print(error_message)
             
if __name__ == "__main__":
    main()
