import os
import argparse
import logging
import requests

from pytubefix import YouTube
from moviepy import editor

FORMAT_CONS = '%(asctime)s %(name)-12s %(levelname)8s\t%(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT_CONS)
logger = logging.getLogger(__name__)


def create_if_not_exists(directory):
  if not os.path.isdir(directory):
    os.mkdir(directory)
    logger.info(f"{directory} was absent. Created the missing directory.")


def download_videos(file, video_dir):
  logger.info(f"Downloading videos from {file} to {video_dir}")
  create_if_not_exists(video_dir)
  downloaded_files = []
  for url in file:
    url = url.strip('\n')
    if not url:
      continue

    try:
      logger.info(f"Trying to connect to {url}")
      yt = YouTube(url, 'TV')
    except Exception as error:
      logger.error(f"[{url}] Connection Error: {error}")
      continue

    logger.info("Successfully connected")
    streams = yt.streams
    logger.info("Found streams")
    stream = streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
    logger.info("Starting download")
    try:
      out_file = stream.download(video_dir)
      logger.info(f"[Downloaded] {stream.title}")
      downloaded_files.append(os.path.basename(out_file))
    except Exception as error:
      logger.error(f"[{url}] Download Error: {error}")
  return downloaded_files

def __transcribe_audio_by_sarvam(file_path):
  logger.info(f"Calling Sarvam API for {file_path}")
  headers = {
    "api-subscription-key": os.getenv("SARVAM_API_KEY"),
  }
  files = {
    "file": (file_path, open(file_path, 'rb'), "audio/mpeg")
  }

  try:
    response = requests.post(
      "https://api.sarvam.ai/speech-to-text",
      headers=headers,
      files=files,
    )
    response.raise_for_status()
    return response.json()
  except Exception as error:
    if hasattr(error, 'response') and error.response is not None:
      logger.error(f"[{file_path}] Transcribe Error: {error} | Response: {error.response.text}")
    else:
      logger.error(f"[{file_path}] Transcribe Error: {error}")
    return None

def transcribe(audio_files):
  create_if_not_exists('transcripts')
  create_if_not_exists('guj-transcripts')
  create_if_not_exists('audio-breakdowns')

  for audio_file in audio_files:
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    breakdown_dir = os.path.join('audio-breakdowns', base_name)
    create_if_not_exists(breakdown_dir)

    # Split audio into 25s chunks
    audio = editor.AudioFileClip(audio_file)
    duration = int(audio.duration)
    chunk_paths = []
    for i in range(0, duration, 25):
      chunk = audio.subclip(i, min(i + 25, duration))
      chunk_path = os.path.join(breakdown_dir, f"chunk_{i//25 + 1}.mp3")
      chunk.write_audiofile(chunk_path, logger=None)
      chunk_paths.append(chunk_path)

    # Transcribe each chunk and collect results
    transcript = []
    for chunk_path in chunk_paths:
      result = __transcribe_audio_by_sarvam(chunk_path)
      if result and 'transcript' in result:
        transcript.append(result['transcript'])
      else:
        logger.error(f"[{chunk_path}] Transcribe Error: {result}")

    # Merge all data into a txt file
    transcript_path = os.path.join('transcripts', f"{base_name}.txt")
    with open(transcript_path, 'w', encoding='utf-8') as f:
      f.write('\n'.join(transcript))


def convert_to_audio(video_dir, audio_dir, video_files=None):
  logger.info(f"Converting videos from {video_dir} to {audio_dir} {'with' if video_files is not None else ''}")

  create_if_not_exists(audio_dir)

  if video_files is None:
    videos = os.listdir(video_dir)
  else:
    videos = video_files

  for video in videos:
    source = editor.VideoFileClip(f"{video_dir}/{video}")
    source.audio.write_audiofile(f"{audio_dir}/{''.join(video.split('.')[:-1])}.mp3")


if __name__ == '__main__':
  parser = argparse.ArgumentParser()

  parser.add_argument('--download', '-d',
                    action="store_true",
                    help='Use this to download the videos specified for the --file option',
                    default=False)

  parser.add_argument('--convert', '-c',
                    action="store_true",
                    help='Use this to convert videos in --video-dir folder into --audio-dir',
                    default=False)

  parser.add_argument('--file', '-f',
                    type=argparse.FileType('r', encoding='utf-8', errors='ignore'),
                    help='Specify the file holding the youtube urls')

  parser.add_argument('--video-dir', '-v',
                    type=str,
                    help='Specify the directory where the videos are to be downloaded')

  parser.add_argument('--audio-dir', '-a',
                    type=str,
                    help='Specify the directory where the audios are to be downloaded')

  parser.add_argument('--transcribe', '-t',
                    action="store_true",
                    help='Use this to transcribe audio files in --audio-dir',
                    default=False)

  args = parser.parse_args()
  downloaded_files = None
  if args.download:
    if not args.file:
      logger.error("Missing --file parameter")
      exit(1)
    downloaded_files = download_videos(args.file, args.video_dir)
  if args.convert:
    if not args.audio_dir:
      logger.error("Missing --audio-dir parameter")
      exit(1)
    if downloaded_files is not None:
      convert_to_audio(args.video_dir, args.audio_dir, downloaded_files)
    else:
      convert_to_audio(args.video_dir, args.audio_dir)
  if args.transcribe:
    if not args.audio_dir:
      logger.error("Missing --audio-dir parameter")
      exit(1)
    audio_files = [os.path.join(args.audio_dir, f) for f in os.listdir(args.audio_dir) if f.endswith('.mp3')]
    if not audio_files:
      logger.error(f"No audio files found in {args.audio_dir}")
      exit(1)
    transcribe(audio_files)