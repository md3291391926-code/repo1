# Kids Smart Tracker Ad Generator

This repository contains a manually triggered GitHub Actions workflow that generates a 30-second, portrait 9:16 MP4 product ad using Replicate Wan 2.5, English female narration, burned-in English subtitles, and hard cuts between scenes.

## One-time setup

1. Create a Replicate API token at https://replicate.com/account/api-tokens.
2. In this repository, open **Settings → Secrets and variables → Actions → New repository secret**.
3. Name the secret `REPLICATE_API_TOKEN` and paste the token value there. Never commit the token or post it in an issue or chat.
4. Open **Actions → Generate Kids Smart Tracker Ad → Run workflow**.

## Output

When the run succeeds, open the completed workflow run and download the artifact named `kids-smart-tracker-ad-30s-9x16`. It contains `kids-smart-tracker-ad-30s-9x16.mp4`.

The workflow makes six 5-second video-generation requests, so Replicate usage charges may apply. Check your Replicate pricing and account limits before running it. The GitHub Actions job may take a while because video generation is compute-intensive.

## Notes

- Generated scenes are assembled with FFmpeg using direct cuts (no fade-in or fade-out).
- English voice uses the online Edge TTS service.
- The repository is public; do not commit credentials, private source material, or personal information.
