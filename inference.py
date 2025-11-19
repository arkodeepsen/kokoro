import argparse
import requests
import json
import base64
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

def main():
    default_endpoint_id = os.getenv("ENDPOINT_ID", "")
    default_api_key = os.getenv("RUNPOD_API_KEY", "")
    default_url = f"https://api.runpod.ai/v2/{default_endpoint_id}/runsync" if default_endpoint_id else None

    parser = argparse.ArgumentParser(description="Inference client for Kokoro Serverless")
    parser.add_argument("--url", type=str, default=default_url, help="RunPod Endpoint URL (e.g., https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync)")
    parser.add_argument("--api-key", type=str, default=default_api_key, help="RunPod API Key")
    parser.add_argument("--text", type=str, default="Hello, this is a test of the Kokoro TTS system.", help="Text to synthesize")
    parser.add_argument("--voice", type=str, default="af_bella", help="Voice ID (default: af_bella)")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed (default: 1.0)")
    parser.add_argument("--output", type=str, default="output.mp3", help="Output filename")
    parser.add_argument("--model", type=str, default="kokoro", help="Model ID")
    
    args = parser.parse_args()

    # Construct payload
    payload = {
        "input": {
            "model": args.model,
            "input": args.text,
            "voice": args.voice,
            "response_format": "mp3",
            "speed": args.speed
        }
    }

    headers = {
        "Content-Type": "application/json"
    }
    
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    print(f"Sending request to {args.url}...")
    print(f"Text: {args.text}")
    print(f"Voice: {args.voice}")

    try:
        response = requests.post(args.url, json=payload, headers=headers, timeout=300)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle RunPod async/sync response structure
        if "id" in data and "status" in data:
            print(f"Job ID: {data['id']}, Status: {data['status']}")
            
            # If async, we might need to poll (simplified here for runsync)
            if data["status"] == "IN_PROGRESS" or data["status"] == "IN_QUEUE":
                 print("Job in progress, this script expects runsync or completed job...")
                 # In a full implementation, we would poll /status endpoint here
            
        # Check for output in various formats (RunPod standard vs direct)
        output_data = None
        
        if "output" in data:
            output_data = data["output"]
        else:
            output_data = data # Direct response

        if output_data and "audio_base64" in output_data:
            audio_bytes = base64.b64decode(output_data["audio_base64"])
            with open(args.output, "wb") as f:
                f.write(audio_bytes)
            print(f"Success! Audio saved to {args.output}")
            print(f"Size: {len(audio_bytes)} bytes")
        elif output_data and "error" in output_data:
             print(f"Error from server: {output_data['error']}")
        else:
            print("Unexpected response format:")
            print(json.dumps(data, indent=2))

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
