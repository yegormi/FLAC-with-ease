import json     # JSON Management
import os       # For renaming and placing files
import re       # RegEx - extracting year from given string
import shutil   # For downloading file
from enum import Enum           # Create a custom enum
from typing import List, Tuple  # Type hints
from tqdm.auto import tqdm      # For progress bar
from fuzzywuzzy import fuzz     # For fuzzy matching
import eyed3     # For reading ID3 tags from mp3 files
import requests  # For making an HTTP request
import urllib3   # To supress unsecure HTTP requests


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
DEBUG_COMPLEX       = True
LOOK_FOR_ORIGINAL   = True
RENAME_SOURCE_FILES = True
SOURCE_FOLDER       = "/Users/yegormyropoltsev/Desktop/mp3"
FLAC_FOLDER         = "/Users/yegormyropoltsev/Desktop/flac"

def get_artist_and_title(source_file: str) -> Tuple[str, str]:
    """
    Extracts the artist and title information from an MP3 file.

    Args:
        source_file (str): The path to the MP3 file.

    Returns:
        tuple: A tuple containing the artist and title extracted from the MP3 file.
               If the MP3 file does not have tag information, returns (None, None).
    """
    artist, title = None, None
    
    try:
        audiofile = eyed3.load(source_file)
        
        if audiofile.tag:
            artist = audiofile.tag.artist
            title = audiofile.tag.title
            
            if DEBUG:
                print(f"\nExtracted: {artist} - {title}")
            
            if LOOK_FOR_ORIGINAL:
                artist = remove_content_after_keyword(artist)
                title = remove_content_after_keyword(title)
                if DEBUG:
                    print(f"  Cleaned: {artist} - {title}")
        
    except Exception as e:
        print(f"Error extracting tags from {source_file}: {e}")
    
    return artist, title




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
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for non-200 status codes
        
        json_data = response.json()
        if DEBUG_COMPLEX:
            print(f"Parsed JSON \"{artist} - {title}\"")
        
        return json_data.get('tracks', {}).get('items', [])
    
    except requests.exceptions.RequestException as e:
        print("Request error:", e)
    except json.decoder.JSONDecodeError as e:
        print("Error parsing JSON response:", e)
    
    return None


def parse_json(data: dict, key: str) -> str:
    """
    Parses the specified JSON object and returns the value of the specified key.

    Parameters:
        data (dict): The JSON object to parse.
        key (str): The name of the key to retrieve from the JSON object.

    Returns:
        The value of the specified key from the JSON object.
    """
    value = data.get(key)
    
    if DEBUG_COMPLEX and value is not None:
        print(f"Parsed {key} \"{value}\"")
    
    return value


def generate_filename(data: dict) -> str:
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
    artist_dict   = parse_json(data, "performer")
    artist        = parse_json(artist_dict, "name")
    title         = parse_json(data, "title")
    bit_depth     = parse_json(data, "maximum_bit_depth")
    sampling_rate = parse_json(data, "maximum_sampling_rate")
    copyright     = parse_json(data, "copyright")
    year          = parse_year(copyright)
    filename      = f"{artist} - {title} ({year}) [FLAC] [{bit_depth}B - {sampling_rate}kHz].flac"
        
    return filename.replace("/", "-")




def generate_url(track_id: int) -> str:
    """
    Generates a URL for downloading a track based on the given track ID.

    Parameters:
        track_id (int): The ID of the track to be downloaded.

    Returns:
        str: The URL for downloading the track.
    """
    return f"{DOWNLOAD_URL}?id={track_id}"

def send_download_request(track_id: int) -> requests.Response:
    """
    Sends a download request for a given track ID and returns the response.

    Parameters:
        track_id (int): The ID of the track to download.

    Returns:
        requests.Response: The response object containing the download data.

    Raises:
        requests.exceptions.RequestException: If an error occurs while sending the request.

    """
    if DEBUG_COMPLEX:
        print(f"Sent request to download id={track_id}")

    try:
        url = generate_url(track_id)
        response = requests.get(url, stream=True, verify=False)

        if DEBUG_COMPLEX:
            print("Response:", response.status_code)
        
        response.raise_for_status()  # Raise an exception for non-200 responses
        
        return response
    
    except requests.exceptions.RequestException as e:
        print("An error occurred:", str(e))
        # You can add additional error handling or logging here

    return None


