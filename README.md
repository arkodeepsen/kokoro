# Kokoro Serverless

[![Runpod](https://api.runpod.io/badge/arkodeepsen/kokoro)](https://console.runpod.io/hub/arkodeepsen/kokoro)
Deploy directly on Pod (Alternative, not serverless) - [Pod Template](https://console.runpod.io/deploy?template=ekgy3gw2fd&ref=az0kmnor)

[![One-Click Pod Deployment](https://cdn.prod.website-files.com/67d20fb9f56ff2ec6a7a657d/685b44aed6fc50d169003af4_banner-runpod.webp)](https://console.runpod.io/deploy?template=ekgy3gw2fd&ref=az0kmnor)

A production-ready RunPod serverless endpoint for Kokoro TTS - a high-quality, lightweight text-to-speech model with exceptional voice mixing and phoneme generation capabilities.

## Features
- **Official Kokoro Model** - v0.19 (82M parameters) high-fidelity TTS
- **GPU Optimized** - Runs efficiently on RTX 3090, 4090, A4000, and L4 GPUs
- **Auto-scaling** - Scales to 0 when idle to save costs
- **Network Volume Storage** - Model cached persistently across all workers
- **Fast Cold Starts** - Optimized Docker image with pre-installed dependencies
- **Advanced Audio** - Voice mixing, word timestamps, and phoneme generation

## Model Specifications
- **Model**: `hexgrad/Kokoro-82M`
- **Recommended VRAM**: 4GB+ (8GB recommended)
- **Precision**: float32 / float16
- **Languages**: English (American/British), French, Japanese, Chinese, and more
- **Voices**: Multiple high-quality voices with mixing support (`af_bella+af_sky`)
- **License**: Apache 2.0

## API Usage

This serverless endpoint supports multiple operations through a single entry point. The operation is determined by the `endpoint` parameter in the input payload (defaults to standard TTS).

### 1. Standard Text-to-Speech
**Endpoint**: `/v1/audio/speech` (Default)

Generate high-quality audio from text.

```json
{
  "input": {
    "model": "kokoro",
    "input": "Hello world! This is Kokoro running on serverless.",
    "voice": "af_bella",
    "response_format": "mp3",
    "speed": 1.0
  }
}
```

### 2. Voice Combination
**Endpoint**: `/v1/audio/voices/combine`

Mix two voices together to create a unique persona. Join voice IDs with `+`.

```json
{
  "input": {
    "endpoint": "/v1/audio/voices/combine",
    "method": "POST",
    "voices": "af_bella+af_sky"
  }
}
```
*Returns a base64-encoded `.pt` file containing the combined voice style.*

### 3. Captioned Speech (Timestamps/SRT)
**Endpoint**: `/dev/captioned_speech`

Generate audio along with word-level timestamps, perfect for creating subtitles (SRT).

```json
{
  "input": {
    "endpoint": "/dev/captioned_speech",
    "method": "POST",
    "input": "This text will have timestamps.",
    "voice": "af_bella",
    "return_timestamps": true,
    "response_format": "mp3"
  }
}
```
*Returns `audio` (base64) and a `timestamps` array with start/end times for each word.*

### 4. Text to Phonemes
**Endpoint**: `/dev/phonemize`

Convert text into its phonemic representation to see exactly how the model interprets pronunciation.

```json
{
  "input": {
    "endpoint": "/dev/phonemize",
    "method": "POST",
    "text": "Hello world",
    "language": "a"
  }
}
```
*Returns the phonemes string.*

### 5. Generate from Phonemes
**Endpoint**: `/dev/generate_from_phonemes`

Generate audio directly from raw phonemes.

```json
{
  "input": {
    "endpoint": "/dev/generate_from_phonemes",
    "method": "POST",
    "phonemes": "həˈloʊ wɜrld",
    "voice": "af_bella"
  }
}
```

### 6. List Available Voices
**Endpoint**: `/v1/audio/voices`

Get a list of all available voice profiles.

```json
{
  "input": {
    "endpoint": "/v1/audio/voices",
    "method": "GET"
  }
}
```

---

### Parameters Reference

#### Common Parameters (TTS)
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input` | string | **required** | The text to generate speech from. |
| `voice` | string | `af_bella` | Voice ID (e.g., `af_bella`, `af_sky`) or combination (`voice1+voice2`). |
| `speed` | float | `1.0` | Speed multiplier (0.5 to 2.0). |
| `response_format` | string | `mp3` | Audio format: `mp3`, `wav`, `pcm`. |
| `model` | string | `kokoro` | Model identifier. |

#### Advanced Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `endpoint` | string | `/v1/audio/speech` | The internal API route to target. |
| `method` | string | `POST` | HTTP method (`GET` or `POST`). |
| `return_timestamps`| boolean | `false` | For `/dev/captioned_speech`: include word-level timing data. |
| `language` | string | `a` | For `/dev/phonemize`: language code (`a` for American English). |
| `phonemes` | string | - | For `/dev/generate_from_phonemes`: raw phoneme string. |

### Output Format
All successful responses return a JSON object. Binary data (audio, files) is **Base64 encoded**.

**Success Response:**
```json
{
  "success": true,
  "audio_base64": "SUQzBAAAAA...",  // Base64 encoded audio
  "text": "Hello world...",
  "voice": "af_bella",
  "size_bytes": 123456
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error description here"
}
```

### Example Request (Python)
```python
import requests
import base64

endpoint_id = "YOUR_ENDPOINT_ID"
api_key = "YOUR_API_KEY"

url = f"https://api.runpod.ai/v2/{endpoint_id}/runsync"

payload = {
    "input": {
        "input": "Hello from Kokoro Serverless!",
        "voice": "af_bella",
        "response_format": "mp3"
    }
}

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)
result = response.json()

if "audio_base64" in result:
    audio_data = base64.b64decode(result["audio_base64"])
    with open("output.mp3", "wb") as f:
        f.write(audio_data)
    print("Audio saved to output.mp3")
else:
    print("Error:", result)
```

### Example Request (cURL)
```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "input": "Hello from Kokoro Serverless!",
      "voice": "af_bella",
      "response_format": "mp3"
    }
  }'
```

## Deployment Configuration

The template is configured with optimal settings in `runpod.toml`:

- **GPU Types**: RTX 4000 Ada, L4, A4000, RTX 3090/4090, A100
- **Recommended VRAM**: 8GB
- **Container Disk**: 10GB (code + dependencies)
- **Network Volume**: ~20GB (persistent model storage) - **⚠️ HIGHLY RECOMMENDED**
- **Workers**: 0-5 (auto-scaling)
- **Timeout**: 300 seconds per job

### ⚠️ Important: Network Volume Recommended

**We highly recommend attaching a network volume (~20GB) when deploying this endpoint.**

Without a network volume:
- ⚠️ Models will be downloaded on **every cold start** (~30-60s delay)
- ⚠️ Higher bandwidth usage and slower scaling

The network volume:
- ✅ Stores the model persistently across all workers
- ✅ Enables **instant cold starts** after the first run
- ✅ Reduces bandwidth costs

## Performance
- **Cold Start**: ~30-60 seconds (first run), <5 seconds (cached)
- **Warm Inference**: <1 second for typical sentences
- **Memory Usage**: ~3-4GB VRAM
- **Throughput**: High (lightweight model)

## Tips for Best Results
1. **Voice Mixing**: Combine voices with `+` (e.g., `af_bella+af_sky`) to create unique personas.
2. **Timestamps**: Use the `/dev/captioned_speech` endpoint to get word-level timestamps for subtitles.
3. **Phonemes**: Use `/dev/phonemize` to check how text is processed before generation.
4. **Speed**: Adjust `speed` (0.5x to 2.0x) to control pacing without altering pitch.

## License
This project is licensed under the Apache 2.0 License. The Kokoro model itself is Apache 2.0.

## Credits
This project is a serverless wrapper around the excellent [Kokoro-FastAPI](https://github.com/remsky/Kokoro-FastAPI) by [remsky](https://github.com/remsky). It uses the official `ghcr.io/remsky/kokoro-fastapi-gpu` Docker image as its base.

## Support
For issues or questions about this RunPod template, please open an issue on the GitHub repository.
