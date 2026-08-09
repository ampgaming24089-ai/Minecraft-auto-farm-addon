#!/usr/bin/env python3
"""
Synthesizes short placeholder SFX (pure Python, stdlib `wave` only - no
audio assets are pulled from anywhere external) for every custom sound
event the scripts trigger, and writes RP/sounds/sound_definitions.json.
Real hand-recorded/composed audio would replace these 1:1 by filename.
"""
import math
import os
import random
import struct
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "RP")
SR = 22050


def envelope(i, n, attack=0.05, release=0.3):
    t = i / n
    a = min(1, t / attack) if attack > 0 else 1
    r = min(1, (1 - t) / release) if release > 0 else 1
    return min(a, r)


def tone_sweep(duration, f_start, f_end, wave_shape="sine", noise=0.0, vol=0.5):
    n = int(SR * duration)
    samples = []
    phase = 0.0
    rnd = random.Random(1)
    for i in range(n):
        t = i / n
        freq = f_start + (f_end - f_start) * t
        phase += 2 * math.pi * freq / SR
        if wave_shape == "sine":
            s = math.sin(phase)
        elif wave_shape == "square":
            s = 1.0 if math.sin(phase) >= 0 else -1.0
        else:
            s = math.sin(phase)
        s = s * (1 - noise) + (rnd.uniform(-1, 1)) * noise
        s *= envelope(i, n) * vol
        samples.append(int(max(-1, min(1, s)) * 32000))
    return samples


def write_wav(name, samples):
    path = os.path.join(RP, "sounds", "hollowveil", f"{name}.wav")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", s) for s in samples))
    return f"sounds/hollowveil/{name}"


SOUND_SPECS = {
    "portal_ignite": dict(duration=1.4, f_start=120, f_end=900, wave_shape="sine", noise=0.15, vol=0.55),
    "debris_throw": dict(duration=0.2, f_start=600, f_end=300, wave_shape="square", noise=0.3, vol=0.35),
    "debris_hit": dict(duration=0.15, f_start=200, f_end=80, wave_shape="square", noise=0.5, vol=0.4),
    "imp_throw": dict(duration=0.25, f_start=800, f_end=1400, wave_shape="sine", noise=0.2, vol=0.4),
    "imp_hit": dict(duration=0.2, f_start=300, f_end=100, wave_shape="square", noise=0.4, vol=0.4),
    "banshee_scream": dict(duration=1.2, f_start=1800, f_end=300, wave_shape="sine", noise=0.25, vol=0.6),
    "widow_wail": dict(duration=1.5, f_start=1400, f_end=200, wave_shape="sine", noise=0.3, vol=0.6),
    "malacoda_buffet": dict(duration=0.8, f_start=90, f_end=45, wave_shape="square", noise=0.4, vol=0.6),
    "hollow_king_pulse": dict(duration=1.0, f_start=110, f_end=55, wave_shape="sine", noise=0.2, vol=0.55),
    "village_restore": dict(duration=1.6, f_start=440, f_end=880, wave_shape="sine", noise=0.02, vol=0.4),
}

EVENT_NAME = {
    "portal_ignite": "hollowveil.portal.ignite",
    "debris_throw": "hollowveil.debris.throw",
    "debris_hit": "hollowveil.debris.hit",
    "imp_throw": "hollowveil.imp.throw",
    "imp_hit": "hollowveil.imp.hit",
    "banshee_scream": "hollowveil.banshee.scream",
    "widow_wail": "hollowveil.widow.wail",
    "malacoda_buffet": "hollowveil.malacoda.buffet",
    "hollow_king_pulse": "hollowveil.hollow_king.pulse",
    "village_restore": "hollowveil.village.restore",
}


def run():
    import json

    defs = {"format_version": "1.14.0", "sound_definitions": {}}
    for key, spec in SOUND_SPECS.items():
        samples = tone_sweep(**spec)
        rel = write_wav(key, samples)
        defs["sound_definitions"][EVENT_NAME[key]] = {
            "category": "hostile" if key not in ("village_restore", "portal_ignite") else "ambient",
            "sounds": [rel],
        }
    with open(os.path.join(RP, "sounds", "sound_definitions.json"), "w") as f:
        json.dump(defs, f, indent=2)
    print(f"wrote {len(SOUND_SPECS)} sfx + sound_definitions.json")


if __name__ == "__main__":
    run()
