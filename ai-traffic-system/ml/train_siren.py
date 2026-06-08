"""
Siren Sound Detection - CNN Training Script
Trains a binary classifier: siren vs non-siren audio.

Dataset structure:
    dataset/audio/
        siren/       ← .wav files of ambulance sirens
        background/  ← .wav files of traffic, wind, speech
"""

import os
import sys
import numpy as np
from pathlib import Path

AUDIO_DATASET = Path(__file__).parent / "dataset" / "audio"
WEIGHTS_DIR = Path(__file__).parent / "weights"
WEIGHTS_DIR.mkdir(exist_ok=True)

SAMPLE_RATE = 22050
N_MELS = 128
HOP_LENGTH = 512
DURATION = 3  # seconds per clip
N_FRAMES = 128


def load_features(folder: Path, label: int):
    """Load audio files and extract mel-spectrogram features."""
    import librosa
    X, y = [], []
    for fpath in folder.glob("*.wav"):
        try:
            audio, _ = librosa.load(fpath, sr=SAMPLE_RATE, duration=DURATION, mono=True)
            mel = librosa.feature.melspectrogram(y=audio, sr=SAMPLE_RATE, n_mels=N_MELS, hop_length=HOP_LENGTH)
            mel_db = librosa.power_to_db(mel, ref=np.max)
            # Pad or crop
            if mel_db.shape[1] < N_FRAMES:
                mel_db = np.pad(mel_db, ((0, 0), (0, N_FRAMES - mel_db.shape[1])))
            else:
                mel_db = mel_db[:, :N_FRAMES]
            X.append(mel_db)
            y.append(label)
        except Exception as e:
            print(f"⚠️  Skipping {fpath.name}: {e}")
    return X, y


def build_model():
    """Build CNN for mel-spectrogram classification."""
    import tensorflow as tf
    from tensorflow.keras import layers, models

    inp = layers.Input(shape=(N_MELS, N_FRAMES, 1))
    x = layers.Conv2D(32, (3, 3), activation="relu", padding="same")(inp)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Conv2D(64, (3, 3), activation="relu", padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Conv2D(128, (3, 3), activation="relu", padding="same")(x)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.4)(x)
    out = layers.Dense(1, activation="sigmoid")(x)

    model = models.Model(inp, out)
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def train():
    import tensorflow as tf

    siren_dir = AUDIO_DATASET / "siren"
    background_dir = AUDIO_DATASET / "background"

    if not siren_dir.exists() or not background_dir.exists():
        print("❌ Audio dataset not found. Create dataset/audio/siren/ and dataset/audio/background/")
        sys.exit(1)

    print("📂 Loading audio features...")
    X_siren, y_siren = load_features(siren_dir, label=1)
    X_bg, y_bg = load_features(background_dir, label=0)

    X = np.array(X_siren + X_bg)[..., np.newaxis]
    y = np.array(y_siren + y_bg)

    # Shuffle
    idx = np.random.permutation(len(X))
    X, y = X[idx], y[idx]

    split = int(0.8 * len(X))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    print(f"   Siren samples: {len(X_siren)}, Background: {len(X_bg)}")
    print(f"   Train: {len(X_train)}, Val: {len(X_val)}")

    model = build_model()
    model.summary()

    callbacks = [
        tf.keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True),
        tf.keras.callbacks.ModelCheckpoint(str(WEIGHTS_DIR / "siren_cnn.h5"), save_best_only=True),
        tf.keras.callbacks.ReduceLROnPlateau(patience=5, factor=0.5),
    ]

    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=50,
        batch_size=32,
        callbacks=callbacks,
    )

    loss, acc = model.evaluate(X_val, y_val, verbose=0)
    print(f"\n✅ Siren CNN trained — Val accuracy: {acc:.4f}")
    print(f"   Weights saved: {WEIGHTS_DIR / 'siren_cnn.h5'}")


if __name__ == "__main__":
    train()
