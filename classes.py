import json
import re
import shutil
import os
import eyed3
from enum import Enum
from typing import List, Tuple
from tqdm.auto import tqdm
from fuzzywuzzy import fuzz
import requests
import config as const

class Action(Enum):
    DOWNLOAD = 1
    SKIP     = 2
    EXIT     = 3
    QUIT     = 4

class SongDownload:
    DOWNLOAD_URL = "https://slavart-api.gamesdrive.net/api/download/track"

    def __init__(self, track_id: int, folder_path: str, filename: str) -> None:
        self.track_id = track_id
        self.folder_path = folder_path
        self.filename = filename

    def _url(self) -> str:
        return f"{self.DOWNLOAD_URL}?id={self.track_id}"

    def request(self) -> requests.Response:
        if const.DEBUG_COMPLEX:
            print(f"Sent request to download id={self.track_id}")

        try:
            url = self._url()
            response = requests.get(url, stream=True, verify=False)

            if const.DEBUG_COMPLEX:
                print("Response:", response.status_code)

            response.raise_for_status()  # Raise an exception for non-200 responses
            return response

        except requests.exceptions.RequestException as e:
            print("An error occurred:", e)

        return None

    def with_progress_bar(self) -> None:
        with self.request() as response:
            total_length = int(response.headers.get("Content-Length"))
            with tqdm.wrapattr(response.raw, "read", total=total_length, desc="") as downloaded:
                file_path = os.path.join(self.folder_path, self.filename)
                # Open the file in binary write mode
                with open(file_path, 'wb') as file:
                    shutil.copyfileobj(downloaded, file)
                    print("\n")

class StringAnalyzer:
    EXCLUDE_ITEMS = ["Instrumental", "Karaoke", "Originally Performed"]
    SIMILARITY_VALUE = 90
    KEYWORDS_TO_DELETE_AFTER = ["feat", "(", ",", "&", "Музыка В Машину 2023"]

    @staticmethod
    def has_cyrillic(input_string: str) -> bool:
        return bool(re.search('[а-яА-Я]', input_string))

    @staticmethod
    def has_word(input_string: str, word_dict: List[str]) -> bool:
        return any(word in input_string for word in word_dict)
    
    @staticmethod
    def has_exception(input_string: str) -> bool:
        return StringAnalyzer.has_word(input_string, StringAnalyzer.EXCLUDE_ITEMS)

    @staticmethod
    def is_similar(string1: str, string2: str) -> bool:
        similarity_ratio = fuzz.token_set_ratio(string1, string2)
        print("Similarity:", similarity_ratio)
        return similarity_ratio >= StringAnalyzer.SIMILARITY_VALUE

    @staticmethod
    def remove_after_keyword(input_string: str) -> str:
        for keyword in StringAnalyzer.KEYWORDS_TO_DELETE_AFTER:
            if keyword in input_string:
                input_string = input_string.split(keyword)[0]
                break
        return input_string

    @staticmethod
    def extract_from(input_string: str, pattern: str) -> str:
        match = re.search(pattern, input_string)
        if const.DEBUG_COMPLEX:
            print(f"Extracted: {match.group()}")
        return match.group() if match else ""

class SongHandler:
    SEARCH_URL = "https://slavart.gamesdrive.net/api/search"
    LOOK_FOR_ORIGINAL = True

    def __init__(self, source_file: str) -> None:
        self.source_file = source_file
        self._data = None
        self._file_artist, self._file_title = None, None
        self._artist, self._title = None, None
        self._bit_depth, self._sampling_rate = None, None
        self._track_id, self._filename = None, None
        self._year = None

    def extract(self) -> Tuple[str, str]:
        """
        Extracts artist and title information from an audio file's metadata.
        
        Returns:
            Tuple[str, str]: A tuple containing the artist and title of the audio file.
        """

        artist, title = None, None
        try:
            audiofile = eyed3.load(self.source_file)
            
            if audiofile.tag:
                artist = audiofile.tag.artist
                title = audiofile.tag.title
                
                if const.DEBUG:
                    print(f"\nExtracted: {artist} - {title}")
                
                if self.LOOK_FOR_ORIGINAL:
                    artist = StringAnalyzer.remove_after_keyword(artist)
                    title = StringAnalyzer.remove_after_keyword(title)
                    if const.DEBUG:
                        print(f"  Cleaned: {artist} - {title}")
            
        except Exception as e:
            print(f"Error extracting tags from {self.source_file}: {e}")
        
        self._file_artist, self._file_title = artist, title
        return self._file_artist, self._file_title

    def request(self) -> List[dict]:
        """
        Sends a request to the specified URL and returns a list of dictionaries representing the response data.
        
        Returns:
            List[dict]
        """
        if self._data is not None:
            return self._data

        query = f"{self._file_artist} {self._file_title}".replace(" ", "%20")
        url = f"{self.SEARCH_URL}?q={query}"

        try:
            return self._try_get_json(url)
        except requests.exceptions.RequestException as e:
            print("Request error:", e)
        except json.decoder.JSONDecodeError as e:
            print("Error parsing JSON response:", e)

        return None

    def _try_get_json(self, url):
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for non-200 status codes

        data = response.json()
        if const.DEBUG_COMPLEX:
            print(f"Parsed JSON for \"{self._file_artist} - {self._file_title}\"")

        self._data = data.get('tracks', {}).get('items', [])
        return self._data

    @staticmethod
    def _parse(data: dict,  key: str) -> dict | str | None:
        value = data.get(key)
        
        if const.DEBUG_COMPLEX and value is not None:
            print(f"Parsed {key} \"{value}\"")
        
        return value

    def set_info(self, data: dict) -> None:
        _artist_dict        = self._parse(data, "performer")
        _copyright          = self._parse(data, "copyright")
        self._track_id      = self._parse(data, "id")
        self._artist        = _artist_dict.get('name')
        self._title         = self._parse(data, "title")
        self._bit_depth     = self._parse(data, "maximum_bit_depth")
        self._sampling_rate = self._parse(data, "maximum_sampling_rate")
        self._year          = StringAnalyzer.extract_from(_copyright, r'\b\d{4}\b')
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

class File:
    def __init__(self, filepath: str) -> None:
        self.filepath = filepath

    def extension_to(self, ext: str) -> None:
        base_path = os.path.splitext(self.filepath)[0]
        new_filepath = f"{base_path}.{ext}"
        os.rename(self.filepath, new_filepath)

    @staticmethod
    def exists(filename: str, folder_path: str) -> bool:
        filepath = os.path.join(folder_path, filename)
        return os.path.exists(filepath)
