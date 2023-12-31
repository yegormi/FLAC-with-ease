<h1 align="center">
  <br>
  <a href="https://github.com/yegormi/FLAC-with-ease"><img src="https://s3.dualstack.us-east-2.amazonaws.com/pythondotorg-assets/media/files/python-logo-only.svg" alt="Python" width="200"></a>
  <br>
</h1>

<h4 align="center">A python script that downloads FLAC music files based on you existing Music library</h4>

## Basic process:

1. Reading metadata from MP3 files (artist, title)
2. Making a JSON request using artist and title
3. Extracting specific variable from JSON content
4. Make a download request, if there is a response, download it
4. Renaming downloaded file
5. Moving downloaded file to destination folder


## Key Features

* Asks you, if script doesn't know what to do
* Renaming source files, so you don't get confused
* Cross platform
  - Windows, macOS and Linux ready.

## Prerequisites
Make sure you have installed all of the following prerequisites on your development machine:
* Git - [Download & Install Git](https://git-scm.com/downloads). macOS and Linux machines typically have this already installed.
* Python (v3.9+) - [Download & Install Python](https://www.python.org/downloads/)

## Downloading script
There are several ways you can get it:

### Cloning The GitHub Repository
The recommended way to get my script is to use git to directly clone the repository:

```bash
$ git clone https://github.com/yegormi/FLAC-with-ease
```

This will clone the latest version of the repository to a **FLAC-with-ease** folder.

### Downloading The Repository Zip File
Another way to use it is to download a zip copy from the [master branch on GitHub](https://github.com/yegormi/FLAC-with-ease/archive/refs/heads/main.zip). You can also do this using the `wget` command:

## Running Your Application

```bash
# Go into the repository
$ cd FLAC-with-ease

# Run the app
$ python3 script.py
```

## License

MIT

---


> GitHub [@yegormi](https://github.com/yegormi) &nbsp;&middot;&nbsp;
> Gmail [egormiropoltsev79@gmail.com](mailto:egormiropoltsev79@gmail.com)
