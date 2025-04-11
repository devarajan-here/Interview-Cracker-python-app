from openai import OpenAI
import sys
import os
import configparser

# Get the absolute path of the current file, move up one level, find config.ini using the absolute path, and read it
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
config_path = os.path.join(project_root, 'config.ini')
MYCONFIG = configparser.ConfigParser()
MYCONFIG.read(config_path, encoding='utf-8')

def update_response(new_text):
    # Callback function to update the response
    print(new_text, end="", flush=True, sep="")

class LLMClient:
    def __init__(self, api_url=MYCONFIG['DEFAULT']['API_URL'], api_key=MYCONFIG['DEFAULT']['API_KEY'], model=MYCONFIG['DEFAULT']['MODEL']):
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_url
        )
        self.model = model

    def get_response(self, prompt, callback=None):
        model = self.model
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        full_response = ""
        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                full_response += delta.content
                if callback:
                    callback(delta.content)
        return full_response
    


if __name__ == "__main__":
    # Ensure the SILICONFLOW_API_KEY environment variable is set
    client = LLMClient()
    
    print(client.get_response("Please act as a professional AI algorithm engineer who is knowledgeable about artificial intelligence. I am currently in an interview. The following text input comes from the interviewer's speech-to-text. Please fully understand and provide me with a suitable answer: In your model training process, how do you handle overfitting?", callback=update_response))
