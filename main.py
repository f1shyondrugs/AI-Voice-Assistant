import openai
import sys
import json
import speech_recognition as sr
import pyttsx3
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel, QWidget, QSystemTrayIcon, QMenu, QAction, QGraphicsDropShadowEffect, QLineEdit, QProgressBar
from PyQt5.QtGui import QColor, QPalette, QIcon, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from pynput import keyboard
import gtts
import os
import pygame

# Load OpenAI API Key
with open('creds.json', 'r') as f:
    openai.api_key = str(json.load(f)['API-KEY'])

recognizer = sr.Recognizer()
microphone = sr.Microphone()
is_recording = False
text_buffer = ""

class Communicate(QObject):
    text_appended = pyqtSignal(str)

com = Communicate()


is_loading = False

def send_to_openai(prompt):
    global is_loading
    is_loading = True
    update_ui_for_loading()
    
    try:
        print("Sending prompt to OpenAI...")
        # Load API key from the same JSON file
        with open('creds.json', 'r') as f:
            api_key = json.load(f)['API-KEY']
        
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        print("Received response from OpenAI")
        return response.choices[0].message.content.strip()
    finally:
        is_loading = False
        update_ui_for_loading()

def update_ui_for_loading():
    # Disable/enable buttons based on loading state
    start_button.setEnabled(not is_loading)
    stop_button.setEnabled(not is_loading)
    edit_button.setEnabled(not is_loading)
    
    # Update progress bar
    progress_bar.setVisible(is_loading)
    if is_loading:
        progress_animation()

def progress_animation():
    if is_loading:
        current_value = progress_bar.value()
        next_value = (current_value + 10) % 100
        progress_bar.setValue(next_value)
        # Schedule next update
        QTimer.singleShot(100, progress_animation)

def process_audio(audio):
    global text_buffer
    try:
        text = recognizer.recognize_google(audio, language='en-US')
        print(f"Recognized text: {text}")
        # Update both text areas
        com.text_appended.emit(text)
        # Set the recognized text as the prompt input
        prompt_input.setText(text)
    except sr.UnknownValueError:
        print("Speech Recognition could not understand audio")
        com.text_appended.emit(" [unintelligible] ")
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        com.text_appended.emit(" [error] ")








def start_recording():
    global is_recording
    is_recording = True
    threading.Thread(target=record_voice).start()

def stop_recording():
    global is_recording
    is_recording = False

def record_voice():
    global is_recording, text_buffer
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Recording started...")
        while is_recording:
            try:
                audio = recognizer.listen(source, timeout=2, phrase_time_limit=2)
                threading.Thread(target=process_audio, args=(audio,)).start()
            except sr.WaitTimeoutError:
                continue



def append_text(text):
    global text_buffer
    text_buffer += text + " "
    response_textbox.setPlainText(text_buffer)

def save_response_to_file(response, filename="response.txt"):
    with open(filename, 'w') as file:
        file.write(response)
    print(f"Response saved to {filename}")

def read_response_aloud(response):
    try:
        # Create a temporary MP3 file
        tts = gtts.gTTS(response, lang='en')
        temp_file = 'response.mp3'
        tts.save(temp_file)
        
        # Initialize pygame mixer
        pygame.mixer.init()
        
        # Play the audio
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        # Clean up
        pygame.mixer.music.unload()
        os.remove(temp_file)
    
    except Exception as e:
        print(f"Error in text-to-speech: {e}")

def get_final_response():
    # First check the manual prompt input
    manual_input = prompt_input.text().strip()
    
    if manual_input:
        response = send_to_openai(manual_input)
        save_response_to_file(response)
        
        # Update the response textbox
        response_textbox.setPlainText(response)
        
        show_response_window(response)
        read_response_aloud(response)
        
        
        # Clear the manual input box after sending
        prompt_input.clear()

def show_response_window(response):
    response_window = QMainWindow()
    response_window.setWindowTitle("Response")

    central_widget = QWidget()
    response_window.setCentralWidget(central_widget)

    layout = QVBoxLayout()
    central_widget.setLayout(layout)

    response_label = QLabel(response)
    response_label.setStyleSheet("""
        background-color: #1E1E2C;
        color: white;
        padding: 15px;
        border-radius: 10px;
    """)
    layout.addWidget(response_label)

    response_window.resize(400, 200)
    response_window.show()

