"""
RunPod Serverless Handler Wrapper for Kokoro FastAPI
This handler starts the existing FastAPI app internally and proxies requests to it.
"""

import asyncio
import base64
import json
import subprocess
import time
import threading
from typing import Dict, Any

import requests
import runpod
from loguru import logger

# Global variables
fastapi_process = None
fastapi_ready = False
FASTAPI_URL = "http://localhost:8880"

def start_fastapi():
    """Start the FastAPI server in the background"""
    global fastapi_process, fastapi_ready

    logger.info("Starting internal FastAPI server...")

    # Start the FastAPI server using the existing startup method
    # Wait for the server to be ready
    max_wait = 120  # 2 minutes max wait
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{FASTAPI_URL}/health", timeout=5)
            if response.status_code == 200:
                fastapi_ready = True
                logger.info("FastAPI server is ready!")
                return
        except requests.exceptions.RequestException:
            pass

        time.sleep(2)

    logger.error("FastAPI server failed to start within timeout")
    raise RuntimeError("FastAPI server startup timeout")

def wait_for_fastapi():
    """Wait for FastAPI to be ready"""
    max_wait = 180  # 3 minutes
    start_time = time.time()

    while not fastapi_ready and time.time() - start_time < max_wait:
        time.sleep(1)

    if not fastapi_ready:
        raise RuntimeError("FastAPI server not ready")

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod serverless handler that proxies to the internal FastAPI server

    Supports all endpoints from the original Kokoro FastAPI:
    - /v1/audio/speech (TTS generation)
    - /v1/audio/voices (list voices)
    - /v1/models (list models)
    - /dev/captioned_speech (TTS with timestamps)
    - /dev/phonemize (text to phonemes)
    - /dev/generate_from_phonemes (phonemes to audio)
    - /v1/audio/voices/combine (voice combination)
    """
    try:
        # Ensure FastAPI is ready
        wait_for_fastapi()

        job_input = job.get("input", {})

        # Determine endpoint and method from input
        endpoint = job_input.get("endpoint", "/v1/audio/speech")
        method = job_input.get("method", "POST").upper()

        # Handle different endpoints
        if endpoint == "/v1/audio/voices" and method == "GET":
            # List voices
            response = requests.get(f"{FASTAPI_URL}/v1/audio/voices", timeout=30)
            if response.status_code == 200:
                return {"success": True, "voices": response.json()}
            else:
                return {"success": False, "error": f"Failed to get voices: {response.text}"}

        elif endpoint == "/v1/models" and method == "GET":
            # List models
            response = requests.get(f"{FASTAPI_URL}/v1/models", timeout=30)
            if response.status_code == 200:
                return {"success": True, "models": response.json()}
            else:
                return {"success": False, "error": f"Failed to get models: {response.text}"}

        elif endpoint == "/dev/phonemize" and method == "POST":
            # Phonemize text
            payload = {
                "text": job_input.get("text", ""),
                "language": job_input.get("language", "a")
            }
            response = requests.post(f"{FASTAPI_URL}/dev/phonemize", json=payload, timeout=60)
            if response.status_code == 200:
                return {"success": True, "result": response.json()}
            else:
                return {"success": False, "error": f"Phonemize failed: {response.text}"}

        elif endpoint == "/dev/generate_from_phonemes" and method == "POST":
            # Generate from phonemes
            payload = {
                "phonemes": job_input.get("phonemes", ""),
                "voice": job_input.get("voice", "af_bella")
            }
            response = requests.post(f"{FASTAPI_URL}/dev/generate_from_phonemes", json=payload, timeout=300)
            if response.status_code == 200:
                audio_data = response.content
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                return {
                    "success": True,
                    "audio_base64": audio_base64,
                    "voice": payload["voice"],
                    "size_bytes": len(audio_data)
                }
            else:
                return {"success": False, "error": f"Phoneme generation failed: {response.text}"}

        elif endpoint == "/v1/audio/voices/combine" and method == "POST":
            # Combine voices
            voices = job_input.get("voices", "")
            response = requests.post(f"{FASTAPI_URL}/v1/audio/voices/combine", json=voices, timeout=120)
            if response.status_code == 200:
                # Voice combination returns a file - encode as base64
                file_data = response.content
                file_base64 = base64.b64encode(file_data).decode('utf-8')
                return {
                    "success": True,
                    "voice_file_base64": file_base64,
                    "voices": voices,
                    "size_bytes": len(file_data)
                }
            else:
                return {"success": False, "error": f"Voice combination failed: {response.text}"}

        elif endpoint == "/dev/captioned_speech" and method == "POST":
            # Captioned speech with timestamps
            fastapi_payload = job_input.copy()
            fastapi_payload.pop("endpoint", None)
            fastapi_payload.pop("method", None)

            # Set defaults for captioned speech
            if "input" not in fastapi_payload:
                fastapi_payload["input"] = job_input.get("text", "")
            if "model" not in fastapi_payload:
                fastapi_payload["model"] = "kokoro"
            if "voice" not in fastapi_payload:
                fastapi_payload["voice"] = "af_bella"
            if "response_format" not in fastapi_payload:
                fastapi_payload["response_format"] = "mp3"

            response = requests.post(f"{FASTAPI_URL}/dev/captioned_speech", json=fastapi_payload, timeout=300)
            if response.status_code == 200:
                result = response.json()
                # If audio is in the response, encode it
                if "audio" in result:
                    # Audio is already base64 encoded in captioned speech response
                    return {"success": True, "result": result}
                else:
                    return {"success": True, "result": result}
            else:
                return {"success": False, "error": f"Captioned speech failed: {response.text}"}

        else:
            # Default: /v1/audio/speech endpoint
            # Handle both OpenAI format and simple format for speech generation
            if "input" in job_input or "text" in job_input:
                if "input" in job_input and isinstance(job_input["input"], str):
                    # OpenAI-compatible format - pass through directly
                    fastapi_payload = job_input.copy()
                    fastapi_payload.pop("endpoint", None)
                    fastapi_payload.pop("method", None)
                elif "text" in job_input:
                    # Simple format - convert to OpenAI format
                    text = job_input.get("text")
                    fastapi_payload = {
                        "model": job_input.get("model", "kokoro"),
                        "input": text,
                        "voice": job_input.get("voice", "af_bella"),
                        "response_format": job_input.get("format", job_input.get("response_format", "mp3")),
                        "speed": job_input.get("speed", 1.0)
                    }
                    # Copy other optional parameters
                    for key in ["stream", "return_download_link", "lang_code", "normalization_options"]:
                        if key in job_input:
                            fastapi_payload[key] = job_input[key]
                else:
                    return {"error": "Missing required parameter: 'input' or 'text'"}
            else:
                return {"error": "Missing required parameter: 'input' or 'text'"}

            logger.info(f"Forwarding TTS request: {fastapi_payload.get('input', '')[:50]}...")

            # Forward request to internal FastAPI server
            response = requests.post(
                f"{FASTAPI_URL}/v1/audio/speech",
                json=fastapi_payload,
                timeout=300,  # 5 minutes timeout
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                # Convert binary audio response to base64
                audio_data = response.content
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')

                return {
                    "success": True,
                    "audio_base64": audio_base64,
                    "text": fastapi_payload.get("input", ""),
                    "voice": fastapi_payload.get("voice", ""),
                    "speed": fastapi_payload.get("speed", 1.0),
                    "format": fastapi_payload.get("response_format", "mp3"),
                    "model": fastapi_payload.get("model", "kokoro"),
                    "size_bytes": len(audio_data)
                }
            else:
                error_msg = f"FastAPI error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }

    except requests.exceptions.Timeout:
        logger.error("Request timeout")
        return {
            "success": False,
            "error": "Request timeout - request took too long"
        }
    except Exception as e:
        logger.error(f"Handler error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# Start FastAPI server in background thread
logger.info("Initializing Kokoro FastAPI Serverless Wrapper...")
threading.Thread(target=start_fastapi, daemon=True).start()

# Start the serverless worker
if __name__ == "__main__":
    logger.info("Starting RunPod serverless worker...")
    runpod.serverless.start({"handler": handler})