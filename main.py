import os
import eyed3
import urllib3
import config as const
from classes import *

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
eyed3.log.setLevel("ERROR")


def perform_download(track_id: int, folder_path: str, filename: str) -> None:
    print("FLAC is being downloaded")
    downloader = SongDownload(track_id, folder_path, filename)
    downloader.with_progress_bar()

def song_handling() -> Action:
    while True:
        print("Does this song match your request?")
        print("    1. Download")
        print("    2. Skip")
        print("    3. Exit")
        print("    4. Quit")
        user_input = str(input("Enter your choice: "))
        match user_input:
            case "1":
                return Action.DOWNLOAD
            case "2":
                return Action.SKIP
            case "3":
                return Action.EXIT
            case "4":
                return Action.QUIT
            case _:
                print("Invalid input. Please make an appropriate choice.")

def create_folder(folder_name: str, path: str) -> str:
    folder_path = os.path.join(path, folder_name)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(":~>  Created folder", folder_path)
        return folder_path


def move_to(filepath: str, folder_name: str) -> None:
    if os.path.exists(filepath):
        path = create_folder(folder_name, const.SOURCE_FOLDER)

        filename = os.path.basename(filepath)
        new_filepath = os.path.join(path, filename)
        shutil.move(filepath, new_filepath)
        print(f":~>  Moved {filename} to {path}")
    else:
        print(":~> Source file does not exist")

def process_songs(filepath: str, folder_path: str) -> None:
    song = SongHandler(filepath)
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

        if StringAnalyzer.has_exception(song.title):
            print("An exception! Heading to the next one...\n")
            continue

        if File.exists(song.filename, folder_path):
            print("File already exists. Skipping...\n")
            move_to(filepath, "done")
            continue

        if (StringAnalyzer.has_cyrillic(name_local) or StringAnalyzer.has_cyrillic(name_json)):
            match song_handling():
                case Action.DOWNLOAD:
                    perform_download(song.track_id, folder_path, song.filename)
                    move_to(filepath, "done")
                    break
                case Action.SKIP:
                    print("Skipping this song\n")
                    continue
                case Action.EXIT:
                    print("Exited successfully")
                    break
                case Action.QUIT:
                    print("Program has been successfully terminated")
                    exit()
        elif StringAnalyzer.is_similar(name_local, name_json):
            perform_download(song.track_id, folder_path, song.filename)      
            move_to(filepath, "done")
            break
        else:
            print("Songs do not match\n")
            continue

def main():
    dir_name = os.path.dirname(const.SOURCE_FOLDER)
    folder_path = create_folder("FLAC", dir_name)
    source_files = os.listdir(const.SOURCE_FOLDER)

    for file in source_files:
        if file.endswith(f".{const.SOURCE_EXTENSION}"):
            mp3_filepath = os.path.join(const.SOURCE_FOLDER, file)
            try:
                process_songs(mp3_filepath, folder_path)
            except Exception as e:
                print(f"An error occurred while processing {mp3_filepath}: {str(e)}")

    print(":~> Congratulations! All songs have been processed")

if __name__ == "__main__":
    main()
