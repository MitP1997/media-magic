import requests
import os
from .logger import logger
from azure.storage.filedatalake.aio import DataLakeDirectoryClient, FileSystemClient
from azure.storage.filedatalake import ContentSettings
import aiofiles
import mimetypes
import asyncio
from urllib.parse import urlparse
import json
from moviepy import editor

# class SarvamTranscriber:
#     """
#     Handles audio transcription using SarvamAI's speech-to-text API.
#     """
#     API_URL = "https://api.sarvam.ai/speech-to-text"
#     DEFAULT_MODEL = "saarika:v2.5"

#     def __init__(self, api_key: str, model: str = None):
#         self.api_key = api_key
#         self.model = model or self.DEFAULT_MODEL

#     def transcribe(self, audio_path: str, language_code: str = "unknown") -> dict:
#         """
#         Transcribe an audio file using SarvamAI's API.
#         Returns the API response as a dict.
#         """
#         if not os.path.isfile(audio_path):
#             logger.error(f"Audio file does not exist: {audio_path}")
#             raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
        
#         files = {
#             'audio': open(audio_path, 'rb')
#         }
#         data = {
#             'model': self.model,
#             'language_code': language_code
#         }
#         headers = {
#             'api-subscription-key': self.api_key
#         }
#         try:
#             logger.info(f"Sending transcription request for {audio_path} to SarvamAI...")
#             response = requests.post(self.API_URL, files=files, data=data, headers=headers)
#             response.raise_for_status()
#             logger.info(f"Transcription successful for {audio_path}")
#             return response.json()
#         except Exception as e:
#             logger.error(f"Transcription failed for {audio_path}: {e}")
#             raise
#         finally:
#             files['audio'].close()

