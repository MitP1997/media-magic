# Transcription configuration working best
```python
model = WhisperModel("large-v2", device="cuda", compute_type="float16")
segments, _ = model.transcribe(
    audio_file,
    language="gu",
    word_timestamps=True,
    vad_filter=True,
    vad_parameters={"threshold": 0.5}
)
```