def download_file_with_progress_bar(track_id: str, destination: str, filename: str) -> None:
    """
    Downloads a file with a progress bar.

    Args:
        track_id (str): The ID of the track to download.
        destination (str): The destination directory to save the file.
        filename (str): The name of the file to save.

    Returns:
        None
    """

    # Send a download request for the track
    with send_download_request(track_id) as response:
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



def remove_content_after_keyword(input_string: str) -> str:
    """
    Removes any content after a keyword in the input_string.

    Args:
        input_string (str): The string to check for keywords.

    Returns:
        str: The input_string with any content after the keyword removed.
    """
    for keyword in KEYWORDS_TO_DELETE_AFTER:
        if keyword in input_string:
            input_string = input_string.split(keyword)[0]
            break
    return input_string

def has_cyrillic(input_string: str) -> bool:
    """
    Check if the given text contains Cyrillic characters.

    Args:
        input_string (str): The text to be checked.

    Returns:
        bool: True if the text contains Cyrillic characters, False otherwise.
    """
    return bool(re.search('[а-яА-Я]', input_string))

def parse_year(input_string: str) -> str:
    """
    Parse the year from the given text.

    Parameters:
        text (str): The text to search for a year.

    Returns:
        str: The parsed year as an integer if found, or an empty string if not found.
    """
    match = re.search(r'\b\d{4}\b', input_string)
    return match.group() if match else ""

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

def is_exception(input_string: str) -> bool:
    """
    Check for any exceptions in the given title.
    
    Parameters:
        title (str): The title to check for exceptions.
        
    Returns:
        bool: True if an exception is found, False otherwise.
    """
    return is_word_present(input_string, EXCLUDE_ITEMS)

def is_similar(string1: str, string2: str) -> bool:
    """
    Check if two strings are similar based on their token set ratio.
    
    Parameters:
        string1 (str): The first string to compare.
        string2 (str): The second string to compare.
        
    Returns:
        bool: True if the similarity ratio is greater than or equal to SIMILARITY_VALUE, False otherwise.
    """
    similarity_ratio = fuzz.token_set_ratio(string1, string2)
    print("Similarity:", similarity_ratio)
    return similarity_ratio >= SIMILARITY_VALUE



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

def does_file_exist(flac_folder_path: str, flac_filename: str) -> bool:
    """
    Check if a file exists in a given folder path.

    Args:
        flac_folder_path (str): The path to the folder where the file should be located.
        flac_filename (str): The name of the file to check.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    flac_file_path = os.path.join(flac_folder_path, flac_filename)
    if os.path.exists(flac_file_path):
        return True
    return False

def check_and_rename(filepath: str, ext: str) -> None:
    if RENAME_SOURCE_FILES:
        rename_file(filepath, ext)
        print("Source file has been renamed")

def perform_download(track_id: int, folder_path: str, filename: str) -> None:
    print("FLAC is being downloaded")
    download_file_with_progress_bar(track_id, folder_path, filename)



def song_handling() -> Action:
    """
    Handles the user interaction for song handling.
    
    This function prompts the user with options for handling a song and 
    returns the appropriate action based on the user's choice.
    
    Returns:
        Action: The action to be taken for the song. It can be 
        Action.download, Action.skip, or Action.exit.
    """
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
            print("Invalid input. Please enter '1' or '2' or '3'.")

def process_and_handle_songs(source_file_path: str, flac_folder_path: str) -> None:
    found = False
    artist_local, title_local = get_artist_and_title(source_file_path)
    list_of_songs = get_json(artist_local, title_local)
    name_local = f"{artist_local} - {title_local}"

    if not list_of_songs:
        print("Could not find", name_local)
        return
    
    for song in list_of_songs:
        if found:
            break

        artist   = parse_json(parse_json(song, "performer"), "name")
        title    = parse_json(song, "title")
        track_id = parse_json(song, "id")
        filename = generate_filename(song)

        print("    Found:", filename)
        name_json = f"{artist} - {title}"

        if is_exception(title):
            print("An exception! Heading to the next one...\n")
            continue

        if does_file_exist(flac_folder_path, filename):
            print("File already exists. Skipping...\n")
            check_and_rename(source_file_path, "mp3f")
            continue

        song_action = song_handling()
        if ((has_cyrillic(name_local) or has_cyrillic(name_json)) and not found):
            if song_action == Action.download:
                found = True
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
                process_and_handle_songs(mp3_filepath, FLAC_FOLDER)
            except Exception as e:
                error_message = f"An error occurred while processing {mp3_filepath}: {str(e)}"
                print(error_message)
             
if __name__ == "__main__":
    main()
