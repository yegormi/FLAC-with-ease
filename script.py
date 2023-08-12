import json     # JSON Management
import os       # For renaming and placing files
import re       # RegEx - extracting year from given string
import shutil   # For downloading file
from typing import List, Tuple  # Type hints

import eyed3    # For reading ID3 tags from mp3 files
import requests # For making an HTTP request
import urllib3  # To supress unsecure HTTP requests
from fuzzywuzzy import fuzz
from tqdm.auto  import tqdm

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

def change_file_extension(file_path: str, new_extension: str) -> None:
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

def contains_year(text):
    """
    Check if the given text contains a year.

    Parameters:
        text (str): The text to be checked.

    Returns:
        int or bool: The year found in the text, as an integer, if found. False otherwise.
    """
    match = re.search(r'\b\d{4}\b', text)
    return int(match.group()) if match else False

def get_url(track_id: int) -> str:
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
        url = get_url(track_id)
        response = requests.get(url, stream=True, verify=False)

        if DEBUG:
            print("Response:", response.status_code)
        return response

    except Exception as e:
        print("An error occurred:", str(e))
        # You can add additional error handling or logging here

    return None


def download_file_bar(track_id: str, destination: str, filename: str) -> None:
    """
    Download a file from a given URL and display a progress bar.
    
    Args:
        track_id (str): The ID of the track to download.
        destination (str): The destination directory to save the downloaded file.
        filename (str): The name of the downloaded file.
    """
    # Get the URL for the track
    url = get_url(track_id)
    
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

def check_words_in_string(input_string: str, word_dict: List[str]) -> bool:
    """
    Check if any word from the word dictionary is present in the input string.

    Args:
        input_string (str): The input string to search for words.
        word_dict (List[str]): The list of words to search for in the input string.

    Returns:
        bool: True if any word from word_dict is found in the input_string, False otherwise.
    """
    return any(word in input_string for word in word_dict)

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
    
    for data in list_of_songs:
        if is_found:
            is_found = False
            continue

        artist        = parse_json(parse_json(data, "performer"), "name")
        title         = parse_json(data, "title")
        bit_depth     = parse_json(data, "maximum_bit_depth")
        sampling_rate = parse_json(data, "maximum_sampling_rate")
        print(f"    Found: {artist} - {title} [{bit_depth}B - {sampling_rate}kHz]")

        isContains = check_words_in_string(title, EXCLUDE_ITEMS)
        if isContains:
            print("An exception! Heading to the next one...")
            continue
        
        name_json = f"{artist} - {title}"
        track_id  = parse_json(data, "id")
        copyright = parse_json(data, "copyright")
        year      = contains_year(copyright) if contains_year(copyright) else ""
            
        filename = f"{artist} - {title} ({year}) [FLAC] [{bit_depth}B - {sampling_rate}kHz].flac"
        filename = filename.replace("/", "-")

        if os.path.exists(os.path.join(flac_folder_path, filename)):
            print("File already exists. Skipping...")
            if RENAME_SOURCE_FILES:
                change_file_extension(source_file_path, "mp3f")
                print("MP3 file has been changed")
            break

        if (has_cyrillic(name_local) or has_cyrillic(name_json)) and not is_found:
            while True:
                print("Does this song match your request?")
                print("1. YES")
                print("2. NO")
                print("3. EXIT")
                user_input = input()
                if user_input == '1':
                    print("FLAC is being downloaded")
                    is_found = True
                    download_file_bar(track_id, flac_folder_path, filename)
                    if RENAME_SOURCE_FILES:
                        change_file_extension(source_file_path, "mp3f")
                        print("MP3 file has been changed")
                    break
                elif user_input == '2':
                    print("Skipping this song...")
                    break
                elif user_input == '3':
                    print("EXITING")
                    should_exit_for_loop = True
                    break
                else:
                    print("Invalid input. Please enter '1' or '2'.")
            if should_exit_for_loop:
                break

        else:
            similarity_ratio = fuzz.token_set_ratio(name_local, name_json)
            print("Similarity:", similarity_ratio)

            if similarity_ratio >= SIMILARITY_VALUE:
                print("FLAC is being downloaded")
                download_file_bar(track_id, flac_folder_path, filename)
                if RENAME_SOURCE_FILES:
                    change_file_extension(source_file_path, "mp3f")
                    print("MP3 file has been changed")
                break

            print("Songs do not match")


def main():
    for filename in os.listdir(SOURCE_FOLDER):
        if filename.endswith("." + SOURCE_EXTENSION):
            mp3_filepath = os.path.join(SOURCE_FOLDER, filename)
            try:
                fetch_flac(mp3_filepath, FLAC_FOLDER)
            except Exception as e:
                print(f"An error occurred while processing {mp3_filepath}: {str(e)}")

if __name__ == "__main__":
    main()
