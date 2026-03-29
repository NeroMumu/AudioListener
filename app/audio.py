from __future__ import annotations

import math

import numpy as np


def unpack_audio_message(payload: bytes) -> tuple[int, np.ndarray]:
    if len(payload) < 6:
        return 0, np.array([], dtype=np.float32)

    sample_rate = int.from_bytes(payload[:4], byteorder="little", signed=False)
    samples = np.frombuffer(payload[4:], dtype="<i2").astype(np.float32) / 32768.0
    return sample_rate, samples


def resample_audio(samples: np.ndarray, original_rate: int, target_rate: int) -> np.ndarray:
    if original_rate <= 0 or samples.size == 0:
        return np.array([], dtype=np.float32)

    if original_rate == target_rate:
        return samples.astype(np.float32)

    target_length = max(1, int(math.ceil(samples.size * target_rate / original_rate)))
    current_positions = np.linspace(0.0, 1.0, num=samples.size, dtype=np.float32)
    target_positions = np.linspace(0.0, 1.0, num=target_length, dtype=np.float32)
    return np.interp(target_positions, current_positions, samples).astype(np.float32)


def rms_level(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples), dtype=np.float64)))
