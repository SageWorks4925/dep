# whisper_stt.py

from streamlit_mic_recorder import mic_recorder
import streamlit as st
import io, base64, requests
from openai import OpenAI
import os

if 'transcriber' not in st.session_state:
    st.session_state.transcriber = None

if 'voice_enabled' not in st.session_state:
    st.session_state.voice_enabled = False

if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []

if 'transcripts' not in st.session_state:
    st.session_state.transcripts = []

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assitant", "content": "Welcome! How may I help you?"}]

print('Secrets')
print(st.secrets)
print('Secrets AI')
os.environ['OPENAI_API_KEY'] = st.secrets["openai_key"]

print("AI")
print(os.getenv('OPENAI_API_KEY'))
print("AI")

def whisper_stt(start_prompt="Record", stop_prompt="Stop", just_once=True, 
                use_container_width=False, language=None, callback=None, args=(), kwargs=None, key=None):
    if not 'openai_client' in st.session_state:
        st.session_state.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    if not '_last_speech_to_text_transcript_id' in st.session_state:
        st.session_state._last_speech_to_text_transcript_id = 0
    if not '_last_speech_to_text_transcript' in st.session_state:
        st.session_state._last_speech_to_text_transcript = None
    if key and not key + '_output' in st.session_state:
        st.session_state[key + '_output'] = None
    audio = mic_recorder(start_prompt=start_prompt, stop_prompt=stop_prompt, just_once=just_once,
                         use_container_width=use_container_width,format="webm", key=key)
    new_output = False
    if audio is None:
        output = None
    else:
        id = audio['id']
        new_output = (id > st.session_state._last_speech_to_text_transcript_id)
        if new_output:
            output = None
            st.session_state._last_speech_to_text_transcript_id = id
            audio_bio = io.BytesIO(audio['bytes'])
            audio_bio.name = 'audio.webm'
            success = False
            err = 0
            while not success and err < 3:  # Retry up to 3 times in case of OpenAI server error.
                try:
                    transcript = st.session_state.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_bio,
                        language=language
                    )
                except Exception as e:
                    print(str(e))  # log the exception in the terminal
                    err += 1
                else:
                    success = True
                    output = transcript.text
                    st.session_state._last_speech_to_text_transcript = output
        elif not just_once:
            output = st.session_state._last_speech_to_text_transcript
        else:
            output = None

    if key:
        st.session_state[key + '_output'] = output
    if new_output and callback:
        callback(*args, **(kwargs or {}))
    return output


def text_to_speech(text, voice="alloy", model="tts-1"):
    """
    Converts text to speech using OpenAI's TTS API.
    
    Parameters:
    - text: The text to be converted to speech.
    - voice: The voice model to use. Default is "alloy".
    - model: The TTS model to use. Default is "tts-1".
    
    Returns:
    - The audio content as bytes.
    """
    try:
        response = st.session_state.openai_client.audio.speech.create(
            model=model,
            input=text,
            voice=voice,
            #response_format="mp3"
        )
        #audio_url = response['data']['url']
        #audio_response = requests.get(audio_url)
        #print(audio_response)
        response.stream_to_file('./out.mp3')
        return  True#io.BytesIO(audio_response)
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

with st.sidebar:
    st.header("Jarvis")
    # More buttons can be added as needed

# Main area split into chat input and chat display
#col1, col2 = st.columns(2)
# Chat input area
#with col1:
    # Display chat messages from history on app rerun

#with st.chat_message("user"):
#    st.markdown(prompt)
# Accept user input

def generate_response():
    st.session_state.messages.append({"role": "assistant", "content": "Response generated."})

def autoplay_audio():
    with open("./out.mp3", "rb") as audio_file:
        audio_bytes = audio_file.read()
    base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
    audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{base64_audio}" type="audio/mp3"></audio>'
    st.markdown(audio_html, unsafe_allow_html=True)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
if st.session_state.messages[-1]['role'] == "assistant":
    audio_bytes = text_to_speech(st.session_state.messages[-1]['content'])
    if audio_bytes:
        autoplay_audio()
prompt = st.chat_input("What is up?")
if prompt:
    # Display user message in chat message container
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    generate_response()
    st.rerun()
#col1, col2 = st.columns([20, 1])

with st.sidebar:
    text = whisper_stt(start_prompt="Record Voice Input", stop_prompt= "Stop", language = 'en')
    if text:
        st.session_state.messages.append({"role": "user", "content": text})
        #st.write(text)
        st.rerun()