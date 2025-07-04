import os
from .logger import logger
from moviepy import editor

def is_audio_file(filepath):
    audio_exts = ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a']
    return os.path.splitext(filepath)[1].lower() in audio_exts 

def get_audio_duration(filepath):
    """Return duration of audio file in seconds. Returns 0 if file is invalid or unreadable."""
    try:
        audio = editor.AudioFileClip(filepath)
        duration = int(audio.duration)
        audio.close()
        return duration
    except Exception as e:
        logger.exception(f"Failed to get duration for {filepath}")
    return 0 

def create_if_not_exists(directory):
    if not os.path.isdir(directory):
        os.mkdir(directory)
        logger.info(f"{directory} was absent. Created the missing directory.") 