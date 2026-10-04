import subprocess
from threading import Lock

from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from resources.errors import ServiceUnavailableError


def levenshtein_distance(first, second):
    if len(first) < len(second):
        first, second = second, first
    previous = list(range(len(second) + 1))
    for i, character in enumerate(first):
        current = [i + 1]
        for j, other in enumerate(second):
            current.append(min(current[j] + 1, previous[j + 1] + 1, previous[j] + (character != other)))
        previous = current
    return previous[-1]


def score_speech(expected, actual):
    length = max(len(expected), len(actual))
    if not length:
        return 0
    similarity = (length - levenshtein_distance(expected, actual)) / length
    return int(similarity * 10 * len(expected.split()))


class WhisperTranscriber:
    def __init__(self):
        self._model = None
        self._lock = Lock()

    def __call__(self, path, max_seconds):
        if not self._lock.acquire(blocking=False):
            raise ServiceUnavailableError("Transcription is busy; retry later")
        try:
            import numpy as np
            import whisper

            try:
                audio = subprocess.run(
                    [
                        "ffmpeg", "-nostdin", "-v", "error", "-threads", "1",
                        "-i", str(path), "-t", str(max_seconds + 1),
                        "-f", "f32le", "-ac", "1", "-ar", "16000", "pipe:1",
                    ],
                    capture_output=True,
                    check=True,
                    timeout=30,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                raise BadRequest("Audio could not be decoded within the time limit") from error
            samples = np.frombuffer(audio.stdout, dtype=np.float32)
            if len(samples) == 0:
                raise BadRequest("Audio is empty")
            if len(samples) > max_seconds * 16000:
                raise RequestEntityTooLarge("Audio exceeds the duration limit")
            if self._model is None:
                self._model = whisper.load_model("tiny")
            return self._model.transcribe(samples, fp16=False)["text"]
        finally:
            self._lock.release()
