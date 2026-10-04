import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from resources.errors import ServiceUnavailableError
from services.speech_service import WhisperTranscriber


@pytest.fixture
def inference(monkeypatch):
    samples = [0.0] * 100
    numpy = SimpleNamespace(float32="float32", frombuffer=Mock(return_value=samples))
    model = Mock()
    model.transcribe.return_value = {"text": "hello"}
    whisper = SimpleNamespace(load_model=Mock(return_value=model))
    monkeypatch.setitem(sys.modules, "numpy", numpy)
    monkeypatch.setitem(sys.modules, "whisper", whisper)
    decode = Mock(return_value=SimpleNamespace(stdout=b"audio"))
    monkeypatch.setattr("services.speech_service.subprocess.run", decode)
    return numpy, whisper, decode


def test_transcriber_loads_model_once_and_bounds_decoding(inference):
    _, whisper, decode = inference
    transcriber = WhisperTranscriber()
    assert transcriber("file.wav", 120) == "hello"
    assert transcriber("other.wav", 120) == "hello"
    whisper.load_model.assert_called_once_with("tiny")
    args = decode.call_args.args[0]
    assert args[args.index("-t") + 1] == "121"
    assert "-nostdin" in args
    assert decode.call_args.kwargs["timeout"] == 30


@pytest.mark.parametrize("size,error", [(0, BadRequest), (16001, RequestEntityTooLarge)])
def test_invalid_audio_is_rejected_before_model_loading(inference, size, error):
    numpy, whisper, _ = inference
    numpy.frombuffer.return_value = [0.0] * size
    with pytest.raises(error):
        WhisperTranscriber()("file.wav", 1)
    whisper.load_model.assert_not_called()


@pytest.mark.parametrize("error", [
    subprocess.TimeoutExpired("ffmpeg", 30), subprocess.CalledProcessError(1, "ffmpeg"),
])
def test_decode_failure_releases_transcription_lock(inference, error):
    _, _, decode = inference
    decode.side_effect = error
    transcriber = WhisperTranscriber()
    with pytest.raises(BadRequest):
        transcriber("file.wav", 120)
    decode.side_effect = None
    assert transcriber("file.wav", 120) == "hello"


def test_busy_worker_rejects_instead_of_queueing(inference):
    transcriber = WhisperTranscriber()
    transcriber._lock.acquire()
    try:
        with pytest.raises(ServiceUnavailableError):
            transcriber("file.wav", 120)
    finally:
        transcriber._lock.release()


def test_model_load_failure_is_retryable(inference):
    _, whisper, _ = inference
    transcriber = WhisperTranscriber()
    whisper.load_model.side_effect = RuntimeError("model unavailable")
    with pytest.raises(RuntimeError):
        transcriber("file.wav", 120)
    whisper.load_model.side_effect = None
    assert transcriber("file.wav", 120) == "hello"
