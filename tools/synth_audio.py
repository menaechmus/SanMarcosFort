"""Synthesize the game's sound effects (WAV, mono, 16-bit) from scratch.

Everything is generated procedurally (noise, filters, oscillators), so the sounds are
license-free and reproducible. Standard library only:
    python -I tools/synth_audio.py            -> assets/audio/*.wav
"""

import math
import random
import struct
import wave
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT / "assets" / "audio"
SR = 32000
TAU = 2 * math.pi


# --- Building blocks ----------------------------------------------------------------------

def silence(seconds):
    return [0.0] * int(seconds * SR)


def noise(rng, seconds):
    return [rng.uniform(-1.0, 1.0) for _ in range(int(seconds * SR))]


def lowpass(signal, cutoff):
    """One-pole lowpass; `cutoff` may be a number or a function of time (s)."""
    out, y = [], 0.0
    for i, x in enumerate(signal):
        fc = cutoff(i / SR) if callable(cutoff) else cutoff
        a = 1.0 - math.exp(-TAU * fc / SR)
        y += a * (x - y)
        out.append(y)
    return out


def highpass(signal, cutoff):
    low = lowpass(signal, cutoff)
    return [x - l for x, l in zip(signal, low)]


def bandpass(signal, center, q=2.0):
    """Resonant two-pole bandpass (RBJ biquad); `center` may be a function of time."""
    out = []
    x1 = x2 = y1 = y2 = 0.0
    for i, x in enumerate(signal):
        fc = center(i / SR) if callable(center) else center
        w = TAU * fc / SR
        alpha = math.sin(w) / (2 * q)
        b0, b2 = alpha, -alpha
        a0, a1, a2 = 1 + alpha, -2 * math.cos(w), 1 - alpha
        y = (b0 * x + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1, y2, y1 = x1, x, y1, y
        out.append(y)
    return out


def envelope(signal, attack, decay, hold=0.0):
    out = []
    for i, x in enumerate(signal):
        t = i / SR
        if t < attack:
            g = t / attack
        elif t < attack + hold:
            g = 1.0
        else:
            g = math.exp(-(t - attack - hold) / decay)
        out.append(x * g)
    return out


def sine(seconds, freq, phase=0.0):
    """Sine whose frequency may be a function of time (phase is integrated)."""
    out, ph = [], phase
    for i in range(int(seconds * SR)):
        f = freq(i / SR) if callable(freq) else freq
        ph += TAU * f / SR
        out.append(math.sin(ph))
    return out


def mix(*tracks):
    length = max(len(t) for t, _ in tracks)
    out = [0.0] * length
    for track, gain in tracks:
        for i, x in enumerate(track):
            out[i] += x * gain
    return out


def place(track, offset_s, length_s):
    out = [0.0] * int(length_s * SR)
    start = int(offset_s * SR)
    for i, x in enumerate(track):
        if start + i < len(out):
            out[start + i] += x
    return out


def normalize(signal, peak=0.92, drive=0.0):
    if drive > 0:
        signal = [math.tanh(x * (1 + drive)) for x in signal]
    top = max(abs(x) for x in signal) or 1.0
    return [x * peak / top for x in signal]


def fade(signal, fade_in=0.002, fade_out=0.05):
    n_in, n_out = int(fade_in * SR), int(fade_out * SR)
    out = list(signal)
    for i in range(min(n_in, len(out))):
        out[i] *= i / n_in
    for i in range(min(n_out, len(out))):
        out[-1 - i] *= i / n_out
    return out


def loop_crossfade(signal, seconds):
    """Make a seamless loop: the tail is crossfaded into the head."""
    n = int(seconds * SR)
    body = signal[:-n]
    tail = signal[-n:]
    for i in range(n):
        w = i / n
        body[i] = body[i] * w + tail[i] * (1 - w)
    return body


def save(name, signal):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.wav"
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, x)) * 32767)) for x in signal))
    print(f"{path.relative_to(PROJECT)}  {len(signal) / SR:.1f} s")


# --- Sounds ------------------------------------------------------------------------------

