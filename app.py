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
    st.session_state.messages = [{"role": "assistant", "content": "Welcome! How may I help you?", "status": "unread"}]

os.environ['OPENAI_API_KEY'] = st.secrets["openai_key"]

print("AI")
print(os.getenv('OPENAI_API_KEY'))
print("AI")

st.markdown(
            """
        <style>
            .st-emotion-cache-1c7y2kd {
                flex-direction: row-reverse;
                text-align: right;
            }
        </style>
        """,
            unsafe_allow_html=True,
        )

if not 'openai_client' in st.session_state:
    st.session_state.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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


def text_to_speech(text, voice="nova", model="tts-1"):
    try:
        response = st.session_state.openai_client.audio.speech.create(
            model=model,
            input=text,
            voice=voice,
        )
        print('Writing to mp3 file')
        response.stream_to_file('./out.mp3')
        #print('Completed writing to mp3 file')
        return True
    except Exception as e:
        print(f"An error occurred: You are using Free tier - Upgrade to Standard (S0).")
        return False

with st.sidebar:
    st.header("Yet Another Jarvis")


def generate_response_ai(text):
    response = st.session_state.openai_client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a helpful AI assistant that answers user queries."},
        {"role": "user", "content": text}
    ]
    )
    return response.choices[0].message.content

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

if ((st.session_state.messages[-1]['role'] == "assistant") and (st.session_state.messages[-1]["status"]=="unread")):
    with st.spinner('Synthesizing..'):
        audio_bytes = text_to_speech(st.session_state.messages[-1]['content'])
        if audio_bytes:
            autoplay_audio()
            st.session_state.messages[-1]["status"]="read"
prompt = st.chat_input("Ask me anything")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt, "status": "unprocessed"})
    st.rerun()

if ((st.session_state.messages[-1]['role'] == "user") and (st.session_state.messages[-1]['status'] == "unprocessed")):
    content = st.session_state.messages[-1]['content']
    with st.spinner('Thinking...'):
        ai_response = generate_response_ai(content)
        st.session_state.messages[-1]['status'] = "processed"
        st.session_state.messages.append({"role": "assistant", "content": ai_response, "status": "unread"})
    st.rerun()

with st.sidebar:
    text = whisper_stt(start_prompt="Record Voice Input", stop_prompt= "Stop", language = 'en')
    if text:
        st.session_state.messages.append({"role": "user", "content": text, "status": "unprocessed"})
        st.rerun()