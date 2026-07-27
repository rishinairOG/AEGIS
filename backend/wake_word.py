"""
Offline wake-word listener for ATLAS.

Uses openWakeWord (fully offline, no account/API key) with the built-in
"hey_jarvis" model — a natural fit for this J.A.R.V.I.S.-style assistant and,
unlike a custom "Atlas" word, available pretrained.

Runs the mic read + inference loop in a daemon thread (PyAudio reads block).
On detection it calls on_detect(model_name, score) FROM THAT THREAD — the
caller is responsible for hopping back to its event loop if needed.

Mic coordination: pause() closes the input stream and resume() reopens it, so
the wake listener and the main AudioLoop never hold the microphone at the same
time (important on Windows / Bluetooth). The server pauses the listener before
starting a voice session and resumes it after.

Degrades safely: if openWakeWord / its models / the mic are unavailable, the
listener logs and disables itself — it never raises into the app.
"""
import threading
import time
import logging

logger = logging.getLogger("ATLAS-WAKE")

SAMPLE_RATE = 16000       # openWakeWord expects 16 kHz mono
FRAME_SAMPLES = 1280      # 80 ms per inference step
DEFAULT_THRESHOLD = 0.5
DETECT_COOLDOWN_S = 3.0   # ignore repeat detections within this window


class WakeWordListener:
    def __init__(self, on_detect, model_name="hey_jarvis", threshold=DEFAULT_THRESHOLD,
                 input_device_index=None):
        self.on_detect = on_detect
        self.model_name = model_name
        self.threshold = threshold
        self.input_device_index = input_device_index

        self._model = None
        self._pyaudio = None
        self._stream = None
        self._thread = None
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._last_detect = 0.0
        self.available = False  # set True once the model loads

    def _load_model(self):
        try:
            import openwakeword
            from openwakeword import Model
            try:
                # One-time; no-op / cached if already downloaded. Offline-safe.
                openwakeword.utils.download_models()
            except Exception as e:
                logger.warning("Wake model download skipped/failed (using cache if present): %s", e)
            self._model = Model(wakeword_models=[self.model_name], inference_framework="onnx")
            self.available = True
            logger.info("Wake-word model '%s' loaded.", self.model_name)
            return True
        except Exception as e:
            logger.warning("Wake-word disabled — could not load openWakeWord: %s", e)
            self.available = False
            return False

    def _open_stream(self):
        import pyaudio
        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()
        self._stream = self._pyaudio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=self.input_device_index,
            frames_per_buffer=FRAME_SAMPLES,
        )

    def _close_stream(self):
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def _run(self):
        import numpy as np
        while not self._stop.is_set():
            if self._paused.is_set():
                self._close_stream()
                time.sleep(0.1)
                continue

            if self._stream is None:
                try:
                    self._open_stream()
                    logger.info("Wake-word listener is now listening for '%s'.", self.model_name)
                except Exception as e:
                    logger.warning("Could not open mic for wake word (will retry): %s", e)
                    time.sleep(1.0)
                    continue

            try:
                data = self._stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                frame = np.frombuffer(data, dtype=np.int16)
                scores = self._model.predict(frame)
                score = scores.get(self.model_name, 0.0)
                if score >= self.threshold:
                    now = time.time()
                    if now - self._last_detect > DETECT_COOLDOWN_S:
                        self._last_detect = now
                        logger.info("Wake word detected (score=%.2f).", score)
                        try:
                            self.on_detect(self.model_name, float(score))
                        except Exception as e:
                            logger.exception("Wake on_detect callback failed: %s", e)
            except Exception as e:
                logger.warning("Wake-word read/inference error: %s", e)
                self._close_stream()
                time.sleep(0.5)

        self._close_stream()

    def start(self):
        """Load the model and begin listening in a background thread. No-op if
        the model can't load (listener stays disabled)."""
        if self._thread and self._thread.is_alive():
            return
        if not self._load_model():
            return
        self._stop.clear()
        self._paused.clear()
        self._thread = threading.Thread(target=self._run, name="WakeWordListener", daemon=True)
        self._thread.start()

    def pause(self):
        """Release the mic (so the voice session can use it)."""
        self._paused.set()

    def resume(self):
        """Resume listening after a session ends."""
        if self.available:
            self._paused.clear()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._pyaudio is not None:
            try:
                self._pyaudio.terminate()
            except Exception:
                pass
            self._pyaudio = None