class SarvamBatchTranscriber:
    API_INIT_URL = "https://api.sarvam.ai/speech-to-text/job/init"
    API_START_URL = "https://api.sarvam.ai/speech-to-text/job"
    API_STATUS_URL = "https://api.sarvam.ai/speech-to-text/job/{job_id}/status"

    def __init__(self, api_key: str, language_code: str = "unknown"):
        self.api_key = api_key
        self.language_code = language_code
        self.lock = asyncio.Lock()

    async def initialize_job(self):
        logger.info("Called initialize_job")
        headers = {"API-Subscription-Key": self.api_key}
        logger.info("Initializing batch job...")
        response = requests.post(self.API_INIT_URL, headers=headers)
        logger.info(f"initialize_job response status: {response.status_code}")
        if response.status_code == 202:
            logger.info(f"Job initialized: {response.json()}")
            return response.json()
        else:
            logger.error(f"Failed to initialize job: {response.text}")
            return None

    async def check_job_status(self, job_id):
        logger.info(f"Called check_job_status with job_id: {job_id}")
        url = self.API_STATUS_URL.format(job_id=job_id)
        headers = {"API-Subscription-Key": self.api_key}
        logger.info(f"Checking status for job: {job_id}")
        response = requests.get(url, headers=headers)
        logger.info(f"check_job_status response status: {response.status_code}")
        if response.status_code == 200:
            logger.info(f"Job status: {response.json()}")
            return response.json()
        else:
            logger.error(f"Failed to get job status: {response.text}")
            return None

    async def start_job(self, job_id):
        logger.info(f"Called start_job with job_id: {job_id}")
        headers = {
            "API-Subscription-Key": self.api_key,
            "Content-Type": "application/json",
        }
        data = {"job_id": job_id, "job_parameters": {"language_code": self.language_code}}
        logger.info(f"Starting job: {job_id} with data: {data}")
        response = requests.post(self.API_START_URL, headers=headers, data=json.dumps(data))
        logger.info(f"start_job response status: {response.status_code}")
        if response.status_code == 200:
            logger.info(f"Job started: {response.json()}")
            return response.json()
        else:
            logger.error(f"Failed to start job: {response.text}")
            return None

    def _extract_url_components(self, url: str):
        logger.info(f"Called _extract_url_components with url: {url}")
        parsed_url = urlparse(url)
        account_url = f"{parsed_url.scheme}://{parsed_url.netloc}".replace(
            ".blob.", ".dfs."
        )
        path_components = parsed_url.path.strip("/").split("/")
        file_system_name = path_components[0]
        directory_name = "/".join(path_components[1:])
        sas_token = parsed_url.query
        logger.info(f"Extracted account_url: {account_url}, file_system_name: {file_system_name}, directory_name: {directory_name}")
        return account_url, file_system_name, directory_name, sas_token

    async def upload_files(self, input_storage_url, local_file_paths, overwrite=True):
        logger.info(f"Called upload_files with input_storage_url: {input_storage_url}, local_file_paths: {local_file_paths}, overwrite: {overwrite}")
        account_url, file_system_name, directory_name, sas_token = self._extract_url_components(input_storage_url)
        logger.info(f"Uploading {len(local_file_paths)} files to {directory_name}")
        async with DataLakeDirectoryClient(
            account_url=f"{account_url}?{sas_token}",
            file_system_name=file_system_name,
            directory_name=directory_name,
            credential=None,
        ) as directory_client:
            tasks = []
            for path in local_file_paths:
                file_name = os.path.basename(path)
                logger.info(f"Preparing to upload file: {file_name}")
                tasks.append(self._upload_file(directory_client, path, file_name, overwrite))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"Upload completed for {sum(1 for r in results if not isinstance(r, Exception))} files")
            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error uploading file {local_file_paths[idx]}: {result}")

    async def _upload_file(self, directory_client, local_file_path, file_name, overwrite=True):
        logger.info(f"Called _upload_file with local_file_path: {local_file_path}, file_name: {file_name}, overwrite: {overwrite}")
        try:
            async with aiofiles.open(local_file_path, mode="rb") as file_data:
                mime_type = mimetypes.guess_type(local_file_path)[0] or "audio/wav"
                file_client = directory_client.get_file_client(file_name)
                data = await file_data.read()
                logger.info(f"Uploading data for file: {file_name}, size: {len(data)} bytes, mime_type: {mime_type}")
                await file_client.upload_data(
                    data,
                    overwrite=overwrite,
                    content_settings=ContentSettings(content_type=mime_type),
                )
                logger.info(f"File uploaded successfully: {file_name}")
                return True
        except Exception as e:
            logger.error(f"Upload failed for {file_name}: {str(e)}")
            return False

    async def list_files(self, storage_url):
        logger.info(f"Called list_files with storage_url: {storage_url}")
        account_url, file_system_name, directory_name, sas_token = self._extract_url_components(storage_url)
        logger.info(f"Listing files in directory: {directory_name}")
        file_names = []
        async with FileSystemClient(
            account_url=f"{account_url}?{sas_token}",
            file_system_name=file_system_name,
            credential=None,
        ) as file_system_client:
            async for path in file_system_client.get_paths(directory_name):
                file_name = path.name.split("/")[-1]
                async with self.lock:
                    file_names.append(file_name)
                logger.info(f"Found file: {file_name}")
        logger.info(f"Found {len(file_names)} files: {file_names}")
        return file_names

    async def download_files(self, storage_url, file_names, destination_dir):
        logger.info(f"Called download_files with storage_url: {storage_url}, file_names: {file_names}, destination_dir: {destination_dir}")
        account_url, file_system_name, directory_name, sas_token = self._extract_url_components(storage_url)
        logger.info(f"Downloading {len(file_names)} files to {destination_dir}")
        async with DataLakeDirectoryClient(
            account_url=f"{account_url}?{sas_token}",
            file_system_name=file_system_name,
            directory_name=directory_name,
            credential=None,
        ) as directory_client:
            tasks = []
            for file_name in file_names:
                logger.info(f"Preparing to download file: {file_name}")
                tasks.append(self._download_file(directory_client, file_name, destination_dir))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"Download completed for {sum(1 for r in results if not isinstance(r, Exception))} files")
            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error downloading file {file_names[idx]}: {result}")

    async def _download_file(self, directory_client, file_name, destination_dir):
        logger.info(f"Called _download_file with file_name: {file_name}, destination_dir: {destination_dir}")
        try:
            file_client = directory_client.get_file_client(file_name)
            download_path = os.path.join(destination_dir, file_name)
            async with aiofiles.open(download_path, mode="wb") as file_data:
                stream = await file_client.download_file()
                data = await stream.readall()
                logger.info(f"Writing data to {download_path}, size: {len(data)} bytes")
                await file_data.write(data)
            logger.info(f"Downloaded: {file_name} -> {download_path}")
            return True
        except Exception as e:
            logger.error(f"Download failed for {file_name}: {str(e)}")
            return False

    def split_audio(self, audio_path, chunk_duration_ms):
        logger.info(f"Called split_audio with audio_path: {audio_path}, chunk_duration_ms: {chunk_duration_ms}")
        chunk_duration = chunk_duration_ms / 1000  # convert ms to seconds
        audio = editor.AudioFileClip(audio_path)
        duration = int(audio.duration)
        logger.info(f"Audio duration: {duration} seconds")
        chunks = []
        for i in range(0, duration, int(chunk_duration)):
            start = i
            end = min(i + int(chunk_duration), duration)
            logger.info(f"Creating chunk from {start} to {end}")
            chunk = audio.subclip(start, end)
            chunks.append(chunk)
        audio.close()
        logger.info(f"Total chunks created: {len(chunks)}")
        return chunks

    async def transcribe_batch(self, local_files, destination_dir, chunk_duration_ms=10*60*1000, progress_callback=None):
        logger.info(f"Called transcribe_batch with local_files: {local_files}, destination_dir: {destination_dir}, chunk_duration_ms: {chunk_duration_ms}")
        # Step 1: Initialize the job
        job_info = await self.initialize_job()
        if not job_info:
            logger.error("Job initialization failed")
            if progress_callback:
                progress_callback("Job initialization failed")
            return
        job_id = job_info["job_id"]
        input_storage_path = job_info["input_storage_path"]
        output_storage_path = job_info["output_storage_path"]

        # Step 2: Upload files (split if needed)
        files_to_upload = []
        for file in local_files:
            logger.info(f"Processing file: {file}")
            audio = editor.AudioFileClip(file)
            logger.info(f"Audio duration (s): {audio.duration}")
            if audio.duration * 1000 > chunk_duration_ms:
                base = os.path.splitext(os.path.basename(file))[0]
                chunks = self.split_audio(file, chunk_duration_ms)
                chunk_paths = []
                for idx, chunk in enumerate(chunks):
                    chunk_path = os.path.join(destination_dir, f"{base}_chunk_{idx+1}.wav")
                    logger.info(f"Exporting chunk {idx+1} to {chunk_path}")
                    chunk.export(chunk_path, format="wav")
                    chunk_paths.append(chunk_path)
                files_to_upload.extend(chunk_paths)
            else:
                files_to_upload.append(file)

            audio.close()
            logger.info(f"Finished processing file: {file}")

        if progress_callback:
            progress_callback("Uploading files...")
        logger.info(f"Uploading files: {files_to_upload}")
        await self.upload_files(input_storage_path, files_to_upload)

        # Step 3: Start the job
        if progress_callback:
            progress_callback("Starting job...")
        logger.info(f"Starting job with job_id: {job_id}")
        job_start_response = await self.start_job(job_id)
        if not job_start_response:
            logger.error("Failed to start job")
            if progress_callback:
                progress_callback("Failed to start job")
            return

        # Step 4: Monitor job status
        logger.info("Monitoring job status...")
        attempt = 1
        status = None
        while True:
            logger.info(f"Status check attempt {attempt}")
            job_status = await self.check_job_status(job_id)
            if not job_status:
                logger.error("Failed to get job status")
                if progress_callback:
                    progress_callback("Failed to get job status")
                break
            status = job_status["job_state"]
            logger.info(f"Current job status: {status}")
            if progress_callback:
                progress_callback(f"Job status: {status}")
            if status == "Completed":
                logger.info("Job completed successfully!")
                break
            elif status == "Failed":
                logger.error("Job failed!")
                break
            else:
                logger.info(f"Current status: {status}")
                await asyncio.sleep(10)
            attempt += 1

        # Step 5: Download results
        if status == "Completed":
            if progress_callback:
                progress_callback("Downloading results...")
            logger.info(f"Downloading results from: {output_storage_path}")
            files = await self.list_files(output_storage_path)
            os.makedirs(destination_dir, exist_ok=True)
            await self.download_files(output_storage_path, files, destination_dir)
            logger.info(f"Files have been downloaded to: {destination_dir}")
            # Fetch job status again to get file_id to file_name mapping
            job_status = await self.check_job_status(job_id)
            file_id_name_map = {}
            if job_status and 'job_details' in job_status:
                for detail in job_status['job_details']:
                    file_id = str(detail.get('file_id'))
                    file_name = detail.get('file_name')
                    if file_id and file_name:
                        file_id_name_map[file_id] = file_name
            if progress_callback:
                progress_callback("Transcription complete!")
            # Post-process: convert downloaded .json transcripts to .txt with correct names
            self._convert_json_transcripts_to_txt(destination_dir, file_id_name_map)

    def _convert_json_transcripts_to_txt(self, directory, file_id_name_map=None):
        """
        For each .json file in the directory, extract the 'transcript' key and save as a .txt file named after the original audio file.
        """
        for filename in os.listdir(directory):
            if filename.endswith('.json'):
                json_path = os.path.join(directory, filename)
                file_id = os.path.splitext(filename)[0]
                # Default to file_id.txt if mapping not found
                base_name = file_id_name_map.get(file_id) if file_id_name_map else None
                if base_name:
                    base_name = os.path.splitext(base_name)[0]  # Remove extension
                    txt_path = os.path.join(directory, base_name + '.txt')
                else:
                    txt_path = os.path.join(directory, file_id + '.txt')
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    transcript = data.get('transcript')
                    if transcript:
                        with open(txt_path, 'w', encoding='utf-8') as f:
                            f.write(transcript)
                        logger.info(f"Extracted transcript to {txt_path}")
                        os.remove(json_path)
                        logger.info(f"Deleted original JSON file: {json_path}")
                    else:
                        logger.warning(f"No 'transcript' key found in {json_path}")
                except Exception as e:
                    logger.error(f"Failed to convert {json_path} to txt: {e}")
