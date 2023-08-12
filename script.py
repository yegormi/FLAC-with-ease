import json    # JSON Management
import os      # For renaming and placing files
import re      # RegEx - extracting year from given string
import shutil  # For downloading file
from enum import Enum           # Create a custom enum
from typing import List, Tuple  # Type hints

import eyed3     # For reading ID3 tags from mp3 files
import requests  # For making an HTTP request
import urllib3   # To supress unsecure HTTP requests
from fuzzywuzzy import fuzz  # For fuzzy matching
from tqdm.auto import tqdm   # For progress bar


class Action(Enum):
    download = 1
    skip = 2
    exit = 3

'''
BASIC PROCESS:

1. Reading metadata from MP3 files (artist, title)
2. Making a JSON request using artist and title
3. Extracting specific variable from JSON content
4. Make a download request, if there is a response, download it
4. Renaming downloaded file
5. Moving downloaded file to destination folder
'''

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
eyed3.log.setLevel("ERROR")

# DO NOT CHANGE IT! CONSTANTS
SIMILARITY_VALUE = 90
SOURCE_EXTENSION = "mp3"
SEARCH_URL       = "https://slavart.gamesdrive.net/api/search"
DOWNLOAD_URL     = "https://slavart-api.gamesdrive.net/api/download/track"
EXCLUDE_ITEMS    = ["Instrumental", "Karaoke"]
KEYWORDS_TO_DELETE_AFTER = ["feat", "(", ",", "&"]
# DO NOT CHANGE IT! CONSTANTS

DEBUG               = True
DEBUG_COMPLEX       = False
LOOK_FOR_ORIGINAL   = True
RENAME_SOURCE_FILES = True
SOURCE_FOLDER       = "/Users/yegormyropoltsev/Desktop/mp3"
FLAC_FOLDER         = "/Users/yegormyropoltsev/Desktop/flac"


def check_and_remove_after_keyword(input_string: str) -> str:
    """
    Check if any of the KEYWORDS_TO_DELETE_AFTER is present in the input_string.
    If a keyword is found, split the input_string at the keyword and return the first part.
    If no keyword is found, return the original input_string.
    
    Args:
        input_string (str): The string to check for keywords.
        
    Returns:
        str: The input_string with any content after the keyword removed, or the original input_string.
    """
    for keyword in KEYWORDS_TO_DELETE_AFTER:
        if keyword in input_string:
            result_string = input_string.split(keyword)[0]
            return result_string
    return input_string

def has_cyrillic(text: str) -> bool:
    """
    Check if the given text contains Cyrillic characters.

    Args:
        text (str): The text to be checked.

    Returns:
        bool: True if the text contains Cyrillic characters, False otherwise.
    """
    return bool(re.search('[а-яА-Я]', text))

def rename_file(file_path: str, new_extension: str) -> None:
    """
    Change the file extension of a given file path.

    Args:
        file_path (str): The path of the file to be modified.
        new_extension (str): The new extension to be applied to the file.

    Returns:
        None
    """
    base_path = os.path.splitext(file_path)[0]
    new_file_path = f"{base_path}.{new_extension}"
    os.rename(file_path, new_file_path)

def get_artist_and_title(SOURCE_FOLDER_file: str) -> Tuple[str, str]:
    """
    Extracts the artist and title information from an MP3 file.

    Args:
        SOURCE_FOLDER_file (str): The path to the MP3 file.

    Returns:
        tuple: A tuple containing the artist and title extracted from the MP3 file. If the MP3 file does not have tag information, returns (None, None).
    """
    audiofile = eyed3.load(SOURCE_FOLDER_file)
    
    if audiofile.tag:
        if DEBUG:
            print(f"\nExtracted: {audiofile.tag.artist} - {audiofile.tag.title}")
        
        if LOOK_FOR_ORIGINAL:
            artist = check_and_remove_after_keyword(audiofile.tag.artist)
            title = check_and_remove_after_keyword(audiofile.tag.title)
            print(f"  Cleaned: {artist} - {title}")
        else:
            artist = audiofile.tag.artist
            title = audiofile.tag.title
        
        return artist, title
    
    return None, None


