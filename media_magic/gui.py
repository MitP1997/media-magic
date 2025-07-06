from ttkbootstrap import Style
from ttkbootstrap.constants import *
import ttkbootstrap as ttkb
from tkinter import ttk, filedialog, messagebox
from .audio_utils import is_audio_file, get_audio_duration, create_if_not_exists
from .logger import logger
import os
from moviepy import editor
from .transcriber import SarvamBatchTranscriber
import asyncio
import threading

class MediaMagicGUI:
    def __init__(self, root):
        self.root = root
        self._setup_window()
        self._setup_tabs()
        self._setup_audio_tab()
        self._setup_video_tab()

    def _setup_window(self):
        self.root.title('Media Magic')
        self.root.geometry('500x300')
        self.root.minsize(500, 300)
        # Add a top label for visibility
        top_label = ttkb.Label(self.root, text='Media Magic!', font=('Arial', 14, 'bold'), bootstyle="primary")
        top_label.pack(pady=5)

    def _setup_tabs(self):
        self.tab_control = ttkb.Notebook(self.root)
        self.video_tab = ttkb.Frame(self.tab_control)
        self.audio_tab = ttkb.Frame(self.tab_control)
        self.tab_control.add(self.video_tab, text='Video Magic')
        self.tab_control.add(self.audio_tab, text='Audio Magic')
        self.tab_control.pack(expand=1, fill='both')
        self.tab_control.select(self.audio_tab)  # Set Audio Magic as default tab

    def _setup_audio_tab(self):
        # Audio Magic Tab
        self.audio_file_path = ttkb.StringVar()
        self.audio_file_path.trace_add('write', self.on_audio_file_selected)

        self.select_btn = ttkb.Button(self.audio_tab, text='Select Audio File', command=self.select_audio_file, bootstyle="success")
        self.select_btn.pack(pady=10)
        self.file_label = ttkb.Label(self.audio_tab, textvariable=self.audio_file_path, bootstyle="info")
        self.file_label.pack(pady=5)

        # Progress label
        self.progress_var = ttkb.StringVar(value='')
        self.progress_label = ttkb.Label(self.audio_tab, textvariable=self.progress_var, bootstyle="warning")
        self.progress_label.pack(pady=5)

        # Start/End time widgets
        self.start_time_vars = [ttkb.IntVar(value=0) for _ in range(3)]  # hours, min, sec
        self.end_time_vars = [ttkb.IntVar(value=0) for _ in range(3)]    # hours, min, sec

        time_frame = ttkb.Frame(self.audio_tab)
        time_frame.pack(pady=5)

        # Start time
        ttkb.Label(time_frame, text='Start Time:').grid(row=0, column=0, padx=2)
        self.start_hour_entry = ttkb.Entry(time_frame, width=3, textvariable=self.start_time_vars[0], state='disabled')
        self.start_hour_entry.grid(row=0, column=1)
        ttkb.Label(time_frame, text='hr').grid(row=0, column=2)
        self.start_min_entry = ttkb.Entry(time_frame, width=3, textvariable=self.start_time_vars[1], state='disabled')
        self.start_min_entry.grid(row=0, column=3)
        ttkb.Label(time_frame, text='min').grid(row=0, column=4)
        self.start_sec_entry = ttkb.Entry(time_frame, width=3, textvariable=self.start_time_vars[2], state='disabled')
        self.start_sec_entry.grid(row=0, column=5)
        ttkb.Label(time_frame, text='sec').grid(row=0, column=6)

        # End time
        ttkb.Label(time_frame, text='End Time:').grid(row=1, column=0, padx=2)
        self.end_hour_entry = ttkb.Entry(time_frame, width=3, textvariable=self.end_time_vars[0], state='disabled')
        self.end_hour_entry.grid(row=1, column=1)
        ttkb.Label(time_frame, text='hr').grid(row=1, column=2)
        self.end_min_entry = ttkb.Entry(time_frame, width=3, textvariable=self.end_time_vars[1], state='disabled')
        self.end_min_entry.grid(row=1, column=3)
        ttkb.Label(time_frame, text='min').grid(row=1, column=4)
        self.end_sec_entry = ttkb.Entry(time_frame, width=3, textvariable=self.end_time_vars[2], state='disabled')
        self.end_sec_entry.grid(row=1, column=5)
        ttkb.Label(time_frame, text='sec').grid(row=1, column=6)

        self.transcribe_btn = ttkb.Button(self.audio_tab, text='Transcribe', command=self.transcribe_audio, state="disabled", bootstyle="primary")
        self.transcribe_btn.pack(pady=10)

    def _setup_video_tab(self):
        # Video Magic Tab UI
        video_frame = ttkb.Frame(self.video_tab)
        video_frame.pack(pady=10, padx=10, fill='x')

        # YouTube Link
        ttkb.Label(video_frame, text='YouTube Link:').grid(row=0, column=0, sticky='w', pady=2)
        self.youtube_link_var = ttkb.StringVar()
        self.youtube_entry = ttkb.Entry(video_frame, textvariable=self.youtube_link_var, width=40)
        self.youtube_entry.grid(row=0, column=1, columnspan=5, sticky='ew', pady=2)

        # Start/End time checkboxes and fields
        self.enforce_start_var = ttkb.BooleanVar(value=False)
        self.enforce_end_var = ttkb.BooleanVar(value=False)

        # Start time
        self.video_start_time_vars = [ttkb.IntVar(value=0) for _ in range(3)]
        ttkb.Checkbutton(video_frame, text='Enforce Start Time', variable=self.enforce_start_var, command=self._on_enforce_start_toggle, bootstyle="success").grid(row=1, column=0, sticky='w', pady=2)
        self.video_start_hour_entry = ttkb.Entry(video_frame, width=3, textvariable=self.video_start_time_vars[0], state='disabled')
        self.video_start_hour_entry.grid(row=1, column=1)
        ttkb.Label(video_frame, text='hr').grid(row=1, column=2)
        self.video_start_min_entry = ttkb.Entry(video_frame, width=3, textvariable=self.video_start_time_vars[1], state='disabled')
        self.video_start_min_entry.grid(row=1, column=3)
        ttkb.Label(video_frame, text='min').grid(row=1, column=4)
        self.video_start_sec_entry = ttkb.Entry(video_frame, width=3, textvariable=self.video_start_time_vars[2], state='disabled')
        self.video_start_sec_entry.grid(row=1, column=5)
        ttkb.Label(video_frame, text='sec').grid(row=1, column=6)

        # End time
        self.video_end_time_vars = [ttkb.IntVar(value=0) for _ in range(3)]
        ttkb.Checkbutton(video_frame, text='Enforce End Time', variable=self.enforce_end_var, command=self._on_enforce_end_toggle, bootstyle="danger").grid(row=2, column=0, sticky='w', pady=2)
        self.video_end_hour_entry = ttkb.Entry(video_frame, width=3, textvariable=self.video_end_time_vars[0], state='disabled')
        self.video_end_hour_entry.grid(row=2, column=1)
        ttkb.Label(video_frame, text='hr').grid(row=2, column=2)
        self.video_end_min_entry = ttkb.Entry(video_frame, width=3, textvariable=self.video_end_time_vars[1], state='disabled')
        self.video_end_min_entry.grid(row=2, column=3)
        ttkb.Label(video_frame, text='min').grid(row=2, column=4)
        self.video_end_sec_entry = ttkb.Entry(video_frame, width=3, textvariable=self.video_end_time_vars[2], state='disabled')
        self.video_end_sec_entry.grid(row=2, column=5)
        ttkb.Label(video_frame, text='sec').grid(row=2, column=6)

        # Transcribe button
        self.video_transcribe_btn = ttkb.Button(self.video_tab, text='Transcribe', command=self._on_video_transcribe, bootstyle="primary")
        self.video_transcribe_btn.pack(pady=15)
        # Progress label for Video Magic
        self.video_progress_label = ttkb.Label(self.video_tab, textvariable=self.progress_var, bootstyle="warning")
        self.video_progress_label.pack(pady=5)

    def on_audio_file_selected(self, *args):
        if self.audio_file_path.get():
            self.transcribe_btn.config(state=ttkb.NORMAL)
            # Enable start/end time fields
            self.start_hour_entry.config(state='normal')
            self.start_min_entry.config(state='normal')
            self.start_sec_entry.config(state='normal')
            self.end_hour_entry.config(state='normal')
            self.end_min_entry.config(state='normal')
            self.end_sec_entry.config(state='normal')
            # Set end time to audio duration
            duration = get_audio_duration(self.audio_file_path.get())
            logger.info(f"Audio duration for {self.audio_file_path.get()}: {duration} seconds")
            if duration == 0:
                messagebox.showerror('Audio Duration Error', f'Could not determine duration for file: {self.audio_file_path.get()}')
            hours = duration // 3600
            mins = (duration % 3600) // 60
            secs = duration % 60
            self.start_time_vars[0].set(0)
            self.start_time_vars[1].set(0)
            self.start_time_vars[2].set(0)
            self.end_time_vars[0].set(hours)
            self.end_time_vars[1].set(mins)
            self.end_time_vars[2].set(secs)
        else:
            self.transcribe_btn.config(state=ttkb.DISABLED)
            # Disable start/end time fields
            self.start_hour_entry.config(state='disabled')
            self.start_min_entry.config(state='disabled')
            self.start_sec_entry.config(state='disabled')
            self.end_hour_entry.config(state='disabled')
            self.end_min_entry.config(state='disabled')
            self.end_sec_entry.config(state='disabled')

    def select_audio_file(self):
        file_path = filedialog.askopenfilename(
            title='Select Audio File',
            filetypes=[('Audio Files', '*.mp3 *.wav *.aac *.flac *.ogg *.m4a')]
        )
        if file_path:
            if is_audio_file(file_path):
                self.audio_file_path.set(file_path)
            else:
                messagebox.showerror('Invalid File', 'Please select a valid audio file.')

    def transcribe_audio(self):
        # Read start and end time from GUI
        start_sec = self.start_time_vars[0].get() * 3600 + self.start_time_vars[1].get() * 60 + self.start_time_vars[2].get()
        end_sec = self.end_time_vars[0].get() * 3600 + self.end_time_vars[1].get() * 60 + self.end_time_vars[2].get()
        audio_path = self.audio_file_path.get()
        if not audio_path or end_sec <= start_sec:
            messagebox.showerror('Invalid Time', 'Please ensure start time is less than end time and a file is selected.')
            return
        # Create temp folder
        temp_dir = os.path.join(os.getcwd(), 'temp')
        create_if_not_exists(temp_dir)
        # Trim audio
        try:
            self.progress_var.set('Trimming audio...')
            audio = editor.AudioFileClip(audio_path)
            trimmed = audio.subclip(start_sec, end_sec)
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            trimmed_path = os.path.join(temp_dir, f"{base_name}_trimmed_{start_sec}_{end_sec}.mp3")
            trimmed.write_audiofile(trimmed_path, logger=None)
            audio.close()
        except Exception as e:
            logger.error(f'Error trimming audio: {e}')
            self.progress_var.set('Error during trimming.')
            messagebox.showerror('Error', f'Failed to trim audio: {e}')
            return

        # Now transcribe using SarvamBatchTranscriber
        def run_transcription():
            api_key = os.getenv('SARVAM_API_KEY')
            if not api_key:
                self.root.after(0, lambda: messagebox.showerror('API Key Error', 'SARVAM_API_KEY not set in environment.'))
                self.root.after(0, lambda: self.progress_var.set(''))
                return
            transcriber = SarvamBatchTranscriber(api_key, language_code='gu-IN')
            transcripts_dir = os.path.join(os.getcwd(), 'transcripts')
            os.makedirs(transcripts_dir, exist_ok=True)
            def progress_callback(status):
                self.root.after(0, lambda: self.progress_var.set(f'Transcribing: {status}'))
            async def do_transcribe():
                try:
                    await transcriber.transcribe_batch([trimmed_path], transcripts_dir, progress_callback=progress_callback)
                    self.root.after(0, lambda: self.progress_var.set('Done!'))
                    self.root.after(0, lambda: messagebox.showinfo('Transcription Complete', f'Transcription complete! Check the transcripts directory.'))
                except Exception as e:
                    logger.error(f'Transcription failed: {e}')
                    self.root.after(0, lambda: self.progress_var.set('Error during transcription.'))
                    self.root.after(0, lambda: messagebox.showerror('Transcription Error', f'Transcription failed: {e}'))
                finally:
                    try:
                        if os.path.exists(trimmed_path):
                            os.remove(trimmed_path)
                            logger.info(f"Deleted temporary file: {trimmed_path}")
                    except Exception as cleanup_err:
                        logger.error(f"Failed to delete temporary file {trimmed_path}: {cleanup_err}")
            asyncio.run(do_transcribe())
        threading.Thread(target=run_transcription, daemon=True).start()

    def _on_enforce_start_toggle(self):
        state = 'normal' if self.enforce_start_var.get() else 'disabled'
        self.video_start_hour_entry.config(state=state)
        self.video_start_min_entry.config(state=state)
        self.video_start_sec_entry.config(state=state)

    def _on_enforce_end_toggle(self):
        state = 'normal' if self.enforce_end_var.get() else 'disabled'
        self.video_end_hour_entry.config(state=state)
        self.video_end_min_entry.config(state=state)
        self.video_end_sec_entry.config(state=state)

    def _on_video_transcribe(self):
        def run_video_transcription():
            link = self.youtube_link_var.get().strip()
            if not link:
                self.root.after(0, lambda: messagebox.showerror('Missing Link', 'Please enter a YouTube link.'))
                return
            self.root.after(0, lambda: self.progress_var.set('Downloading video...'))
            import tempfile
            import shutil
            from pytubefix import YouTube
            import traceback
            temp_dir = os.path.join(os.getcwd(), 'temp')
            create_if_not_exists(temp_dir)
            video_path = None
            audio_path = None
            trimmed_audio_path = None
            try:
                # Download video
                yt = YouTube(link, 'TV')
                stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                if not stream:
                    raise Exception('No suitable video stream found.')
                video_path = stream.download(output_path=temp_dir)
                # Check if file exists and is not empty
                if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
                    raise Exception('Downloaded video file is missing or empty.')
                # Try to load video file
                try:
                    video_clip = editor.VideoFileClip(video_path)
                except Exception as e:
                    raise Exception(f'Failed to load video file: {e}')
                self.root.after(0, lambda: self.progress_var.set('Converting to audio...'))
                # Convert to audio
                base_name = os.path.splitext(os.path.basename(video_path))[0]
                audio_path = os.path.join(temp_dir, f"{base_name}.mp3")
                video_clip.audio.write_audiofile(audio_path, logger=None)
                video_clip.close()

                # Check for start/end enforcement
                enforce_start = self.enforce_start_var.get()
                enforce_end = self.enforce_end_var.get()
                start_sec = 0
                end_sec = None
                if enforce_start:
                    start_sec = self.video_start_time_vars[0].get() * 3600 + self.video_start_time_vars[1].get() * 60 + self.video_start_time_vars[2].get()
                if enforce_end:
                    end_sec = self.video_end_time_vars[0].get() * 3600 + self.video_end_time_vars[1].get() * 60 + self.video_end_time_vars[2].get()
                # Only trim if either is enforced
                if enforce_start or enforce_end:
                    self.root.after(0, lambda: self.progress_var.set('Trimming audio...'))
                    from moviepy.editor import AudioFileClip
                    audio_clip = AudioFileClip(audio_path)
                    duration = audio_clip.duration
                    if end_sec is None or end_sec > duration:
                        end_sec = duration
                    if start_sec >= end_sec:
                        audio_clip.close()
                        raise Exception('Start time must be less than end time.')
                    trimmed_audio_path = os.path.join(temp_dir, f"{base_name}_trimmed_{int(start_sec)}_{int(end_sec)}.mp3")
                    trimmed_clip = audio_clip.subclip(start_sec, end_sec)
                    trimmed_clip.write_audiofile(trimmed_audio_path, logger=None)
                    audio_clip.close()
                    trimmed_clip.close()
                    audio_to_transcribe = trimmed_audio_path
                else:
                    audio_to_transcribe = audio_path

                self.root.after(0, lambda: self.progress_var.set('Transcribing audio...'))
                # Transcribe using SarvamBatchTranscriber (reuse logic from audio tab)
                api_key = os.getenv('SARVAM_API_KEY')
                if not api_key:
                    self.root.after(0, lambda: messagebox.showerror('API Key Error', 'SARVAM_API_KEY not set in environment.'))
                    self.root.after(0, lambda: self.progress_var.set(''))
                    return
                transcriber = SarvamBatchTranscriber(api_key, language_code='gu-IN')
                transcripts_dir = os.path.join(os.getcwd(), 'transcripts')
                os.makedirs(transcripts_dir, exist_ok=True)
                def progress_callback(status):
                    self.root.after(0, lambda: self.progress_var.set(f'Transcribing: {status}'))
                async def do_transcribe():
                    try:
                        await transcriber.transcribe_batch([audio_to_transcribe], transcripts_dir, progress_callback=progress_callback)
                        self.root.after(0, lambda: self.progress_var.set('Done!'))
                        self.root.after(0, lambda: messagebox.showinfo('Transcription Complete', f'Transcription complete! Check the transcripts directory.'))
                    except Exception as e:
                        logger.error(f'Transcription failed: {e}\n{traceback.format_exc()}')
                        self.root.after(0, lambda e=e: messagebox.showerror('Transcription Error', f'Transcription failed: {e}'))
                        self.root.after(0, lambda: self.progress_var.set('Error during transcription.'))
                    finally:
                        # Clean up temp files
                        for f in [video_path, audio_path, trimmed_audio_path]:
                            try:
                                if f and os.path.exists(f):
                                    os.remove(f)
                                    logger.info(f"Deleted temporary file: {f}")
                            except Exception as cleanup_err:
                                logger.error(f"Failed to delete temporary file {f}: {cleanup_err}")
                asyncio.run(do_transcribe())
            except Exception as e:
                logger.error(f'Video transcription error: {e}\n{traceback.format_exc()}')
                self.root.after(0, lambda: messagebox.showerror('Error', f'Failed: {e}'))
                self.root.after(0, lambda: self.progress_var.set('Error during processing.'))
                # Clean up temp files if any
                for f in [video_path, audio_path, trimmed_audio_path]:
                    try:
                        if f and os.path.exists(f):
                            os.remove(f)
                            logger.info(f"Deleted temporary file: {f}")
                    except Exception as cleanup_err:
                        logger.error(f"Failed to delete temporary file {f}: {cleanup_err}")
        threading.Thread(target=run_video_transcription, daemon=True).start()

def launch_gui():
    try:
        style = Style(theme="pulse")
        root = style.master
        app = MediaMagicGUI(root)
        # Bring window to foreground and focus
        root.lift()
        root.attributes('-topmost', True)
        root.after(100, lambda: root.attributes('-topmost', False))
        root.focus_force()
        root.mainloop()
    except Exception as e:
        logger.error('Exception in launch_gui:', exc_info=e)
