# whisper_stt.py

from streamlit_mic_recorder import mic_recorder
import streamlit as st
import io
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()


if 'transcriber' not in st.session_state:
    st.session_state.transcriber = None

if 'voice_enabled' not in st.session_state:
    st.session_state.voice_enabled = False

if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []

if 'transcripts' not in st.session_state:
    st.session_state.transcripts = []

if "messages" not in st.session_state:
    st.session_state.messages = []


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


with st.sidebar:
    st.header("Jarvis")
    # Add your buttons and functionality here
    speech_key = "" #st.text_input("", value="")
    service_region = "" #st.text_input("",value="")
    # Check if the user has entered the Azure credentials
    #transcribe = st.toggle('Voice support', value=False)
    # More buttons can be added as needed

# Main area split into chat input and chat display
#col1, col2 = st.columns(2)
# Chat input area
#with col1:
    # Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
#with st.chat_message("user"):
#    st.markdown(prompt)
# Accept user input
with st.container():
    # Use columns to layout the chat input and the mic recorder button side by side
    col1, col2 = st.columns([6, 1])
    with col1:
        prompt = st.chat_input("What is up?")
        if prompt:
            # Display user message in chat message container
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
    with col2:
        text = whisper_stt(language = 'en')
        if text:
            st.session_state.messages.append({"role": "user", "content": text})
            #st.write(text)
            st.rerun()