def get_json(artist: str, title: str) -> List[dict]:
    """
    Retrieves a JSON response from the specified API endpoint by making a GET request with the provided artist and title parameters.

    Parameters:
        artist (str): The name of the artist.
        title (str): The title of the song.
    
    Returns:
        list: A list of track items from the JSON response, or None if there was an error parsing the JSON.
    """
    query = f"{artist} {title}".replace(" ", "%20")
    url = f"{SEARCH_URL}?q={query}"
    response = requests.get(url)
    try:
        json_data = response.json()
        if DEBUG_COMPLEX:
            print(f"Parsed JSON \"{artist} - {title}\"")
        return json_data['tracks']['items']
    except json.decoder.JSONDecodeError as e:
        print("Error parsing JSON response:", e)
        return None


def parse_json(data: dict, key: str):
    """
    Parses the specified JSON object and returns the value of the specified key.

    Parameters:
        data (dict): The JSON object to parse.
        key (str): The name of the key to retrieve from the JSON object.

    Returns:
        The value of the specified key from the JSON object.
    """
    if DEBUG_COMPLEX:
        print(f"Parsed {key} \"{data[key]}\"")
    return data[key]

def parse_year(text):
    """
    Parse the year from the given text.

    Parameters:
        text (str): The text to search for a year.

    Returns:
        str: The parsed year as an integer if found, or an empty string if not found.
    """
    match = re.search(r'\b\d{4}\b', text)
    return match.group() if match else ""

def generate_url(track_id: int) -> str:
    """
    Generates a URL for downloading a track based on the given track ID.

    Parameters:
        track_id (int): The ID of the track to be downloaded.

    Returns:
        str: The URL for downloading the track.
    """
    url = f"{DOWNLOAD_URL}?id={track_id}"
    return url


def download(track_id: int) -> requests.Response:
    """
    Downloads a track given its ID.

    Parameters:
        track_id (int): The ID of the track to download.

    Returns:
        requests.Response: The response object containing the downloaded track.
    """
    if DEBUG:
        print("Sent request to download id=" + str(track_id))

    try:
        url = generate_url(track_id)
        response = requests.get(url, stream=True, verify=False)

        if DEBUG:
            print("Response:", response.status_code)
        return response
    
    except Exception as e:
        print("An error occurred:", str(e))
        # You can add additional error handling or logging here

    return None


def download_file_with_progress_bar(track_id: str, destination: str, filename: str) -> None:
    """
    Download a file from a given URL and display a progress bar.
    
    Args:
        track_id (str): The ID of the track to download.
        destination (str): The destination directory to save the downloaded file.
        filename (str): The name of the downloaded file.
    """
    # Get the URL for the track
    url = generate_url(track_id)
    
    # Send a GET request to the URL and stream the response
    with requests.get(url, stream=True, verify=False) as response:
        # Get the total length of the file
        total_length = int(response.headers.get("Content-Length"))
        
        # Wrap the response in a tqdm downloaded content
        with tqdm.wrapattr(response.raw, "read", total=total_length, desc="") as downloaded:
            # Create the file path
            file_path = os.path.join(destination, filename)
            
            # Open the file in binary write mode
            with open(file_path, 'wb') as file:
                # Copy the contents of the downloaded content to the file
                shutil.copyfileobj(downloaded, file)
                
                # Print a newline character to separate the progress bar from other output
                print("\n")

def is_word_present(input_string: str, word_dict: List[str]) -> bool:
    """
    Check if any word from the word dictionary is present in the input string.

    Args:
        input_string (str): The input string to search for words.
        word_dict (List[str]): The list of words to search for in the input string.

    Returns:
        bool: True if any word from word_dict is found in the input_string, False otherwise.
    """
    return any(word in input_string for word in word_dict)

