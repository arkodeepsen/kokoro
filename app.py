import streamlit as st
import requests
import json
import base64
import time
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Kokoro Serverless Client", layout="wide")

# --- Helper Functions ---

def timestamp_to_srt_time(seconds):
    """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int(td.microseconds / 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def generate_srt(timestamps):
    """Generate SRT content from timestamps"""
    srt_content = ""
    for i, ts in enumerate(timestamps, 1):
        start = timestamp_to_srt_time(ts['start_time'])
        end = timestamp_to_srt_time(ts['end_time'])
        word = ts['word']
        srt_content += f"{i}\n{start} --> {end}\n{word}\n\n"
    return srt_content

def make_request(url, api_key, payload):
    """Make request to RunPod endpoint"""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=300)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response:
             st.error(f"Response: {e.response.text}")
        return None

# --- Sidebar Configuration ---
st.sidebar.title="Configuration"

# Load defaults from env
default_endpoint_id = os.getenv("ENDPOINT_ID", "")
default_api_key = os.getenv("RUNPOD_API_KEY", "")
default_url = f"https://api.runpod.ai/v2/{default_endpoint_id}/runsync" if default_endpoint_id else ""

api_url = st.sidebar.text_input("RunPod Endpoint URL", value=default_url, placeholder="https://api.runpod.ai/v2/YOUR_ID/runsync")
api_key = st.sidebar.text_input("RunPod API Key", value=default_api_key, type="password")

if not api_url:
    st.warning("Please enter your RunPod Endpoint URL in the sidebar.")
    st.stop()

# --- Main UI ---
st.title("Kokoro Serverless Client")

tabs = st.tabs(["Text to Speech", "Voices", "Tools (SRT/Phonemes)"])

# --- Tab 1: Text to Speech ---
with tabs[0]:
    st.header("Text to Speech")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        text_input = st.text_area("Input Text", "Hello, this is a test of the Kokoro TTS system.", height=150)
    
    with col2:
        voice = st.text_input("Voice ID", "af_bella", help="e.g., af_bella, af_sky, or combination af_bella+af_sky")
        speed = st.slider("Speed", 0.25, 4.0, 1.0, 0.1)
        response_format = st.selectbox("Format", ["mp3", "wav", "opus", "flac", "pcm"])
        model = st.text_input("Model", "kokoro")

    if st.button("Generate Audio", type="primary"):
        with st.spinner("Generating audio..."):
            payload = {
                "input": {
                    "model": model,
                    "input": text_input,
                    "voice": voice,
                    "response_format": response_format,
                    "speed": speed
                }
            }
            
            data = make_request(api_url, api_key, payload)
            
            if data:
                # Handle RunPod response structure
                output = data.get("output", data) # Handle wrapped or direct
                
                if output and "audio_base64" in output:
                    audio_bytes = base64.b64decode(output["audio_base64"])
                    st.audio(audio_bytes, format=f"audio/{response_format}")
                    st.success(f"Generated {len(audio_bytes)} bytes")
                    
                    st.download_button(
                        label="Download Audio",
                        data=audio_bytes,
                        file_name=f"output.{response_format}",
                        mime=f"audio/{response_format}"
                    )
                elif output and "error" in output:
                    st.error(f"API Error: {output['error']}")
                else:
                    st.write("Raw Response:", data)

# --- Tab 2: Voices ---
with tabs[1]:
    st.header("Voice Management")
    
    v_col1, v_col2 = st.columns(2)
    
    with v_col1:
        st.subheader("List Available Voices")
        if st.button("Fetch Voices"):
            payload = {
                "input": {
                    "endpoint": "/v1/audio/voices",
                    "method": "GET"
                }
            }
            data = make_request(api_url, api_key, payload)
            if data:
                output = data.get("output", data)
                if output and "voices" in output:
                    st.json(output["voices"])
                else:
                    st.error("Failed to fetch voices")
                    st.write(data)

    with v_col2:
        st.subheader("Combine Voices")
        voices_to_combine = st.text_input("Voices to combine (comma or + separated)", "af_bella+af_sky")
        if st.button("Combine"):
            payload = {
                "input": {
                    "endpoint": "/v1/audio/voices/combine",
                    "method": "POST",
                    "voices": voices_to_combine
                }
            }
            data = make_request(api_url, api_key, payload)
            if data:
                output = data.get("output", data)
                if output and "voice_file_base64" in output:
                    voice_bytes = base64.b64decode(output["voice_file_base64"])
                    st.success("Voices combined successfully!")
                    st.download_button(
                        label="Download Combined Voice (.pt)",
                        data=voice_bytes,
                        file_name="combined_voice.pt",
                        mime="application/octet-stream"
                    )
                else:
                    st.error("Failed to combine voices")
                    st.write(data)

# --- Tab 3: Tools ---
with tabs[2]:
    st.header("Advanced Tools")
    
    tool_type = st.radio("Select Tool", ["Captioned Speech (SRT)", "Phonemize"])
    
    if tool_type == "Captioned Speech (SRT)":
        st.subheader("Generate Audio with Subtitles (SRT)")
        cs_text = st.text_area("Text for Captioning", "This is a test of captioned speech generation.")
        cs_voice = st.text_input("Voice", "af_bella", key="cs_voice")
        
        if st.button("Generate with Captions"):
            payload = {
                "input": {
                    "endpoint": "/dev/captioned_speech",
                    "method": "POST",
                    "input": cs_text,
                    "voice": cs_voice,
                    "return_timestamps": True,
                    "response_format": "mp3"
                }
            }
            
            with st.spinner("Generating..."):
                data = make_request(api_url, api_key, payload)
                if data:
                    output = data.get("output", data)
                    result = output.get("result", {})
                    
                    if "audio" in result:
                        audio_bytes = base64.b64decode(result["audio"])
                        st.audio(audio_bytes, format="audio/mp3")
                        
                        if "timestamps" in result:
                            srt_file = generate_srt(result["timestamps"])
                            st.text_area("Generated SRT", srt_file, height=200)
                            
                            col_d1, col_d2 = st.columns(2)
                            with col_d1:
                                st.download_button("Download Audio", audio_bytes, "captioned.mp3", "audio/mp3")
                            with col_d2:
                                st.download_button("Download SRT", srt_file, "captioned.srt", "text/plain")
                        else:
                            st.warning("No timestamps returned")
                    else:
                        st.error("Failed")
                        st.write(output)

    elif tool_type == "Phonemize":
        st.subheader("Convert Text to Phonemes")
        ph_text = st.text_input("Text", "Hello world")
        ph_lang = st.text_input("Language Code", "a", help="a=American English, b=British English, etc.")
        
        if st.button("Phonemize"):
            payload = {
                "input": {
                    "endpoint": "/dev/phonemize",
                    "method": "POST",
                    "text": ph_text,
                    "language": ph_lang
                }
            }
            data = make_request(api_url, api_key, payload)
            if data:
                output = data.get("output", data)
                result = output.get("result", {})
                if "phonemes" in result:
                    st.code(result["phonemes"], language="text")
                    st.write(f"Tokens: {result.get('tokens')}")
                else:
                    st.error("Failed")
                    st.write(output)
