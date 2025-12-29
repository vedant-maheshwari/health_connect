
import os
import io
import numpy as np
import wfdb
import tempfile
import keras
from scipy.signal import butter, sosfilt, medfilt, stft

# Constants from code.ipynb
FS = 125
WINDOW_SIZE_SECONDS = 15
WINDOW_SIZE_SAMPLES = WINDOW_SIZE_SECONDS * FS
OVERLAP_RATIO = 0.5
NPERSEG = 256
NOVERLAP = 128
EPS = 1e-8
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "AF_classification_model.keras")

_model = None

def get_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
        _model = keras.saving.load_model(MODEL_PATH)
        print("✅ BSP Model loaded successfully")
    return _model

def bandpass_filter(signal, lowcut, highcut, fs, order=4):
    sos = butter(order, [lowcut, highcut], btype="band", fs=fs, output="sos")
    return sosfilt(sos, signal)

def preprocess_signal(sig, sig_type='PPG'):
    sig = medfilt(sig, kernel_size=5)
    if sig_type == 'PPG':
        low, high = 0.5, 8.0
    else:  # ECG
        low, high = 0.5, 40.0
    sig = bandpass_filter(sig, low, high, FS)
    std = np.std(sig)
    if std == 0:
        std = 1e-6
    return (sig - np.mean(sig)) / std

def segment_signal(signal):
    step = int(WINDOW_SIZE_SAMPLES * (1 - OVERLAP_RATIO))
    segs = []
    if len(signal) < WINDOW_SIZE_SAMPLES:
        return np.array([])
        
    for start in range(0, len(signal) - int(WINDOW_SIZE_SAMPLES) + 1, step):
        segs.append(signal[start:start + int(WINDOW_SIZE_SAMPLES)])
    return np.array(segs)

def compute_log_stft(sig):
    f, t, Zxx = stft(sig, fs=FS, nperseg=NPERSEG, noverlap=NOVERLAP, boundary=None)
    return np.log1p(np.abs(Zxx) + EPS).astype(np.float32)

import os
import tempfile
import numpy as np
import wfdb

def process_record_files(header_content: bytes, dat_content: bytes):
    """
    Process uploaded WFDB record files.
    header_content: bytes of .hea file
    dat_content: bytes of .dat file
    """

    with tempfile.TemporaryDirectory() as temp_dir:

        # -------------------------------
        # Decode header
        # -------------------------------
        try:
            header_str = header_content.decode("utf-8")
        except UnicodeDecodeError:
            header_str = header_content.decode("latin-1")

        lines = header_str.splitlines()
        if not lines:
            raise ValueError("Empty header file")

        # -------------------------------
        # Parse record name
        # -------------------------------
        first_line_parts = lines[0].split()
        if not first_line_parts:
            raise ValueError("Invalid header format")

        record_name = first_line_parts[0]

        # -------------------------------
        # Parse expected .dat filename
        # -------------------------------
        dat_filename = None

        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if not parts:
                continue

            fn = parts[0]
            if fn != "~":
                dat_filename = os.path.basename(fn)  # 🔥 CRITICAL FIX
                break

        if not dat_filename:
            dat_filename = record_name + ".dat"

        print(f"BSP: Record name = {record_name}")
        print(f"BSP: Expected dat file = {dat_filename}")

        # -------------------------------
        # Write files
        # -------------------------------
        hea_path = os.path.join(temp_dir, record_name + ".hea")
        dat_path = os.path.join(temp_dir, dat_filename)

        with open(hea_path, "wb") as f:
            f.write(header_content)

        with open(dat_path, "wb") as f:
            f.write(dat_content)

        print("BSP: Temp dir contents:", os.listdir(temp_dir))

        # -------------------------------
        # Read WFDB record
        # -------------------------------
        try:
            rec = wfdb.rdrecord(os.path.join(temp_dir, record_name))
        except Exception as e:
            raise ValueError(
                f"Failed to read WFDB record: {e}. "
                f"Ensure .hea and .dat filenames match."
            )

        if rec.p_signal is None:
            raise ValueError("Record contains no signal data")

        if rec.p_signal.shape[1] < 2:
            raise ValueError(
                f"Expected at least 2 channels (PPG, ECG), got {rec.p_signal.shape[1]}"
            )

        # -------------------------------
        # Extract signals
        # -------------------------------
        ppg_raw = rec.p_signal[:, 0]
        ecg_raw = rec.p_signal[:, 1]

        print(f"BSP: PPG length={len(ppg_raw)}, ECG length={len(ecg_raw)}")

        # -------------------------------
        # Preprocessing
        # -------------------------------
        ppg_proc = preprocess_signal(ppg_raw, "PPG")
        ecg_proc = preprocess_signal(ecg_raw, "ECG")

        p_segs = segment_signal(ppg_proc)
        e_segs = segment_signal(ecg_proc)

        if len(p_segs) == 0:
            raise ValueError("Signal too short for segmentation")

        # Ensure equal number of segments
        min_len = min(len(p_segs), len(e_segs))
        p_segs = p_segs[:min_len]
        e_segs = e_segs[:min_len]

        specs = []

        # -------------------------------
        # STFT → Model input
        # -------------------------------
        target_freq = 129
        target_time = 14

        for ps, es in zip(p_segs, e_segs):
            p_spec = compute_log_stft(ps)
            e_spec = compute_log_stft(es)

            if p_spec.shape[1] < target_time or e_spec.shape[1] < target_time:
                continue

            spec = np.stack(
                [
                    p_spec[:target_freq, :target_time],
                    e_spec[:target_freq, :target_time],
                ],
                axis=-1,
            )

            if not np.isnan(spec).any():
                specs.append(spec)

        if not specs:
            raise ValueError("No valid segments after preprocessing")

        X = np.array(specs, dtype=np.float32)

        # -------------------------------
        # Prediction
        # -------------------------------
        model = get_model()
        preds = model.predict(X, verbose=0)

        af_prob = float(np.mean(preds))
        is_af = af_prob > 0.5

        print(f"BSP: AF probability = {af_prob:.4f}")

        return {
            "classification": "Atrial Fibrillation Detected"
            if is_af
            else "Normal Rhythm",
            "confidence": af_prob if is_af else (1.0 - af_prob),
            "af_probability": af_prob,
            "segments_processed": len(specs),
            "af_segments_count": int(np.sum(preds > 0.5)),
        }
