from src.audio_capture import LoopbackRecorder
from src.transcriber import SpeechTranscriber
from src.llm_client import LLMClient
import time
import os

def update_response(new_text):
    #As a callback function, update the response
    print(new_text, end="", flush=True,sep="")

def main():
    while True:
        # 1. recording
# Press Ctrl+C to start
        client = LLMClient()
        input('press key to start recording...')
        # Start recording
        print("starting recording...")
        recorder = LoopbackRecorder(device_index=2)
        recorder.start_recording("interview.wav")
        recorder.record(duration=5)# Record for 5 seconds

        recorder.stop_recording()
        print("recording completed successfully")

        # 2. transliteration
        print("\nstart transcribing...")
        transcriber = SpeechTranscriber()
        text = transcriber.transcribe("interview.wav")
        print(f"\ntransliteratio;n content: {text}")
        
        # 3. LLLM processing
        
        print("\nmodel reply:")
        full_response = []
        client.get_response(f"\n{text}", callback=update_response)


if __name__ == "__main__":
    main()