def cannon(rng, distant=False):
    length = 3.0
    crack = envelope(highpass(noise(rng, 0.08), 1800), 0.0005, 0.012)
    body_cut = (lambda t: 500 * math.exp(-t * 3) + 90) if distant else (lambda t: 1400 * math.exp(-t * 4) + 120)
    body = envelope(lowpass(noise(rng, length), body_cut), 0.004, 0.32 if distant else 0.28)
    thump = envelope(sine(0.8, lambda t: 48 * math.exp(-t * 2) + 28), 0.003, 0.22)
    rumble = envelope(lowpass(noise(rng, length), 160), 0.05, 1.1)
    echo = place(envelope(lowpass(noise(rng, 1.5), 400), 0.02, 0.35), 0.42, length)
    tracks = [(body, 1.0), (thump, 0.9), (rumble, 0.35), (echo, 0.18)]
    if not distant:
        tracks.append((crack, 0.7))
    return fade(normalize(mix(*tracks), 0.95 if not distant else 0.7, drive=1.5), fade_out=0.3)


def splash(rng):
    length = 1.6
    rush = envelope(bandpass(noise(rng, length), lambda t: 1500 * math.exp(-t * 1.5) + 450, 1.2), 0.015, 0.32)
    thud = envelope(lowpass(noise(rng, 0.4), 260), 0.002, 0.07)
    drops = [0.0] * int(length * SR)
    for _ in range(70):
        start = int(rng.uniform(0.15, 1.3) * SR)
        f = rng.uniform(900, 3200)
        for i in range(int(0.025 * SR)):
            if start + i < len(drops):
                drops[start + i] += math.sin(TAU * f * i / SR) * math.exp(-i / (0.006 * SR)) * rng.uniform(0.2, 0.6)
    return fade(normalize(mix((rush, 1.0), (thud, 0.6), (drops, 0.35))), fade_out=0.2)


def wood_hit(rng):
    length = 1.0
    crack = envelope(highpass(noise(rng, 0.05), 1200), 0.0005, 0.01)
    modes = mix(*[(envelope(sine(length, f, rng.uniform(0, TAU)), 0.001, d), 1.0)
                  for f, d in ((170, 0.16), (410, 0.09), (760, 0.06), (1290, 0.04))])
    splinters = [0.0] * int(length * SR)
    for _ in range(60):
        start = int(rng.uniform(0.0, 0.5) * SR)
        for i in range(int(0.004 * SR)):
            if start + i < len(splinters):
                splinters[start + i] += rng.uniform(-1, 1) * math.exp(-i / (0.0012 * SR)) * 0.5
    body = envelope(lowpass(noise(rng, length), 900), 0.002, 0.12)
    return fade(normalize(mix((crack, 0.9), (modes, 0.6), (splinters, 0.5), (body, 0.6)), drive=0.8), fade_out=0.2)


def stone_hit(rng):
    length = 1.4
    thud = envelope(lowpass(noise(rng, 0.6), lambda t: 700 * math.exp(-t * 8) + 100), 0.001, 0.12)
    gravel = [0.0] * int(length * SR)
    for k in range(140):
        start = int((0.05 + rng.random() ** 1.6 * 1.1) * SR)
        f = rng.uniform(1500, 5000)
        amp = math.exp(-start / (0.45 * SR)) * rng.uniform(0.3, 1.0)
        for i in range(int(0.006 * SR)):
            if start + i < len(gravel):
                gravel[start + i] += math.sin(TAU * f * i / SR) * math.exp(-i / (0.0015 * SR)) * amp
    return fade(normalize(mix((thud, 1.0), (gravel, 0.35)), drive=0.6), fade_out=0.2)


def whistle(rng):
    length = 1.1
    tone = bandpass(noise(rng, length), lambda t: 2600 * math.exp(-t * 1.1) + 500, 9.0)
    rise = [x * min(i / (0.9 * SR), 1.0) ** 2 for i, x in enumerate(tone)]
    return fade(normalize(rise, 0.6), fade_out=0.04)


def bell(rng):
    length = 4.5
    f0 = 196.0
    partials = [(0.5, 1.0, 3.6), (1.0, 0.9, 3.0), (1.19, 0.55, 2.4), (1.5, 0.45, 1.9), (2.0, 0.5, 1.5),
                (2.52, 0.25, 1.0), (3.01, 0.2, 0.8), (4.07, 0.12, 0.5)]
    tone = mix(*[(envelope(sine(length, f0 * r, rng.uniform(0, TAU)), 0.002, d), a) for r, a, d in partials])
    strike = envelope(highpass(noise(rng, 0.05), 2000), 0.0005, 0.008)
    return fade(normalize(mix((tone, 1.0), (strike, 0.25))), fade_out=0.5)


