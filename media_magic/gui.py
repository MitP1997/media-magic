import tkinter as tk
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
        top_label = ttk.Label(self.root, text='Welcome to Media Magic!', font=('Arial', 14, 'bold'))
        top_label.pack(pady=5)

    def _setup_tabs(self):
        self.tab_control = ttk.Notebook(self.root)
        self.video_tab = ttk.Frame(self.tab_control)
        self.audio_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.video_tab, text='Video Magic')
        self.tab_control.add(self.audio_tab, text='Audio Magic')
        self.tab_control.pack(expand=1, fill='both')
        self.tab_control.select(self.audio_tab)  # Set Audio Magic as default tab

    def _setup_audio_tab(self):
        # Audio Magic Tab
        self.audio_file_path = tk.StringVar()
        self.audio_file_path.trace_add('write', self.on_audio_file_selected)

        self.select_btn = ttk.Button(self.audio_tab, text='Select Audio File', command=self.select_audio_file)
        self.select_btn.pack(pady=10)
        self.file_label = ttk.Label(self.audio_tab, textvariable=self.audio_file_path)
        self.file_label.pack(pady=5)

        # Progress label
        self.progress_var = tk.StringVar(value='')
        self.progress_label = ttk.Label(self.audio_tab, textvariable=self.progress_var, foreground='blue')
        self.progress_label.pack(pady=5)

        # Start/End time widgets
        self.start_time_vars = [tk.IntVar(value=0) for _ in range(3)]  # hours, min, sec
        self.end_time_vars = [tk.IntVar(value=0) for _ in range(3)]    # hours, min, sec

        time_frame = ttk.Frame(self.audio_tab)
        time_frame.pack(pady=5)

        # Start time
        ttk.Label(time_frame, text='Start Time:').grid(row=0, column=0, padx=2)
        self.start_hour_entry = ttk.Entry(time_frame, width=3, textvariable=self.start_time_vars[0], state='disabled')
        self.start_hour_entry.grid(row=0, column=1)
        ttk.Label(time_frame, text='hr').grid(row=0, column=2)
        self.start_min_entry = ttk.Entry(time_frame, width=3, textvariable=self.start_time_vars[1], state='disabled')
        self.start_min_entry.grid(row=0, column=3)
        ttk.Label(time_frame, text='min').grid(row=0, column=4)
        self.start_sec_entry = ttk.Entry(time_frame, width=3, textvariable=self.start_time_vars[2], state='disabled')
        self.start_sec_entry.grid(row=0, column=5)
        ttk.Label(time_frame, text='sec').grid(row=0, column=6)

        # End time
        ttk.Label(time_frame, text='End Time:').grid(row=1, column=0, padx=2)
        self.end_hour_entry = ttk.Entry(time_frame, width=3, textvariable=self.end_time_vars[0], state='disabled')
        self.end_hour_entry.grid(row=1, column=1)
        ttk.Label(time_frame, text='hr').grid(row=1, column=2)
        self.end_min_entry = ttk.Entry(time_frame, width=3, textvariable=self.end_time_vars[1], state='disabled')
        self.end_min_entry.grid(row=1, column=3)
        ttk.Label(time_frame, text='min').grid(row=1, column=4)
        self.end_sec_entry = ttk.Entry(time_frame, width=3, textvariable=self.end_time_vars[2], state='disabled')
        self.end_sec_entry.grid(row=1, column=5)
        ttk.Label(time_frame, text='sec').grid(row=1, column=6)

        self.transcribe_btn = ttk.Button(self.audio_tab, text='Transcribe', command=self.transcribe_audio, state=tk.DISABLED)
        self.transcribe_btn.pack(pady=10)

    def _setup_video_tab(self):
        # Video Magic Tab (placeholder)
        self.video_label = ttk.Label(self.video_tab, text='Video Magic features coming soon!')
        self.video_label.pack(pady=20)

    def on_audio_file_selected(self, *args):
        if self.audio_file_path.get():
            self.transcribe_btn.config(state=tk.NORMAL)
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
            self.transcribe_btn.config(state=tk.DISABLED)
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
            audio = editor.AudioFileClip(audio_path)
            trimmed = audio.subclip(start_sec, end_sec)
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            trimmed_path = os.path.join(temp_dir, f"{base_name}_trimmed_{start_sec}_{end_sec}.mp3")
            trimmed.write_audiofile(trimmed_path, logger=None)
            audio.close()
        except Exception as e:
            logger.error(f'Error trimming audio: {e}')
            messagebox.showerror('Error', f'Failed to trim audio: {e}')
            return

        # Now transcribe using SarvamBatchTranscriber
        def run_transcription():
            api_key = os.getenv('SARVAM_API_KEY')
            if not api_key:
                self.root.after(0, lambda: messagebox.showerror('API Key Error', 'SARVAM_API_KEY not set in environment.'))
                return
            transcriber = SarvamBatchTranscriber(api_key, language_code='gu-IN')
            transcripts_dir = os.path.join(os.getcwd(), 'transcripts')
            os.makedirs(transcripts_dir, exist_ok=True)
            def progress_callback(status):
                self.root.after(0, lambda: self.progress_var.set(status))
            async def do_transcribe():
                try:
                    await transcriber.transcribe_batch([trimmed_path], transcripts_dir, progress_callback=progress_callback)
                    self.root.after(0, lambda: messagebox.showinfo('Transcription Complete', f'Transcription complete! Check the transcripts directory.'))
                except Exception as e:
                    logger.error(f'Transcription failed: {e}')
                    self.root.after(0, lambda e=e: messagebox.showerror('Transcription Error', f'Transcription failed: {e}'))
                finally:
                    try:
                        if os.path.exists(trimmed_path):
                            os.remove(trimmed_path)
                            logger.info(f"Deleted temporary file: {trimmed_path}")
                    except Exception as cleanup_err:
                        logger.error(f"Failed to delete temporary file {trimmed_path}: {cleanup_err}")
            asyncio.run(do_transcribe())
        threading.Thread(target=run_transcription, daemon=True).start()

def launch_gui():
    try:
        root = tk.Tk()
        app = MediaMagicGUI(root)
        # Bring window to foreground and focus
        root.lift()
        root.attributes('-topmost', True)
        root.after(100, lambda: root.attributes('-topmost', False))
        root.focus_force()
        root.mainloop()
    except Exception as e:
        logger.error('Exception in launch_gui:', exc_info=e)
