import sys
import threading
import time
import ctypes

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout, QPushButton, QCheckBox, QTextBrowser, QLabel

import markdown2  # please use pip install markdown2 to install thsi package

from src.audio_capture import LoopbackRecorder
from src.transcriber import SpeechTranscriber
from src.llm_client import LLMClient
import os
import configparser

#Get the absolute path of the current file, go up one level, use the absolute path to find config.ini and read it

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
config_path = os.path.join(project_root, 'config.ini')
MYCONFIG = configparser.ConfigParser()
MYCONFIG.read(config_path,encoding='utf-8')

#
class RecorderThread(threading.Thread):
    def __init__(self, recorder, filename, duration=None):
        super().__init__()
        self.recorder = recorder
        self.filename = filename
        self.duration = duration

    def run(self):
        try:
            self.recorder.start_recording(self.filename)
            self.recorder.record(duration=self.duration)
        finally:
            self.recorder._cleanup()  # Free up resources in the same thread

# Leverage Windows APIs to prevent screen capture
def prevent_screen_capture(winId):
    try:
        WDA_MONITOR = 1  # Valid only on Windows systems that support the API
        ctypes.windll.user32.SetWindowDisplayAffinity(int(winId), WDA_MONITOR)
    except Exception as e:
        print("Screen saver setting failed:",e)

class InterviewAssistantGUI(QMainWindow):
    def __init__(self,config):
        super().__init__()
        self.setWindowTitle("Dev AI")
       #Set Icon
        self.setWindowIcon(QtGui.QIcon('logo.png'))
        self.setGeometry(100, 100, 1200, 900)
        # Create a central control and layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QGridLayout(central)
        
      # State variables and module initialization
        self.recorder = None
        self.recording_thread = None
        self.current_filename = ""
        self.llm_full_text = ""
        self.llm_client_ask_cnt = 1
        self.default_prompt = MYCONFIG['DEFAULT']['DEFAULT_PROMPT']
        
        self.transcriber = SpeechTranscriber()
        self.llm_client = LLMClient()  # Replace with your API key

