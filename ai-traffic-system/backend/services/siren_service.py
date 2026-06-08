"""
Siren Sound Detection Service
Uses Librosa + trained CNN to classify ambulance siren audio.
"""

import io
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)
MODEL_PATH = Path(__file__).parent.parent / "ml" / "weights" / "siren_cnn.h5"

SAMPLE_RATE = 22050
N_MELS = 128
HOP_LENGTH = 512
SIREN_THRESHOLD = 0.70


class SirenDetectionService:
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self._load_model()

    def _load_model(self):
        try:
            import tensorflow as tf
            if MODEL_PATH.exists():
                self.model = tf.keras.models.load_model(str(MODEL_PATH))
                self.model_loaded = True
                logger.info("✅ Siren CNN model loaded")
            else:
                logger.warning("⚠️  Siren model weights not found. Train first with ml/train_siren.py")
        except Exception as e:
            logger.error(f"Siren model load failed: {e}")

    def extract_features(self, audio_bytes: bytes) -> np.ndarray:
        """Extract mel-spectrogram features from raw audio bytes."""
        import librosa
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=SAMPLE_RATE, mono=True)
        mel = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=N_MELS, hop_length=HOP_LENGTH)
        mel_db = librosa.power_to_db(mel, ref=np.max)
        # Pad or crop to fixed size
        target_frames = 128
        if mel_db.shape[1] < target_frames:
            mel_db = np.pad(mel_db, ((0, 0), (0, target_frames - mel_db.shape[1])))
        else:
            mel_db = mel_db[:, :target_frames]
        return mel_db

    def predict(self, audio_bytes: bytes) -> dict:
        """
        Returns: {"siren_detected": bool, "confidence": float}
        """
        if not self.model_loaded:
            return {"siren_detected": False, "confidence": 0.0, "error": "Model not loaded"}

        try:
            features = self.extract_features(audio_bytes)
            features = features[np.newaxis, ..., np.newaxis]  # (1, 128, 128, 1)
            prob = float(self.model.predict(features, verbose=0)[0][0])
            return {
                "siren_detected": prob >= SIREN_THRESHOLD,
                "confidence": round(prob, 4),
            }
        except Exception as e:
            logger.error(f"Siren prediction failed: {e}")
            return {"siren_detected": False, "confidence": 0.0, "error": str(e)}

    def realtime_monitor(self, duration_seconds: int = 5) -> dict:
        """
        Record audio from default mic and classify.
        Requires pyaudio: pip install pyaudio
        """
        try:
            import pyaudio
            import soundfile as sf

            CHUNK = 1024
            FORMAT = pyaudio.paFloat32
            CHANNELS = 1

            p = pyaudio.PyAudio()
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE, input=True, frames_per_buffer=CHUNK)

            frames = []
            for _ in range(0, int(SAMPLE_RATE / CHUNK * duration_seconds)):
                data = stream.read(CHUNK)
                frames.append(np.frombuffer(data, dtype=np.float32))

            stream.stop_stream()
            stream.close()
            p.terminate()

            audio = np.concatenate(frames)
            buf = io.BytesIO()
            sf.write(buf, audio, SAMPLE_RATE, format="WAV")
            return self.predict(buf.getvalue())

        except ImportError:
            return {"siren_detected": False, "confidence": 0.0, "error": "pyaudio not installed"}
        except Exception as e:
            return {"siren_detected": False, "confidence": 0.0, "error": str(e)}
