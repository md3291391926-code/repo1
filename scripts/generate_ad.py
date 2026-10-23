import asyncio
import os
import subprocess
import time
from pathlib import Path

import edge_tts
import requests

TOKEN = os.environ["REPLICATE_API_TOKEN"]
OUT = Path("output")
OUT.mkdir(exist_ok=True)
API = "https://api.replicate.com/v1/models/wan-video/wan-2.5-t2v/predictions"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

SCENES = [
    ("Premium cinematic 3D macro shot of a tiny smart tracker rotating in a dark studio, glossy black and brushed titanium, electric cyan and violet rim lighting, luxury tech commercial, vertical portrait 9:16, no text or logos.", "I recently found a little gadget that can make everyday life so much easier."),
    ("Stylish 3D scene of a compact smart tracker attached to a colorful child's backpack beside a toy, modern family home, premium soft lighting, cyan accents, vertical portrait 9:16, no text or logos.", "You can attach it to toys, clip it onto backpacks,"),
    ("Premium 3D product photography of a compact tracker beside a reusable water bottle, umbrella and child's jacket, glossy reflections, blue and violet highlights, vertical portrait 9:16, no text or logos.", "use it with water bottles, or keep it with umbrellas and jackets."),
    ("Cinematic 3D close-up of a smartphone showing a clean abstract location map and a cyan pulse leading to a small tracker, futuristic but believable interface, dark studio, vertical portrait 9:16, no readable text.", "This smart tracker is small, lightweight, and easy to carry,"),
    ("Warm premium 3D animated family scene, parent finding a backpack with a small tracker using a smartphone, subtle sound-wave rings around the tracker, reassuring commercial lighting, vertical portrait 9:16, no text or logos.", "making it perfect for your kids' everyday essentials. When something goes missing, use a compatible phone to help locate the tracker and play a sound."),
    ("Hero shot of the smart tracker on a dark pedestal, electric cyan and violet light trails, elegant particles, cinematic camera push-in, premium 3D tech advertisement, vertical portrait 9:16, no text or logos.", "No more wasting time searching for misplaced things. It's a practical, affordable helper for busy families. Check it out!")
]

def ffmpeg(args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)

def generate(prompt):
    """Create one Replicate prediction and poll it until it succeeds or fails."""
    payload = {
        "input": {
            "prompt": prompt + " High detail, consistent product design, cinematic camera movement, 5-second commercial shot.",
            "size": "720*1280",
            "duration": 5,
            "negative_prompt": "text, captions, watermark, logo, blurry, distorted product",
            "enable_prompt_expansion": True,
        }
    }

    response = requests.post(
        API,
        headers={**HEADERS, "Prefer": "wait=60"},
        json=payload,
        timeout=90,
    )
    if not response.ok:
        raise RuntimeError(
            f"Replicate create-prediction request failed (HTTP {response.status_code}): "
            f"{response.text[:2000]}"
        )
    data = response.json()
    prediction_url = data.get("urls", {}).get("get")
    if not prediction_url:
        raise RuntimeError(f"Replicate response did not include urls.get: {data}")

    deadline = time.monotonic() + 3600
    while data.get("status") in ("starting", "processing"):
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Replicate prediction timed out. Prediction: {prediction_url}")
        time.sleep(10)
        poll = requests.get(prediction_url, headers=HEADERS, timeout=90)
        if not poll.ok:
            raise RuntimeError(
                f"Replicate polling failed (HTTP {poll.status_code}): {poll.text[:2000]}"
            )
        data = poll.json()
        print(f"Replicate prediction status: {data.get('status', 'unknown')}")

    if data.get("status") != "succeeded":
        raise RuntimeError(
            f"Replicate video generation status={data.get('status')}; "
            f"error={data.get('error')}; logs={str(data.get('logs', ''))[-2000:]}"
        )

    url = data.get("output")
    if isinstance(url, list):
        url = url[0] if url else None
    if not isinstance(url, str) or not url.startswith("https://"):
        raise RuntimeError(f"Replicate returned an unexpected output value: {url!r}")

    video = requests.get(url, timeout=240)
    if not video.ok:
        raise RuntimeError(
            f"Could not download generated video (HTTP {video.status_code}): {video.text[:500]}"
        )
    if not video.content:
        raise RuntimeError("Replicate returned an empty video file.")
    return video.content

async def main():
    normalized = []
    for i, (prompt, _) in enumerate(SCENES, 1):
        print(f"Generating scene {i}/{len(SCENES)}")
        raw = OUT / f"raw{i}.mp4"
        raw.write_bytes(generate(prompt))
        clean = OUT / f"scene{i}.mp4"
        ffmpeg(["-i", str(raw), "-t", "5", "-vf",
                "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,fps=30,setsar=1",
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(clean)])
        normalized.append(clean)

    concat = OUT / "concat.txt"
    concat.write_text("".join(f"file '{p.resolve()}'\n" for p in normalized))
    silent = OUT / "silent.mp4"
    ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(silent)])

    narration = OUT / "narration.mp3"
    script = " ".join(line for _, line in SCENES)
    await edge_tts.Communicate(script, "en-US-AriaNeural", rate="+2%").save(str(narration))

    def stamp(seconds):
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02}:{m:02}:{s:02},000"

    with open(OUT / "captions.srt", "w", encoding="utf-8") as f:
        for i, (_, line) in enumerate(SCENES):
            f.write(f"{i+1}\n{stamp(i*5)} --> {stamp((i+1)*5)}\n{line}\n\n")

    final = OUT / "kids-smart-tracker-ad-30s-9x16.mp4"
    ffmpeg(["-i", str(silent), "-i", str(narration), "-vf",
            f"subtitles={OUT / 'captions.srt'}:force_style='FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=90'",
            "-af", "apad,atrim=0:30", "-t", "30", "-r", "30", "-c:v", "libx264",
            "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(final)])
    print(f"Created {final}")

asyncio.run(main())