# Buttons & Controls
        self.start_btn = QPushButton("Start recording")
        self.start_btn.clicked.connect(self.start_recording)
        layout.addWidget(self.start_btn, 0, 0)
        
        self.stop_btn = QPushButton("End Recording")
        self.stop_btn.clicked.connect(self.stop_recording)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn, 0, 1)
        
        self.transcribe_btn = QPushButton("Transfer text")
        self.transcribe_btn.clicked.connect(self.transcribe_audio)
        self.transcribe_btn.setEnabled(False)
        layout.addWidget(self.transcribe_btn, 0, 2)
        
        self.send_llm_btn = QPushButton("Send to LLM")
        self.send_llm_btn.clicked.connect(self.send_to_llm)
        self.send_llm_btn.setEnabled(False)
        layout.addWidget(self.send_llm_btn, 0, 3)
        
        self.auto_transcribe_chk = QCheckBox("Auto convert to text after ending the interview")
        self.auto_transcribe_chk.setChecked(True)
        layout.addWidget(self.auto_transcribe_chk, 1, 0, 1, 2)
        
        self.auto_send_llm_chk = QCheckBox("Auto send to LLM after conversion")
        self.auto_send_llm_chk.setChecked(True)
        layout.addWidget(self.auto_send_llm_chk, 1, 1, 1, 2)

        #Create a checkbox for whether or not to automatically scroll the scrollbar
        self.auto_scroll_chk = QCheckBox("Auto Scroll")
        self.auto_scroll_chk.setChecked(True)
        #Put it in the third column of the first row

        layout.addWidget(self.auto_scroll_chk, 1, 2,1,2)
        
        # Transcribe the text display area

        self.transcription_browser = QTextBrowser()
        self.transcription_browser.setPlaceholderText("The transcription will be displayed here...")
        #Set to editable

        self.transcription_browser.setReadOnly(False)
        #Set to draggable

        self.transcription_browser.setAcceptDrops(True)
        layout.addWidget(self.transcription_browser, 2, 0, 1, 4)
        # Altitude Fixed
        self.transcription_browser.setFixedHeight(150)  # Or use setMinimumHeight(150)
        # LLM Reply area: Markdown rendering is supported
        self.llm_response_browser = QTextBrowser()
        self.llm_response_browser.setPlaceholderText("LLM replies will be displayed here（to supportMarkdown）...")

        #Set to draggable
        self.llm_response_browser.setAcceptDrops(True)
        layout.addWidget(self.llm_response_browser, 3, 0, 1, 4)


        
        # Sets the slider behavior: the slider automatically scrolls to the latest llm_response output when it is at the bottom

        self.llm_response_browser.textChanged.connect(self.auto_scroll_llm_response)
        
        self.status_label = QLabel("ready")
        layout.addWidget(self.status_label, 4, 0, 1, 4)
        
        # Invoke anti-screen capture settings after the window is displayed (valid on Windows only)

        QTimer.singleShot(100, self.apply_screen_capture_protection)
    
    def auto_scroll_llm_response(self):
        cursor = self.llm_response_browser.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.llm_response_browser.setTextCursor(cursor)
        self.llm_response_browser.ensureCursorVisible()
    
    def apply_screen_capture_protection(self):
        if sys.platform.startswith("win"):
            prevent_screen_capture(self.winId())
    
    def start_recording(self):
        try:
            # Generate a unique file name for each recording
            filename = f"interview_{int(time.time())}.wav"
            #splicing MYCONFIG['DEFAULT']['OUTPUT_DIR']和filename
            filename = os.path.join(MYCONFIG['DEFAULT']['OUTPUT_DIR'],filename)
            print(f"start recording: {filename}")
            self.recorder = LoopbackRecorder(device_index=MYCONFIG['DEFAULT'].getint('SPEAKER_DEVICE_INDEX'))
            device_info = self.recorder.device_info
            self.recording_thread = RecorderThread(self.recorder, filename)
            self.recording_thread.start()
            self.current_filename = filename
            self.status_label.setText(f"recording...device：({device_info['index']})({device_info['name']})")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        except Exception as e:
            print(f"failed to start recording: {e}")
            self.status_label.setText("failed to start recording")
    
    def stop_recording(self):
        try:
            self.recorder.is_recording = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            # If the saved file size is 0, the recording failed
            if os.path.getsize(self.current_filename) < 1:
                self.status_label.setText("Recording failed：the file size may be no audio input and output")
                return
            self.recording_thread.join()
            self.status_label.setText("recording has stopped")

            self.transcribe_btn.setEnabled(True)
            if self.auto_transcribe_chk.isChecked():
                self.transcribe_audio()

        except Exception as e:
            print(f"failed to stop recording: {e}")
            self.status_label.setText("failed to stop recording")

    
    def transcribe_audio(self):
        self.transcription_browser.clear()
        self.status_label.setText("translating...")
        try:
            text = self.transcriber.transcribe(self.current_filename)
            self.transcription_browser.setPlainText(text)
            self.status_label.setText("transcription completed")
            self.send_llm_btn.setEnabled(True)
            self.transcribe_btn.setEnabled(False)
            if self.auto_send_llm_chk.isChecked():
                self.send_to_llm()
        except Exception as e:
            print(f"transcription failed: {e}")
            self.transcription_browser.setPlainText(f"transcription failed: {e}\n")
    
    def send_to_llm(self):
        self.status_label.setText("LLM thinking...")
        self.llm_response_browser.clear()
        transcription = self.transcription_browser.toPlainText().strip()
        # Stitch DEFAULT_PROMPT in front of the transcribed text
        transcription = f"{self.default_prompt}\n{transcription}"
        if not transcription:
            self.llm_response_browser.setPlainText("the transcribed text is empty，please transcribe the audio first\n")
            return
        threading.Thread(target=self.llm_thread, args=(transcription,), daemon=True).start()
    
    def llm_thread(self, text):
        # Callback function: Accumulate the text returned by the stream and convert it to HTML with markdown2 to update the interface
        def update_ui(new_text):
            self.llm_full_text += new_text
            html = markdown2.markdown(self.llm_full_text)
            # Use QueuedConnection to ensure thread-safe updates
            QtCore.QMetaObject.invokeMethod(
                self.llm_response_browser, "setHtml", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, html)
            )
        
        try:
            # to display the invocation count in the reply box

            self.llm_client.get_response(text, callback=update_ui)
        except Exception as e:
            QtCore.QMetaObject.invokeMethod(
                self.llm_response_browser, "append", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, f"\nLLM call failed: {e}")
            )
        self.status_label.setText("LLM processing completed")
        # display certain invocation counts in the response box with a divider using markdown.
        divider = f"\n\n**No. {self.llm_client_ask_cnt} call completed**\n\n---\n"
        self.llm_full_text += divider
        html = markdown2.markdown(self.llm_full_text)
        QtCore.QMetaObject.invokeMethod(
            self.llm_response_browser, "setHtml", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, html)
        )

        
        self.llm_client_ask_cnt += 1

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = InterviewAssistantGUI(MYCONFIG)
    window.show()
    sys.exit(app.exec_())