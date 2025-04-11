# The model file is automatically downloaded on the first run
import whisper
from whisper.utils import get_writer
import os
import configparser

#Obtain the absolute path of the current file, go up one level, find the config.ini with the absolute path, and read it
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
config_path = os.path.join(project_root, 'config.ini')
MYCONFIG = configparser.ConfigParser()
MYCONFIG.read(config_path,encoding='utf-8')


class SpeechTranscriber:
    def __init__(self, model_size=MYCONFIG['DEFAULT']['WHISPER_MODEL_SIZW']):
        self.model = whisper.load_model(model_size)
        
    def transcribe(self, audio_path):
        #Determine whether the size of the audio file is less than 1 byte

        if os.path.getsize(audio_path) < 1:
            return "The audio file size is 0"
        result = self.model.transcribe(audio_path)
        return result["text"]

if __name__ == "__main__":
    transcriber = SpeechTranscriber()
    text = transcriber.transcribe("output/test_record.wav")
    print("Transcribe the results:", text)