def sea_loop(rng):
    length = 18.0
    base = lowpass(noise(rng, length), 520)
    hiss = highpass(lowpass(noise(rng, length), 3500), 900)
    out = []
    for i, (b, h) in enumerate(zip(base, hiss)):
        t = i / SR
        swell = 0.55 + 0.45 * math.sin(TAU * t / 6.0) * math.sin(TAU * t / 9.0 + 1.0)
        lap = max(0.0, math.sin(TAU * t / 3.0 + 0.5 * math.sin(TAU * t / 7.0))) ** 3
        out.append(b * (0.6 + 0.4 * swell) + h * (0.12 + 0.35 * lap))
    return normalize(loop_crossfade(out, 2.0), 0.5)


def gull(rng):
    length = 1.2
    out = [0.0] * int(length * SR)
    t0 = 0.0
    for _ in range(rng.randint(2, 3)):
        dur = rng.uniform(0.22, 0.32)
        call = sine(dur, lambda t, d=dur: 1500 + 700 * math.sin(math.pi * t / d) + 60 * math.sin(TAU * 32 * t))
        call = [x * math.sin(math.pi * i / len(call)) ** 0.7 for i, x in enumerate(call)]
        harm = sine(dur, lambda t, d=dur: 3000 + 1400 * math.sin(math.pi * t / d))
        harm = [x * 0.25 * math.sin(math.pi * i / len(harm)) for i, x in enumerate(harm)]
        out = mix((out, 1.0), (place(mix((call, 1.0), (harm, 1.0)), t0, length), 1.0))
        t0 += dur + rng.uniform(0.05, 0.12)
    return fade(normalize(out, 0.5), fade_out=0.05)


def creak(rng):
    length = 4.0
    groan = []
    ph = 0.0
    for i in range(int(length * SR)):
        t = i / SR
        f = 85 + 25 * math.sin(TAU * 0.6 * t) + 10 * math.sin(TAU * 3.1 * t)
        ph += TAU * f / SR
        saw = (ph / math.pi % 2.0) - 1.0
        groan.append(saw * (0.5 + 0.5 * math.sin(TAU * 0.45 * t + 0.4)) * min(t / 0.3, 1.0))
    groan = bandpass(groan, 420, 3.0)
    bubbles = [0.0] * int(length * SR)
    for _ in range(60):
        start = int(rng.uniform(0.3, 3.8) * SR)
        f0 = rng.uniform(300, 900)
        for i in range(int(0.05 * SR)):
            if start + i < len(bubbles):
                f = f0 * (1 + 2.5 * i / (0.05 * SR))
                bubbles[start + i] += math.sin(TAU * f * i / SR) * math.exp(-i / (0.012 * SR)) * 0.6
    water = envelope(lowpass(noise(rng, length), 300), 0.4, 1.5, hold=1.5)
    return fade(normalize(mix((groan, 0.7), (bubbles, 0.5), (water, 0.6))), fade_out=0.6)


def fire_loop(rng):
    length = 8.0
    roar = lowpass(noise(rng, length), 380)
    crackle = [0.0] * int(length * SR)
    for _ in range(420):
        start = int(rng.uniform(0, length) * SR)
        amp = rng.uniform(0.2, 1.0)
        for i in range(int(0.003 * SR)):
            if start + i < len(crackle):
                crackle[start + i] += rng.uniform(-1, 1) * amp * math.exp(-i / (0.0008 * SR))
    return normalize(loop_crossfade(mix((roar, 0.8), (crackle, 0.6)), 1.0), 0.55)


def click(rng):
    tick = envelope(bandpass(noise(rng, 0.06), 2200, 4.0), 0.0005, 0.01)
    return fade(normalize(tick, 0.5), fade_out=0.01)


def main() -> int:
    rng = random.Random(1695)
    save("cannon", cannon(rng))
    save("cannon_far", cannon(rng, distant=True))
    save("splash", splash(rng))
    save("wood_hit", wood_hit(rng))
    save("stone_hit", stone_hit(rng))
    save("whistle", whistle(rng))
    save("bell", bell(rng))
    save("sea_loop", sea_loop(rng))
    save("gull", gull(rng))
    save("creak", creak(rng))
    save("fire_loop", fire_loop(rng))
    save("click", click(rng))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