def toggle_window():
    if window.isVisible():
        window.hide()
    else:
        window.show()
        app.setQuitOnLastWindowClosed(False)
        tray_icon.setVisible(True)

def create_styled_button(text):
    button = QPushButton(text)
    button.setStyleSheet("""
        QPushButton {
            background-color: #2C3E50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #34495E;
        }
        QPushButton:pressed {
            background-color: #1E2A38;
        }
    """)
    
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(15)
    shadow.setColor(QColor(0, 0, 0, 80))
    shadow.setOffset(3, 3)
    button.setGraphicsEffect(shadow)
    
    return button

def create_styled_textbox():
    textbox = QTextEdit()
    textbox.setStyleSheet("""
        QTextEdit {
            background-color: #1E1E2C;
            color: white;
            border: 2px solid #2C3E50;
            border-radius: 10px;
            padding: 10px;
            font-size: 14px;
        }
    """)
    textbox.setPlaceholderText("Here will be the response...")
    return textbox

def create_styled_prompt_input():
    prompt_input = QLineEdit()
    prompt_input.setStyleSheet("""
        QLineEdit {
            background-color: #1E1E2C;
            color: white;
            border: 2px solid #2C3E50;
            border-radius: 10px;
            padding: 10px;
            font-size: 14px;
        }
    """)
    prompt_input.setPlaceholderText("Type your prompt here...")
    return prompt_input

# GUI
app = QApplication(sys.argv)
app.setStyle("Fusion")

window = QMainWindow()
window.setWindowTitle("Voice Assistant")
window.resize(500, 400)
window.setStyleSheet("background-color: #0A0A1A;")
window.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)

central_widget = QWidget()
window.setCentralWidget(central_widget)

layout = QVBoxLayout()
central_widget.setLayout(layout)

# Title Label
title_label = QLabel("Voice Assistant")
title_label.setAlignment(Qt.AlignCenter)
title_label.setStyleSheet("""
    color: #2C3E50;
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 20px;
""")
layout.addWidget(title_label)

# Prompt Input Section
prompt_input_layout = QHBoxLayout()
layout.addLayout(prompt_input_layout)

prompt_input = create_styled_prompt_input()
prompt_input_layout.addWidget(prompt_input)

buttons_layout = QHBoxLayout()
layout.addLayout(buttons_layout)

# Styled Buttons
start_button = create_styled_button("Start Recording")
start_button.clicked.connect(start_recording)
buttons_layout.addWidget(start_button)

stop_button = create_styled_button("Stop Recording")
stop_button.clicked.connect(stop_recording)
buttons_layout.addWidget(stop_button)

edit_button = create_styled_button("Get Response")
edit_button.clicked.connect(get_final_response)
buttons_layout.addWidget(edit_button)

# Styled Response Textbox
response_textbox = create_styled_textbox()
layout.addWidget(response_textbox)

# System Tray Icon
tray_icon = QSystemTrayIcon(QIcon("icon.png"), parent=app)
tray_icon.setToolTip("Voice Assistant")
tray_icon.activated.connect(toggle_window)

progress_bar = QProgressBar()
progress_bar.setStyleSheet("""
    QProgressBar {
        border: 2px solid #2C3E50;
        border-radius: 5px;
        text-align: center;
    }
    QProgressBar::chunk {
        background-color: #2C3E50;
    }
""")
progress_bar.setTextVisible(False)
progress_bar.setVisible(False)
layout.addWidget(progress_bar)


menu = QMenu()
open_action = QAction("Open", parent=app)
open_action.triggered.connect(toggle_window)
menu.addAction(open_action)

quit_action = QAction("Quit", parent=app)
quit_action.triggered.connect(app.quit)
menu.addAction(quit_action)

tray_icon.setContextMenu(menu)
tray_icon.show()

# Global Hotkey Setup
def for_canonical(f):
    return lambda k: f(listener.canonical(k))

listener = keyboard.GlobalHotKeys({
    '<ctrl>+<alt>+a': toggle_window
})
listener.start()

# Connect text appending signal
com.text_appended.connect(append_text)

# Run the application
window.show()
window.raise_()
window.activateWindow()
    
sys.exit(app.exec_())


































































xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx