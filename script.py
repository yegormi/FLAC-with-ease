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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
eyed3.log.setLevel("ERROR")

# DO NOT CHANGE IT! CONSTANTS
SOURCE_EXTENSION = "mp3"
# DO NOT CHANGE IT! CONSTANTS

DEBUG               = True
DEBUG_COMPLEX       = False
LOOK_FOR_ORIGINAL   = True
RENAME_SOURCE_FILES = True
SOURCE_FOLDER       = "/Users/yegormyropoltsev/Desktop/mp3"
FLAC_FOLDER         = "/Users/yegormyropoltsev/Desktop/flac"

'''
BASIC PROCESS:

1. Reading metadata from MP3 files (artist, title)
2. Making a JSON request using artist and title
3. Extracting specific variable from JSON content
4. Make a download request, if there is a response, download it
4. Renaming downloaded file
5. Moving downloaded file to destination folder
'''

class Action(Enum):
    download = 1
    skip     = 2
    exit     = 3
    quit     = 4

class Downloader:
    DOWNLOAD_URL = "https://slavart-api.gamesdrive.net/api/download/track"

    def __init__(self, track_id: int, folder_path: str, filename: str) -> None:
        self.track_id = track_id
        self.folder_path = folder_path
        self.filename = filename

    def _generate_url(self) -> str:
        """
        Generates a URL for downloading a track.

        Returns:
            str: The URL for downloading the track.
        """
        return f"{Downloader.DOWNLOAD_URL}?id={self.track_id}"

    def send_request(self) -> requests.Response:
        """
        Sends a download request and returns the response.
        
        Returns:
            requests.Response: The response object containing the result of the download request.
        """
        if DEBUG_COMPLEX:
            print(f"Sent request to download id={self.track_id}")

        try:
            url = self._generate_url()
            response = requests.get(url, stream=True, verify=False)

            if DEBUG_COMPLEX:
                print("Response:", response.status_code)
            
            response.raise_for_status()  # Raise an exception for non-200 responses
            
            return response
        
        except requests.exceptions.RequestException as e:
            print("An error occurred:", str(e))
            # You can add additional error handling or logging here

        return None

    def with_progress_bar(self) -> None:
        """
        Downloads a file from a given URL and displays a progress bar.

        Returns:
            None
        """
        # Send a download request for the track
        with self.send_request() as response:
            # Get the total length of the file
            total_length = int(response.headers.get("Content-Length"))
            
            # Wrap the response in a tqdm downloaded content
            with tqdm.wrapattr(response.raw, "read", total=total_length, desc="") as downloaded:
                # Create the file path
                file_path = os.path.join(self.folder_path, self.filename)
                
                # Open the file in binary write mode
                with open(file_path, 'wb') as file:
                    # Copy the contents of the downloaded content to the file
                    shutil.copyfileobj(downloaded, file)
                    
                    # Print a newline character to separate the progress bar from other output
                    print("\n")

class Analyzer:
    EXCLUDE_ITEMS = ["Instrumental", "Karaoke"]
    SIMILARITY_VALUE = 90
    KEYWORDS_TO_DELETE_AFTER = ["feat", "(", ",", "&", "Музыка В Машину 2023"]

    def has_cyrillic(input_string: str) -> bool:
        """
        Check if the given text contains Cyrillic characters.

        Args:
            input_string (str): The text to be checked.

        Returns:
            bool: True if the text contains Cyrillic characters, False otherwise.
        """
        return bool(re.search('[а-яА-Я]', input_string))

    def has_word(input_string: str, word_dict: List[str]) -> bool:
        """
        Check if any word from the given word dictionary is present in the input string.

        Parameters:
            input_string (str): The input string to search for words in.
            word_dict (List[str]): The list of words to search for in the input string.

        Returns:
            bool: True if any word from the word dictionary is present in the input string, False otherwise.
        """
        return any(word in input_string for word in word_dict)
    
    def has_exception(input_string: str) -> bool:
        """
        Check for any exceptions in the given title.
        
        Parameters:
            input_string (str): The title to check for exceptions.
            
        Returns:
            bool: True if an exception is found, False otherwise.
        """
        return Analyzer.has_word(input_string, Analyzer.EXCLUDE_ITEMS)

    def is_similar(string1: str, string2: str) -> bool:
        """
        Check if two strings are similar based on their token set ratio.

        Args:
            string1 (str): The first string to compare.
            string2 (str): The second string to compare.

        Returns:
            bool: True if the similarity ratio is greater than or equal to SIMILARITY_VALUE, False otherwise.
        """
        similarity_ratio = fuzz.token_set_ratio(string1, string2)
        print("Similarity:", similarity_ratio)
        return similarity_ratio >= Analyzer.SIMILARITY_VALUE

    def remove_after_keyword(input_string: str) -> str:
        """
        Remove the part of the input string that comes after any of the keywords in KEYWORDS_TO_DELETE_AFTER.
        
        Args:
            input_string (str): The input string from which to remove the text.
            
        Returns:
            str: The modified input string with the text removed.
        """
        for keyword in Analyzer.KEYWORDS_TO_DELETE_AFTER:
            if keyword in input_string:
                input_string = input_string.split(keyword)[0]
                break
        return input_string

    def extract_from(input_string: str, pattern: str) -> str:
        """
        Extracts a substring from the input string that matches the given pattern.

        Parameters:
            input_string (str): The input string from which to extract the substring.
            pattern (str): The regular expression pattern used to match the substring.

        Returns:
            str: The extracted substring if a match is found, otherwise an empty string.
        """
        match = re.search(pattern, input_string)
        if DEBUG_COMPLEX:
            print(f"Extracted: {match.group()}")
        return match.group() if match else ""

class Handler:
    SEARCH_URL = "https://slavart.gamesdrive.net/api/search"

    def __init__(self, source_file: str) -> None:
        self.source_file = source_file
        self._data = None
        self._file_artist, self._file_title = None, None
        self._artist, self._title            = None, None
        self._bit_depth, self._sampling_rate = None, None
        self._year          = None
        self._track_id, self._filename       = None, None

    def extract(self) -> Tuple[str, str]:

        artist, title = None, None
        try:
            audiofile = eyed3.load(self.source_file)
            
            if audiofile.tag:
                artist = audiofile.tag.artist
                title = audiofile.tag.title
                
                if DEBUG:
                    print(f"\nExtracted: {artist} - {title}")
                
                if LOOK_FOR_ORIGINAL:
                    artist = Analyzer.remove_after_keyword(artist)
                    title = Analyzer.remove_after_keyword(title)
                    if DEBUG:
                        print(f"  Cleaned: {artist} - {title}")
            
        except Exception as e:
            print(f"Error extracting tags from {self.source_file}: {e}")
        
        self._file_artist, self._file_title = artist, title
        return self._file_artist, self._file_title

    def request(self) -> List[dict]:
        if self._data is not None:
            return self._data
        
        query = f"{self._file_artist} {self._file_title}".replace(" ", "%20")
        url = f"{self.SEARCH_URL}?q={query}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise exception for non-200 status codes
            
            data = response.json()
            if DEBUG_COMPLEX:
                print(f"Parsed JSON for \"{self._file_artist} - {self._file_title}\"")
            
            self._data = data.get('tracks', {}).get('items', [])
            # self._data = data['tracks']['items']
            return self._data
        
        except requests.exceptions.RequestException as e:
            print("Request error:", e)
        except json.decoder.JSONDecodeError as e:
            print("Error parsing JSON response:", e)
        
        return None

    def parse(self, data: dict,  key: str) -> dict | str | None:
        value = data.get(key)
        
        if DEBUG_COMPLEX and value is not None:
            print(f"Parsed {key} \"{value}\"")
        
        return value

    def set_info(self, data: dict) -> None:
        _artist_dict        = self.parse(data, "performer")
        _copyright          = self.parse(data, "copyright")
        self._track_id      = self.parse(data, "id")
        self._artist        = _artist_dict.get('name')
        self._title         = self.parse(data, "title")
        self._bit_depth     = self.parse(data, "maximum_bit_depth")
        self._sampling_rate = self.parse(data, "maximum_sampling_rate")
        self._year          = Analyzer.extract_from(_copyright, r'\b\d{4}\b')
        self._filename      = f"{self._artist} - {self._title} ({self._year}) [FLAC] [{self._bit_depth}B - {self._sampling_rate}kHz].flac"
    
    @property
    def artist(self):
        return self._artist
    @property
    def title(self):
        return self._title
    @property
    def track_id(self):
        return self._track_id
    @property
    def bit_depth(self):
        return self._bit_depth
    @property
    def sampling_rate(self):
        return self._sampling_rate
    @property
    def year(self):
        return self._year
    @property
    def filename(self):
        return self._filename



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
    downloader = Downloader(track_id, folder_path, filename)
    downloader.with_progress_bar()



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
    song = Handler(source_file_path)
    artist_local, title_local = song.extract()
    list_of_songs = song.request()
    name_local = f"{artist_local} - {title_local}"

    if not list_of_songs:
        print("Could not find", name_local)
        return
    
    for item in list_of_songs:
        song.set_info(item)
        print("    Found:", song.filename)
        name_json = f"{song.artist} - {song.title}"

        if Analyzer.has_exception(song.title):
            print("An exception! Heading to the next one...\n")
            continue

        if does_file_exist(flac_folder_path, song.filename):
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
                raise ValueError("Unknown error occurred") 
        else:
            if Analyzer.is_similar(name_local, name_json):
                perform_download(song.track_id, flac_folder_path, song.filename)      
                check_and_rename(source_file_path, "mp3f")
            else:
                print("Songs do not match\n")

def main():
    source_files = os.listdir(SOURCE_FOLDER)
    
    for filename in source_files:
        if filename.endswith("." + SOURCE_EXTENSION):
            mp3_filepath = os.path.join(SOURCE_FOLDER, filename)

            # try:
            process_and_handle_songs(mp3_filepath, FLAC_FOLDER)
            # except Exception as e:
            #     error_message = f"An error occurred while processing {mp3_filepath}: {str(e)}"
            #     print(error_message)
             
if __name__ == "__main__":
    main()