def generate_filename(data):
    """
    Generate a filename for a FLAC audio file based on the given data.

    Parameters:
        data (dict): The data used to generate the filename. It should contain the following keys:
            - 'performer' (str): The name of the artist.
            - 'title' (str): The title of the audio file.
            - 'maximum_bit_depth' (int): The maximum bit depth of the audio file.
            - 'maximum_sampling_rate' (float): The maximum sampling rate of the audio file.
            - 'copyright' (str): The copyright information.

    Returns:
        str: The generated filename for the FLAC audio file.
    """
    artist        = parse_json(parse_json(data, "performer"), "name")
    title         = parse_json(data, "title")
    bit_depth     = parse_json(data, "maximum_bit_depth")
    sampling_rate = parse_json(data, "maximum_sampling_rate")
    copyright     = parse_json(data, "copyright")
    year          = parse_year(copyright)
    filename      = f"{artist} - {title} ({year}) [FLAC] [{bit_depth}B - {sampling_rate}kHz].flac"
    filename      = filename.replace("/", "-")
    
    return filename


def check_for_existence(source_file_path, flac_folder_path, flac_filename):
    flac_file_path = os.path.join(flac_folder_path, flac_filename)
    if os.path.exists(flac_file_path):
        print("File already exists. Skipping...\n")
        check_and_rename(source_file_path, "mp3f")

def check_for_exceptions(title):
    is_exception = is_word_present(title, EXCLUDE_ITEMS)
    if is_exception:
        print("An exception! Heading to the next one...\n")
        return True
    return False

def song_handling():
    while True:
        print("Does this song match your request?")
        print("    1. Download")
        print("    2. Skip")
        print("    3. Exit")
        user_input = str(input("Enter your choice: "))
        if user_input == '1':
            return Action.download
        elif user_input == '2':
            return Action.skip
        elif user_input == '3':
            return Action.exit
        else:
            print("Invalid input. Please enter '1' or '2'.")


def is_similar(string1: str, string2: str) -> bool:
    similarity_ratio = fuzz.token_set_ratio(string1, string2)
    print("Similarity:", similarity_ratio)
    return similarity_ratio >= SIMILARITY_VALUE

def check_and_rename(filepath: str, ext: str) -> None:
    if RENAME_SOURCE_FILES:
        rename_file(filepath, ext)
        print("Source file has been renamed")

def perform_download(track_id: int, folder_path: str, filename: str) -> None:
    print("FLAC is being downloaded")
    download_file_with_progress_bar(track_id, folder_path, filename)


def fetch_flac(source_file_path, flac_folder_path):
    """
    Fetches FLAC files based on the provided MP3 path and saves them in the FLAC folder.

    Parameters:
    - source_file_path (str): The path of the MP3 file.
    - destination_path (str): The folder where the FLAC files will be saved.

    Returns:
        - None
    """
    is_found = False
    artist_local, title_local = get_artist_and_title(source_file_path)
    list_of_songs = get_json(artist_local, title_local)
    name_local = f"{artist_local} - {title_local}"

    if not list_of_songs:
        print("Could not find", name_local)
        return
    
    for song in list_of_songs:
        if is_found:
            break

        artist   = parse_json(parse_json(song, "performer"), "name")
        title    = parse_json(song, "title")
        track_id = parse_json(song, "id")
        filename = generate_filename(song)

        print("    Found:", filename)
        name_json = f"{artist} - {title}"

        check_for_exceptions(title)
        check_for_existence(source_file_path, flac_folder_path, filename)
        
        song_action = song_handling()
        if (has_cyrillic(name_local) or has_cyrillic(name_json) and not is_found):
            if song_action == Action.download:
                is_found = True
                perform_download(track_id, flac_folder_path, filename)                
                check_and_rename(source_file_path, "mp3f")
                break
            elif song_action == Action.skip:
                print("Skipping this song\n")
                continue
            elif song_action == Action.exit:
                print("Exited successfully")
                break
            else:
                raise ValueError("Unknown error occurred") 

        if is_similar(name_local, name_json):
            perform_download(track_id, flac_folder_path, filename)                
            check_and_rename(source_file_path, "mp3f")
        else:
            print("Songs do not match\n")


def main():
    source_files = os.listdir(SOURCE_FOLDER)
    
    for filename in source_files:
        if filename.endswith("." + SOURCE_EXTENSION):
            mp3_filepath = os.path.join(SOURCE_FOLDER, filename)

            try:
                fetch_flac(mp3_filepath, FLAC_FOLDER)
            except Exception as e:
                error_message = f"An error occurred while processing {mp3_filepath}: {str(e)}"
                print(error_message)

                
if __name__ == "__main__":
    main()
