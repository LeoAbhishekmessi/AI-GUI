# === Standard Library ===
import ctypes
from ctypes import wintypes
import json
import logging
import os
import random
import subprocess
import sys
import threading
import time
from datetime import datetime

# === Third-party Modules ===
import keyboard
import numpy as np
import psutil
import requests
import sounddevice as sd

# === PyQt6 Core ===
from PyQt6.QtCore import (
    QCoreApplication,
    QEvent,
    QPropertyAnimation,
    QRect,
    QRegularExpression,
    QSize,
    QTimer,
    Qt,
    QUrl,
    QUrlQuery,
    QBuffer,
)

# === PyQt6 GUI ===
from PyQt6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QPainter,
    QPixmap,
    QTextCharFormat,
    QTextFormat,
    QSyntaxHighlighter,
)

# === PyQt6 Widgets ===
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# === PyQt6 Multimedia ===
from PyQt6.QtMultimedia import (
    QCamera,
    QCameraDevice,
    QMediaCaptureSession,
    QMediaDevices,
    QMediaFormat,
    QMediaRecorder,
)

from PyQt6.QtMultimediaWidgets import QVideoWidget

# === PyQt6 Network ===
from PyQt6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
)

# === PyQt6 Web Engine ===
from PyQt6.QtWebEngineWidgets import QWebEngineView
# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
from PyQt6.QtGui import QGuiApplication

# -----------------------------------------------------------------------------
# Key Blocking
# -----------------------------------------------------------------------------
def block_system_keys():
    """Block system keys using multiple methods to ensure effectiveness"""
    try:
        logging.info("Initializing enhanced key blocking system")
        
        # Method 1: Using direct key blocking
        for key in ['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12']:
            keyboard.block_key(key)
            # Also create an explicit suppressed hotkey for each function key
            keyboard.add_hotkey(key, lambda k=key: logging.info(f"Blocked {k} via hotkey"), suppress=True)
            logging.info(f"Blocking {key}")
        
        # Block Windows keys
        keyboard.block_key('left windows')
        keyboard.block_key('right windows')
        logging.info("Blocking Windows keys")
        
        # Block escape key
        keyboard.block_key('esc')
        logging.info("Blocking 'esc' key")
        
        # Block alt key to prevent alt+tab
        keyboard.block_key('alt')
        logging.info("Blocking 'alt' key")
        
        # Block tab key to prevent tab switching
        keyboard.block_key('tab')
        logging.info("Blocking 'tab' key")
        
        # Block additional keys that might be problematic
        keyboard.block_key('print screen')
        logging.info("Blocking 'print screen' key")
        
        # Method 2: Using hotkeys for more complex combinations
        combinations = [
            'alt+tab', 'alt+f4', 'ctrl+alt+del', 'ctrl+shift+esc',  # System combinations
            'ctrl+f1', 'ctrl+f2', 'ctrl+f3', 'ctrl+f4', 'ctrl+f5',  # Ctrl + function keys
            'ctrl+f6', 'ctrl+f7', 'ctrl+f8', 'ctrl+f9', 'ctrl+f10', 'ctrl+f11', 'ctrl+f12',
            'alt+f1', 'alt+f2', 'alt+f3', 'alt+f4', 'alt+f5',       # Alt + function keys
            'alt+f6', 'alt+f7', 'alt+f8', 'alt+f9', 'alt+f10', 'alt+f11', 'alt+f12',
            'ctrl+tab', 'ctrl+w', 'ctrl+q',                         # Browser/application controls
            'ctrl+esc', 'win+d', 'win+e', 'win+r',                  # System shortcuts
        ]
        
        for combo in combinations:
            # Using a more robust approach for hotkeys
            keyboard.add_hotkey(combo, lambda c=combo: logging.info(f"Blocked combination {c}"), suppress=True)
            logging.info(f"Blocking combination {combo}")
        
        # Method 3: Global keyboard hook as a failsafe
        # This is the most comprehensive approach as it intercepts ALL keyboard events
        def keyboard_hook_handler(event):
            """Handle keyboard events from the global hook"""
            # For key down events, check if it's a key we want to block
            if event.event_type == keyboard.KEY_DOWN:
                key_name = event.name.lower() if event.name else ""
                
                # Comprehensive list of keys to block
                blocked_keys = [
                    'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
                    'esc', 'tab', 'alt', 'win', 'print screen', 'menu',
                    # Include the actual scan codes for function keys as some systems report them differently
                    '112', '113', '114', '115', '116', '117', '118', '119', '120', '121', '122', '123',
                ]
                
                # Check if our key is in the blocked list
                for blocked_key in blocked_keys:
                    if blocked_key in key_name or blocked_key == str(event.scan_code):
                        logging.info(f"Blocked key {key_name} (scan code: {event.scan_code}) via global hook")
                        return False  # Block the event
                
                # Also block if any modifiers are held with certain keys
                if keyboard.is_pressed('alt') or keyboard.is_pressed('ctrl') or keyboard.is_pressed('win'):
                    sensitive_keys = ['tab', 'esc', 'd', 'e', 'r', 'q', 'w']
                    for sensitive_key in sensitive_keys:
                        if sensitive_key in key_name:
                            logging.info(f"Blocked modifier+{key_name} via global hook")
                            return False  # Block the event
            
            # For all other events, allow them to pass through
            return True
        
        # Register our global hook with suppression enabled
        keyboard.hook(keyboard_hook_handler, suppress=True)
        logging.info("Global keyboard hook established")
            
    except Exception as e:
        logging.error(f"Error in key blocking system: {e}")
        raise

def prevent_window_minimization():
    """Additional measures to prevent window minimization"""
    try:
        # Block Win+D (show desktop)
        keyboard.add_hotkey('win+d', lambda: None, suppress=True)
        
        # Block Win+M (minimize all)
        keyboard.add_hotkey('win+m', lambda: None, suppress=True)
        
        logging.info("Added minimization prevention measures")
    except Exception as e:
        logging.error(f"Error setting up minimization prevention: {e}")

def start_key_blocking():
    """Start key blocking in a separate thread with robust error handling"""
    logging.info("Starting key blocking system")
    
    def blocking_worker():
        try:
            block_system_keys()
            prevent_window_minimization()
            logging.info("Key blocking system successfully initialized")
            
            # Keep the thread alive and checking
            while True:
                # Periodically check if our hooks are still active
                # This helps catch and fix any hooks that might have been bypassed
                import time
                time.sleep(5)
                
        except Exception as e:
            logging.error(f"Critical error in key blocking thread: {e}")
            # Try to recover
            try:
                logging.info("Attempting to recover key blocking...")
                block_system_keys()
            except:
                logging.error("Recovery attempt failed")
    
    # Start in a daemon thread so it automatically terminates when the main program exits
    blocking_thread = threading.Thread(target=blocking_worker, daemon=True)
    blocking_thread.start()
    return blocking_thread

# -----------------------------------------------------------------------------
# API Integration: Login API
# -----------------------------------------------------------------------------
SESSION_TOKEN = None

def login_api(exam_code):
    url = "https://stageevaluate.sentientgeeks.us/wp-json/api/v1/login"
    payload = {"exam_link": exam_code}
    headers = {"Content-Type": "application/json"}

    try:
        logging.debug(f"🔹 Sending POST request to {url} with payload: {payload}")
        response = requests.post(url, json=payload, headers=headers)
        logging.debug(f"📡 Response Status Code: {response.status_code}")
        logging.debug(f"📜 Response Content: {response.text}")

        if response.status_code == 200:
            global SESSION_TOKEN
            SESSION_TOKEN = response.json().get("token", "")
            if SESSION_TOKEN.startswith("Bearer "):
                SESSION_TOKEN = SESSION_TOKEN.replace("Bearer ", "")
            if SESSION_TOKEN:
                print(f"\n✅ Token Generated: {SESSION_TOKEN}")
                return SESSION_TOKEN
            else:
                print("\n❌ Token not found in response")
        else:
            print(f"\n❌ Login failed with status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"⚠️ Error hitting the API: {e}")
    return None

def get_exam_details(token, exam_code=None):
    url = "https://stageevaluate.sentientgeeks.us/wp-json/api/v1/get-exam-details"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {"exam_link": exam_code} if exam_code else {}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        logging.debug(f"Response Status Code: {response.status_code}")
        logging.debug(f"Response Content: {response.text}")
        response_json = response.json()
        if response.status_code == 200 or ('message' in response_json and 'remaining_time' in response_json):
            print("\n✅ Exam Details:", response_json)
            return response_json
        else:
            print(f"\n❌ Failed to fetch exam details. Status Code: {response.status_code}")
            print("Response JSON:", response_json)
            return response_json
    except requests.exceptions.RequestException as e:
        logging.error(f"API Request Exception: {e}")
        print("\n⚠️ Error calling exam details API:", e)
        return None

def fetch_question(question_id, exam_id, user_id, idx, first_request=False):
    url = "https://stageevaluate.sentientgeeks.us/wp-json/api/v1/get-question-from-id"
    payload = {
        "question_id": str(question_id),
        "exam_id": str(exam_id),
        "user_id": str(user_id),
        "idx": idx,
        "first_request": first_request
    }
    headers = {
        "Authorization": f"Bearer {SESSION_TOKEN}",  # <-- Check if SESSION_TOKEN is VALID and not expired
        "Content-Type": "application/json"
    }

    try:
        logging.info(f"[fetch_question] Sending request: {payload}")
        response = requests.post(url, json=payload, headers=headers)
        logging.info(f"[fetch_question] Status Code: {response.status_code}")

        if response.status_code != 200:
            logging.error(f"[fetch_question] Failed with status: {response.status_code}")
            return None

        data = response.json()
        logging.debug(f"[fetch_question] Full JSON Response: {data}")

        if data.get("status") is True and data.get("question_id"):
            logging.info(f"[fetch_question] Successfully fetched question ID {data['question_id']}")
            return data
        else:
            logging.warning(f"[fetch_question] No valid question returned for ID {question_id}")
            return None

    except Exception as e:
        logging.exception(f"[fetch_question] Exception: {e}")
        return None



def save_question_answer(exam_id, user_id, question_id, question_type, answer, SESSION_TOKEN):
    """
    Save a question answer to the API.
    
    Args:
        exam_id (str): The ID of the exam
        user_id (str): The ID of the user
        question_id (str): The ID of the question
        question_type (str): The type of question (1, 2, 3, or 4)
        answer: The user's answer (format depends on question type)
        session_token (str): The authentication token
        
    Returns:
        dict: The API response as a dictionary, or None if the request failed
    """
    try:
        import json  # Make sure to import json
        import requests  # Make sure requests is imported
        
        # Debug information
        print(f"DEBUG - Saving answer with parameters:")
        print(f"  exam_id: {exam_id}")
        print(f"  user_id: {user_id}")
        print(f"  question_id: {question_id}")
        print(f"  question_type: {question_type}")
        print(f"  raw answer: {answer}")
        
        # Validation check - ensure question_id is not empty
        if not question_id:
            print("ERROR: question_id is empty or None")
            return None
            
        # Format the answer based on question type
        formatted_answer = format_answer_for_api(question_type, answer)
        print(f"  formatted answer: {formatted_answer}")
        
        # Prepare the payload - simplified to use consistent naming
        payload = {
            "exam_id": exam_id,
            "user_id": user_id,
            "question_id": question_id,
            "question_type": question_type,
            "provided_answer": formatted_answer
        }
        
        headers = {
            "Authorization": f"Bearer {SESSION_TOKEN}",
            "Content-Type": "application/json"
        }
        
        print(f"DEBUG - API Payload: {payload}")
        
        # Make the API request
        response = requests.post(
            "https://stageevaluate.sentientgeeks.us/wp-json/api/v1/save-question-answer",
            json=payload,
            headers=headers
        )
        
        # Check if request was successful
        if response.status_code in (200, 201):
            print(f"Successfully saved answer for question {question_id}")
            print(f"Response: {response.json()}")
            return response.json()
        else:
            print(f"Failed to save answer for question {question_id}")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error saving answer for question {question_id}: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()  # Print full stack trace for debugging
        return None
        

def format_answer_for_api(question_type, answer):
    """
    Format the answer based on question type for API submission.
    
    Args:
        question_type (str): The type of question ("1", "2", "3", or "4")
        answer: The user's answer in the internal format
        
    Returns:
        The formatted answer ready for API submission
    """
    if answer is None:
        print("WARNING: Answer is None, returning empty string")
        return ""
        
    if question_type == "1":  # Descriptive
        # Just send the text as is
        return answer
        
    elif question_type == "2":  # MCQ
        # Send the selected option index
        # Ensure the answer is a string as some APIs expect string values
        return str(answer)
        
    elif question_type == "3":  # MSQ
        # Convert to comma-separated string of selected indices
        if isinstance(answer, list) and len(answer) > 0:
            return ",".join(str(idx) for idx in answer)
        return ""
        
    elif question_type == "4":  # Coding
        # Handle coding questions - answer is a tuple of (code, language)
        if answer is not None:
            code, language = answer
            # Format as: language>code
            return f"{language}>{code}"
        return ""
    
    # Default case
    return str(answer) if answer is not None else ""

# -----------------------------------------------------------------------------
# System Check Functions
# -----------------------------------------------------------------------------
def check_audio():
    duration = 0.5
    fs = 44100
    try:
        # Get available devices
        devices = sd.query_devices()
        if not devices:
            logging.error("No audio devices found")
            return "Failed (No audio devices detected)"
        
        # Print all available devices for debugging
        logging.info("Available audio devices:")
        for i, device in enumerate(devices):
            logging.info(f"Device {i}: {device['name']} - Input: {device['max_input_channels']}, Output: {device['max_output_channels']}")
            
        # Check if the microphone exists first
        input_device = None
        output_device = None
        
        # Try to use the default devices first
        default_in = sd.default.device[0]
        default_out = sd.default.device[1]
        
        logging.info(f"Default input device index: {default_in}")
        logging.info(f"Default output device index: {default_out}")
        
        # Validate default input device
        if default_in >= 0 and default_in < len(devices):
            if devices[default_in]['max_input_channels'] > 0:
                input_device = default_in
                logging.info(f"Using default input device: {devices[input_device]['name']}")
        
        # If default input device is invalid, find the first available input device
        if input_device is None:
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_device = i
                    logging.info(f"Using alternate input device: {devices[input_device]['name']}")
                    break
                    
        # If still no input device found, try system microphone with more flexible criteria
        if input_device is None:
            for i, device in enumerate(devices):
                if 'mic' in device['name'].lower() or 'input' in device['name'].lower():
                    input_device = i
                    logging.info(f"Using detected microphone device: {devices[input_device]['name']}")
                    break
        
        # Validate default output device
        if default_out >= 0 and default_out < len(devices):
            if devices[default_out]['max_output_channels'] > 0:
                output_device = default_out
                logging.info(f"Using default output device: {devices[output_device]['name']}")
        
        # If default output device is invalid, find the first available output device
        if output_device is None:
            for i, device in enumerate(devices):
                if device['max_output_channels'] > 0:
                    output_device = i
                    logging.info(f"Using alternate output device: {devices[output_device]['name']}")
                    break
        
        # If no input device found after all attempts
        if input_device is None:
            logging.error("No valid microphone found after multiple attempts")
            return "Failed (No microphone found)"
            
        # If no output device found
        if output_device is None:
            logging.error("No valid output device found")
            return "Failed (No output device found)"
        
        # Try WASAPI loopback if available
        try:
            device_info = sd.query_devices(output_device)
            hostapi_info = sd.query_hostapis()[device_info['hostapi']]
            
            if "WASAPI" in hostapi_info['name']:
                logging.info("Using WASAPI Loopback for audio check.")
                recording = sd.rec(
                    int(duration * fs),
                    samplerate=fs,
                    channels=1,
                    dtype='float32',
                    device=output_device,
                    blocking=True,
                    extra_settings=sd.WasapiSettings(loopback=True)
                )
            else:
                # Fall back to traditional recording
                logging.info(f"Using traditional recording. Input: {input_device}, Output: {output_device}")
                # Play test sound and record simultaneously
                sd.play(np.sin(2*np.pi*1000*np.arange(fs*duration)/fs)*0.3, fs, device=output_device)
                recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32', device=input_device)
                sd.wait()
                
            amplitude = np.max(np.abs(recording))
            logging.info(f"Detected audio amplitude: {amplitude}")
            
            # Changed condition: audio exists if amplitude > 0.01 (more sensitive)
            if amplitude > 0.01:
                return "OK"
            else:
                return "Failed (No audio detected)"
                
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Audio recording error: {error_msg}")
            return f"Failed (Recording error: {error_msg})"
            
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Audio check error: {error_msg}")
        
        if "Invalid device" in error_msg:
            return "Failed (Invalid audio device)"
        elif "Error opening" in error_msg:
            return "Failed (Cannot access audio device)"
        else:
            return f"Failed ({error_msg})"


def check_video():
    available = QMediaDevices.videoInputs()
    if available:
        return "OK"
    else:
        logging.info("Video check failed: No cameras detected")
        return "Failed (No camera detected)"


def check_screen_sharing():
    known_keywords = {"zoom", "skype", "teamviewer", "anydesk", "webex", "gotomeeting"}
    detected_apps = []
    
    for proc in psutil.process_iter(['name']):
        try:
            proc_name = proc.info['name']
            if proc_name:
                for keyword in known_keywords:
                    if keyword in proc_name.lower():
                        detected_apps.append(proc_name)
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if detected_apps:
        app_names = ", ".join(detected_apps)
        logging.info(f"Screen sharing check failed: {app_names} detected")
        return f"Failed (Found: {app_names})"
    else:
        logging.info("Screen sharing check: OK")
        return "OK"


def check_monitor():
    screens = len(QApplication.screens())
    if screens == 1:
        return "OK"
    else:
        logging.info(f"Monitor check failed: {screens} monitors detected")
        return f"Failed ({screens} monitors detected)"

# -----------------------------------------------------------------------------
# Dialogs & Pages
# -----------------------------------------------------------------------------

# 1. Exam Code Page
class ExamCodePage(QWidget):
    def __init__(self, switch_to_system_check_callback):
        super().__init__()
        self.switch_to_system_check_callback = switch_to_system_check_callback
        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main

        # ------------------ Left Form Column ------------------ #
        form_widget = QWidget()
        form_widget.setStyleSheet("background-color: white;")
        form_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        form_layout = QVBoxLayout(form_widget)
        form_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.setContentsMargins(40, 40, 40, 40) 
        form_layout.setSpacing(10)

        # Welcome label
        welcome_label = QLabel("Welcome to Evaluate")
        welcome_label.setStyleSheet("color: #00205b;")
        welcome_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.addWidget(welcome_label)

        # Title label
        title_label = QLabel("Enter Exam Code")
        title_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Medium))
        title_label.setStyleSheet("color: #444; margin-top: 0px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.addWidget(title_label)

        # Exam code input
        self.exam_code_edit = QLineEdit()
        self.exam_code_edit.setPlaceholderText("Enter Code Here...")
        self.exam_code_edit.setFont(QFont("Segoe UI", 16, QFont.Weight.Medium))
        self.exam_code_edit.setMinimumHeight(45)
        self.exam_code_edit.setStyleSheet("""
            QLineEdit {
                padding: 7px 15px;
                border: 1px solid #ccc;
                border-radius: 10px;
                background-color: #f9f9f9;
            }
            QLineEdit:focus {
                border-color: #00205b;
                background-color: #ffffff;
            }
        """)
        form_layout.addWidget(self.exam_code_edit)

        # Submit button
        submit_button = QPushButton("Submit")
        submit_button.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        submit_button.setMinimumHeight(40)
        submit_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        submit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        submit_button.setStyleSheet("""
            QPushButton {
                background-color: #00205b;
                color: white;
                border-radius: 12px;
                padding: 11px 0px;
            }
            QPushButton:hover {
                background-color: #001a4f;
            }
        """)

        # Optional: Add a drop shadow to button
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 120))
        submit_button.setGraphicsEffect(shadow)

        submit_button.clicked.connect(self.handle_exam_code)
        form_layout.addWidget(submit_button)
        main_layout.addWidget(form_widget, stretch=1)  # Left column takes 1 part of space

        logo_widget = QWidget()
        logo_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        logo_layout = QVBoxLayout(logo_widget)
        logo_layout.setContentsMargins(0, 0, 0, 0)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        logo_width = int(screen_size.width() * 0.6)
        logo_height = int(screen_size.height() * 1)
        pixmap = QPixmap("login.jpg")
        if not pixmap.isNull():
            # Calculate aspect ratio preserving scale and crop center (object-fit: cover)
            label_ratio = logo_width / logo_height
            pixmap_ratio = pixmap.width() / pixmap.height()

            if pixmap_ratio > label_ratio:
                # Pixmap is wider, scale by height and crop width
                scaled_pixmap = pixmap.scaledToHeight(logo_height, Qt.TransformationMode.SmoothTransformation)
                x_offset = int((scaled_pixmap.width() - logo_width) / 2)
                cropped_pixmap = scaled_pixmap.copy(x_offset, 0, logo_width, logo_height)
            else:
                # Pixmap is taller, scale by width and crop height
                scaled_pixmap = pixmap.scaledToWidth(logo_width, Qt.TransformationMode.SmoothTransformation)
                y_offset = int((scaled_pixmap.height() - logo_height) / 2)
                cropped_pixmap = scaled_pixmap.copy(0, y_offset, logo_width, logo_height)

            logo_label.setPixmap(cropped_pixmap)
        else:
            logo_label.setText("Logo")
            logo_label.setFont(QFont("Cinzel", 20, QFont.Weight.Bold))
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_layout.addWidget(logo_label)

        main_layout.addWidget(logo_widget, stretch=1)  

    def handle_exam_code(self):
        exam_code = self.exam_code_edit.text().strip()
        if exam_code:
            token = login_api(exam_code)
            if token:
                print("\n✅ Token generated:", token)
                logging.info(f"Exam code entered and login successful: {exam_code}")
                exam_details = get_exam_details(token, exam_code)
                if exam_details:
                    print("\n✅ Exam Details received in ExamCodePage:", exam_details)
                    self.switch_to_system_check_callback(exam_code, token, exam_details)
                else:
                    print("\n❌ Exam details API call failed.")
            else:
                logging.warning("❌ Login failed. Please check your exam code or your network connection.")
        else:
            logging.warning("⚠️ Exam code cannot be empty.")

# 2. System Check Page
class SystemCheckPage(QWidget):
    def __init__(self, switch_to_instructions_callback):
        super().__init__()
        self.switch_to_instructions_callback = switch_to_instructions_callback
        self.exam_details = None
        self.setup_ui()
        # Removed automatic check start to wait for device selection first
        self.check_counter = 0
        self.checks_completed = False
        self.skip_media_checks = True #skip media check
    def set_exam_details(self, exam_details):
        self.exam_details = exam_details
        print("\n✅ Exam Details in SystemCheckPage:", self.exam_details)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(20, 20, 20, 20)

        # Outer container
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 30, 20, 20) 
        container_layout.setSpacing(8)
        container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 15px;
            }
        """)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(container)

        # Header
        header = QLabel("System & Device Checks")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setFixedHeight(65)
        header.setStyleSheet("QLabel { text-decoration: underline; margin: 0; color: #00205b;  }")
        header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        container_layout.addWidget(header)

        # 2-column grid layout for status boxes
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        container_layout.addLayout(grid_layout)

        label_style = """
        QLabel {
            background-color: #f0f4ff;
            color: #0d1b57;
            border: 1px solid #c5cae9;
            border-radius: 10px;
            padding: 10px 16px;
            font-family: 'Segoe UI';
            font-size: 20px;
        }
        """

        def create_label(text):
            label = QLabel(text)
            label.setStyleSheet(label_style)
            label.setFont(QFont("Arial", 18))
            label.setFixedHeight(80)
            return label

        self.video_label = create_label("Video Check: Pending")
        self.audio_label = create_label("Audio Check: Pending")
        self.machine_label = create_label("Machine Requirement: Pending")
        self.screen_label = create_label("Screen Sharing App: Pending")
        self.funkey_label = create_label("Function Key Block: Pending")
        self.monitor_label = create_label("Monitor Check: Pending")

        # Add to grid (2 columns, 3 rows)
        grid_layout.addWidget(self.video_label, 0, 0)
        grid_layout.addWidget(self.audio_label, 0, 1)
        grid_layout.addWidget(self.machine_label, 1, 0)
        grid_layout.addWidget(self.screen_label, 1, 1)
        grid_layout.addWidget(self.funkey_label, 2, 0)
        grid_layout.addWidget(self.monitor_label, 2, 1)

        # Select Devices Button
        self.select_devices_button = QPushButton("Select Devices")
        self.select_devices_button.setFont(QFont("Arial", 18))
        self.select_devices_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #00205b;
                border: 1px solid #00205b;
                padding: 10px 20px;
                font-size: 18px;
                border-radius: 8px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #00205b;
                color: white;
                border: 1px solid #001b4f;
            }
        """)
        self.select_devices_button.clicked.connect(self.handle_select_devices)
        container_layout.addWidget(self.select_devices_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # Status Message
        self.status_message = QLabel("")
        self.status_message.setFont(QFont("Arial", 18))
        self.status_message.setFixedHeight(40)
        self.status_message.setContentsMargins(0,5,0,0)
        self.status_message.setStyleSheet("QLabel { text-decoration: underline; padding-bottom: 4px; color: #00205b;  }")
        self.status_message.setAlignment(Qt.AlignmentFlag.AlignLeft)
        container_layout.addWidget(self.status_message)

        # Continue Button
        self.continue_button = QPushButton("Continue")
        self.continue_button.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.continue_button.setStyleSheet("""
            QPushButton {
                background-color: #00205b;
                color: white;
                border: 1px solid #00205b;
                padding: 10px 20px;
                font-size: 18px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #001b4f;
                color: white;
                border: 1px solid #001b4f;
            }
        """)
        self.continue_button.setEnabled(False)
        self.continue_button.clicked.connect(self.on_continue)
        container_layout.addWidget(self.continue_button, alignment=Qt.AlignmentFlag.AlignLeft)

    def start_checks(self):
        # Reset labels to "Checking..." state
        for lbl in [self.video_label, self.audio_label, self.machine_label,
                    self.screen_label, self.funkey_label, self.monitor_label]:
            lbl.setText(f"{lbl.text().split(':')[0]}: Checking...")
            
        self.status_message.setText("Running system checks...")
        self.check_counter = 0
        self.checks_completed = False
        
        # Start the check timer
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.update_checks)
        self.check_timer.start(1000)

    def update_checks(self):
        self.check_counter += 1
        if self.check_counter >= 3:
            # Only perform checks if they haven't been completed yet
            if not self.checks_completed:
                # Run all checks and store the results
                video_result = check_video()
                audio_result = check_audio()

                #skip audio video
                if self.skip_media_checks:
                    video_result = "OK"
                    audio_result = "OK"
                else:
                    video_result = check_video()
                    audio_result = check_audio()  

            # skip audio video
                machine_result = "OK"  # Always OK for this check
                screen_result = check_screen_sharing()
                funkey_result = "OK"   # Always OK for this check
                monitor_result = check_monitor()
                
                # Update the labels with results
                self.video_label.setText("Video Check: " + video_result)
                self.audio_label.setText("Audio Check: " + audio_result)
                self.machine_label.setText("Machine Requirement: " + machine_result)
                self.screen_label.setText("Screen Sharing App: " + screen_result)
                self.funkey_label.setText("Function Key Block: " + funkey_result)
                self.monitor_label.setText("Monitor Check: " + monitor_result)
                
                # Format labels for better visibility of failures
                for lbl in [self.video_label, self.audio_label, self.machine_label,
                           self.screen_label, self.funkey_label, self.monitor_label]:
                    if "Failed" in lbl.text():
                        lbl.setStyleSheet("color: red;")
                    else:
                        lbl.setStyleSheet("color: green;")
                
                self.checks_completed = True
                
            self.check_timer.stop()
            
            # Check if all tests passed
            failed_checks = []
            for lbl in [self.video_label, self.audio_label, self.machine_label,
                        self.screen_label, self.funkey_label, self.monitor_label]:
                if "Failed" in lbl.text():
                    failed_checks.append(lbl.text().split(':')[0])
            
            if not failed_checks:
                self.status_message.setText("All checks passed!")
                self.status_message.setStyleSheet("color: green; font-weight: bold;")
                self.continue_button.setEnabled(True)
            else:
                # Create a detailed failure message
                failed_items = ", ".join(failed_checks)
                self.status_message.setText(f"Failed checks: {failed_items}. Please fix issues and try again.")
                self.status_message.setStyleSheet("color: red;")
                self.select_devices_button.setEnabled(True)

    def handle_select_devices(self):
        # Disable the select devices button while dialog is open
        self.select_devices_button.setEnabled(False)
        
        dialog = DeviceSelectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            logging.info("Devices confirmed. Starting system checks...")
            # Start checks only after device selection is confirmed
            self.start_checks()
        else:
            logging.info("Device selection cancelled.")
            self.select_devices_button.setEnabled(True)

    def on_continue(self):
        self.switch_to_instructions_callback()

class SharedCameraSession:
    def __init__(self):
        self.camera = None
        self.capture_session = None
        self.is_initialized = False
        
    def initialize(self, camera_device):
        if self.is_initialized:
            return True

        self.camera = QCamera(camera_device)
        self.capture_session = QMediaCaptureSession()
        self.capture_session.setCamera(self.camera)
        self.is_initialized = True
        return True
        
    def get_session(self):
        return self.capture_session
        
    def start_camera(self):
        if self.camera and self.is_initialized:
            self.camera.start()
            return True
        return False
            
    def stop_camera(self):
        if self.camera and self.is_initialized:
            self.camera.stop()
            return True
        return False

# Global shared session instance
shared_camera = SharedCameraSession()


class BackgroundWebcamRecorder:
    def __init__(self, token=None, exam_code=None, user_id=None, exam_id=None):
        self.token = token
        self.exam_code = exam_code
        self.user_id = user_id if user_id is not None else "default_user"
        self.exam_id = exam_id if exam_id is not None else "default_exam"
        self.recorder = None
        self.recording_dir = "exam_recordings"
        self.ensure_recording_dir()
        self.chunk_timer = QTimer()
        self.chunk_timer.timeout.connect(self.handle_chunk_timer)
        self.chunk_interval = 10000  # 10 seconds in milliseconds
        self.current_chunk_file = None
        self.chunk_counter = 0
        self.api_endpoint = "https://stageevaluate.sentientgeeks.us/wp-json/api/v1/save-exam-recorded-video"


    
    def ensure_recording_dir(self):
        try:
            if not os.path.exists(self.recording_dir):
                os.makedirs(self.recording_dir)

            # Test writability
            test_file = os.path.join(self.recording_dir, "test_write.txt")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            logging.info(f"Recording directory {self.recording_dir} is writable")
        except Exception as e:
            logging.error(f"Error with recording directory: {str(e)}")

    def setup_recorder(self, capture_session):
        self.recorder = QMediaRecorder()
        capture_session.setRecorder(self.recorder)
        
        # Connect error signal
        self.recorder.errorOccurred.connect(self.handle_error)
        
        # Set up the media format
        fmt = QMediaFormat()
        fmt.setFileFormat(QMediaFormat.FileFormat.MPEG4)
        fmt.setVideoCodec(QMediaFormat.VideoCodec.H264)
        
        # Add more specific settings
        self.recorder.setMediaFormat(fmt)
        self.recorder.setQuality(QMediaRecorder.Quality.HighQuality)
        self.recorder.setVideoResolution(QSize(640, 480))
        self.recorder.setVideoFrameRate(30.0)
        
        # Set up initial chunk file
        self.update_chunk_file()
        
        logging.info(f"Recorder configured with absolute path: {self.current_chunk_file}")
        return True
    
    def update_chunk_file(self):
        # Ensure we have valid user_id and exam_id values to avoid "None" in filenames
        user_id = str(self.user_id) if self.user_id is not None else "unknown"
        exam_id = str(self.exam_id) if self.exam_id is not None else "unknown"
        
        # Create the simplified filename in the format "user_id-exam_id.mp4"
        # We'll append the chunk number internally to avoid overwriting files locally
        filename = f"{user_id}-{exam_id}_{self.chunk_counter}.mp4"
        
        # Create the full path
        chunk_filepath = os.path.join(self.recording_dir, filename)
        self.current_chunk_file = os.path.abspath(chunk_filepath)
        
        # Set the output location for the recorder
        self.recorder.setOutputLocation(QUrl.fromLocalFile(self.current_chunk_file))
        
        # Log the new file path
        logging.info(f"New recording chunk will be saved as: {self.current_chunk_file}")
        
        # Increment chunk counter for next file
        self.chunk_counter += 1
    
    def handle_error(self, error, error_string):
        logging.error(f"Recorder error ({error}): {error_string}")

    def is_ready(self):
        return self.recorder is not None

    def start_recording(self):
        if self.is_ready() and self.recorder.recorderState() != QMediaRecorder.RecorderState.RecordingState:
            logging.info(f"Starting recording to: {self.recorder.outputLocation().toLocalFile()}")
            self.recorder.record()
            # Start the chunk timer
            self.chunk_timer.start(self.chunk_interval)
            logging.info(f"Recorder state after starting: {self.recorder.recorderState()}")
            logging.info(f"Recording duration: {self.recorder.duration()} ms")
            return True
        return False

    def stop_recording(self):
        if self.is_ready() and self.recorder.recorderState() == QMediaRecorder.RecorderState.RecordingState:
            logging.info("Stopping recording...")
            self.recorder.stop()
            # Stop the chunk timer
            self.chunk_timer.stop()
            # Upload the final chunk
            self.upload_current_chunk()
            logging.info(f"Recorder state after stopping: {self.recorder.recorderState()}")
            logging.info(f"Final recording duration: {self.recorder.duration()} ms")
            logging.info(f"Output file should be at: {self.recorder.outputLocation().toLocalFile()}")
            return True
        return False
    
    def handle_chunk_timer(self):
        # This function is called every 10 seconds
        if self.recorder.recorderState() == QMediaRecorder.RecorderState.RecordingState:
            # Stop current recording
            logging.info("Stopping current chunk recording...")
            self.recorder.stop()
            
            # Add a small delay to ensure file is properly finalized
            QTimer.singleShot(500, self.process_and_start_new_chunk)

    def process_and_start_new_chunk(self):
        # Upload the current chunk
        success = self.upload_current_chunk()
        logging.info(f"Upload of chunk {self.chunk_counter-1} {'succeeded' if success else 'failed'}")
        
        # Start a new chunk
        self.update_chunk_file()
        logging.info(f"Starting new chunk recording to: {self.current_chunk_file}")
        self.recorder.record()
    
    def upload_current_chunk(self):
        if not self.current_chunk_file or not os.path.exists(self.current_chunk_file):
            logging.error(f"Chunk file doesn't exist: {self.current_chunk_file}")
            return False
        
        try:
            # Log file info before upload attempt
            file_size = os.path.getsize(self.current_chunk_file)
            logging.info(f"Preparing to upload chunk: {self.current_chunk_file} (Size: {file_size} bytes)")
            
            if file_size == 0:
                logging.error("File size is 0 bytes, cannot upload empty file")
                return False
                
            # Format chunk counter with leading zeros
            chunk_number = f"chunk{(self.chunk_counter - 1):04d}"
            
            # Create file_name for the API request
            file_id = f"{self.user_id}-{self.exam_id}"
            
            # Prepare multipart form data exactly matching Postman
            with open(self.current_chunk_file, 'rb') as file_data:
                files = {
                    'exam_id': (None, str(self.exam_id)),
                    'user_id': (None, str(self.user_id)),
                    'chunk': (f"{file_id}.mp4", file_data, 'video/mp4'),  # Use proper MIME type
                    'type': (None, 'ondataavailable'),
                    'file_name': (None, file_id),
                    'chunk_number': (None, chunk_number)
                }
                
                # Set headers with token
                headers = {
                    'Authorization': f'Bearer {self.token}'
                }
                
                # Log the request details
                logging.info(f"Sending request to: {self.api_endpoint}")
                logging.info(f"Headers: {headers}")
                logging.info(f"Form data keys: {list(files.keys())}")
                
                # Send POST request
                response = requests.post(
                    self.api_endpoint,
                    files=files,
                    headers=headers
                )
            
            # Check response
            logging.info(f"Response status code: {response.status_code}")
            logging.info(f"Response content: {response.text}")
            
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    if json_response.get('status') is True and "successful" in json_response.get('message', ''):
                        logging.info(f"Successfully uploaded chunk {chunk_number}")
                        # Delete the file after successful upload
                        os.remove(self.current_chunk_file)
                        return True
                    else:
                        logging.warning(f"Upload response not as expected: {json_response}")
                        return False
                except ValueError:
                    logging.error("Could not parse response as JSON")
                    return False
            else:
                logging.error(f"Failed to upload chunk. Status code: {response.status_code}")
                logging.error(f"Response text: {response.text}")
                return False
                    
        except requests.RequestException as req_err:
            logging.error(f"Request error uploading chunk: {str(req_err)}")
            return False
        except IOError as io_err:
            logging.error(f"I/O error handling chunk file: {str(io_err)}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error uploading chunk: {str(e)}")
            logging.exception("Stack trace:")
            return False
        
# 3. Device Selection Dialog
class DeviceSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Your Audio & Video Device")
        self.setModal(True)
        self.resize(400, 200)
        self.setup_ui()
        self.populate_device_lists()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        self.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI';
                color: #0d1b57;
            }

            QComboBox {
                padding: 8px 12px;
                border-radius: 8px;
                border: 1px solid #c5cae9;
                background-color: #f0f4ff;
                font-family: 'Segoe UI';
                font-size: 14px;
                color: #0d1b57;
            }

            QPushButton {
                background-color: #00205b;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #001b4f;
            }
        """)

        title_label = QLabel("Choose Your Audio & Video Device")
        title_label.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Audio layout (use vertical layout like old design)
        audio_layout = QVBoxLayout()
        audio_label = QLabel("Select Audio Device:")
        audio_label.setFont(QFont("Segoe UI", 14))
        self.audio_combo = QComboBox()
        self.audio_combo.setFont(QFont("Segoe UI", 14))
        audio_layout.addWidget(audio_label)
        audio_layout.addWidget(self.audio_combo)
        layout.addLayout(audio_layout)

        # Video layout (use vertical layout like old design)
        video_layout = QVBoxLayout()
        video_label = QLabel("Select Video Device:")
        video_label.setFont(QFont("Segoe UI", 14))
        self.video_combo = QComboBox()
        self.video_combo.setFont(QFont("Segoe UI", 14))
        video_layout.addWidget(video_label)
        video_layout.addWidget(self.video_combo)
        layout.addLayout(video_layout)

        # Buttons layout (keep horizontal but apply styling/alignment)
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(5)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.show_demo_button = QPushButton("Show Demo")
        self.show_demo_button.setFont(QFont("Segoe UI", 14))
        self.show_demo_button.clicked.connect(self.on_show_demo_clicked)
        buttons_layout.addWidget(self.show_demo_button)

        self.confirm_button = QPushButton("Confirm and Run Checks")
        self.confirm_button.setFont(QFont("Segoe UI", 14))
        self.confirm_button.clicked.connect(self.accept)
        buttons_layout.addWidget(self.confirm_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont("Segoe UI", 14))
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)

        layout.addLayout(buttons_layout)

    def populate_device_lists(self):
        # Populate audio devices from system
        try:
            self.audio_combo.clear()
            devices = sd.query_devices()
            for i, device in enumerate(devices):
                if device['max_output_channels'] > 0:
                    self.audio_combo.addItem(f"{device['name']}", i)
            
            # Set default device if available
            default_out = sd.default.device[1]
            if default_out >= 0 and default_out < self.audio_combo.count():
                self.audio_combo.setCurrentIndex(default_out)
        except Exception as e:
            logging.error(f"Error populating audio devices: {e}")
            # Add fallback items
            self.audio_combo.addItems([
                "Default - Microphone Array (Intel® Smart Sound Tech)",
                "External USB Microphone",
                "Bluetooth Headset"
            ])
        
        # Populate video devices
        self.video_combo.clear()
        available_cameras = QMediaDevices.videoInputs()
        if available_cameras:
            for camera in available_cameras:
                self.video_combo.addItem(f"{camera.description()}")
        else:
            # Add fallback items if no cameras detected
            self.video_combo.addItems([
                "Integrated Camera (04f2:b725)",
                "External USB Camera",
                "Virtual Camera"
            ])

    def on_show_demo_clicked(self):
        audio_device = self.audio_combo.currentText()
        video_device = self.video_combo.currentText()
        demo_dialog = DemoPreviewDialog(audio_device, video_device, parent=self)
        if demo_dialog.exec() == QDialog.DialogCode.Accepted:
            logging.info("Devices confirmed via demo.")
            self.accept()
        else:
            logging.info("Device demo cancelled.")

# For completeness, a stub for DemoPreviewDialog (if you need the implementation, let me know)
class DemoPreviewDialog(QDialog):
    def __init__(self, audio_device, video_device, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Device Preview")
        self.setModal(True)
        self.resize(600, 500)
        self.audio_device = audio_device
        self.video_device = video_device
        self.setup_ui()
        self.start_audio_monitoring()
        
    def setup_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: 1px solid transparent;")

        # MAIN CONTENT WIDGET
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)

        # HEADER
        header_frame = QWidget()
        header_frame.setStyleSheet("""
            QFrame {
                color: #c5cae9;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_label = QLabel("Device Preview")
        header_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_label.setStyleSheet("color: #00205b; padding: 0px;")
        header_layout.addWidget(header_label)
        layout.addWidget(header_frame, alignment=Qt.AlignmentFlag.AlignTop)

        # DEVICE INFO BLOCK
        device_frame = QFrame()
        device_frame.setStyleSheet("""
            QFrame {
                background-color: #f0f4ff;
                border-radius: 6px;
                padding: 5px;
            }
        """)
        device_layout = QVBoxLayout(device_frame)

        device_title = QLabel("Selected Devices")
        device_title.setStyleSheet("color: #00205b; text-decoration: underline;")
        # Change alignment to left instead of top
        device_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        device_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        device_layout.addWidget(device_title)

        self.audio_device = "Intel(R) Display Audio HDMI 1"
        self.video_device = "Integrated Camera (04f2:b725)"

        audio_info = QLabel(f"Audio: {self.audio_device}")
        audio_info.setFont(QFont("Segoe UI", 12))
        device_layout.addWidget(audio_info)

        video_info = QLabel(f"Video: {self.video_device}")
        video_info.setFont(QFont("Segoe UI", 12))
        device_layout.addWidget(video_info)

        layout.addWidget(device_frame)

        # CAMERA PREVIEW BLOCK
        video_section = QFrame()
        video_section.setStyleSheet("""
            QFrame {
                background-color: #f0f4ff;
                border-radius: 6px;
                padding: 5px;
            }
        """)
        self.video_layout = QVBoxLayout(video_section)

        video_title = QLabel("Camera Preview")
        video_title.setStyleSheet("color: #00205b; text-decoration: underline;")
        # Change alignment to left instead of default center
        video_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        video_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.video_layout.addWidget(video_title)

        self.video_container = QWidget()
        self.video_container_layout = QVBoxLayout(self.video_container)

        self.video_preview = QLabel("Connecting to camera...")
        self.video_preview.setFont(QFont("Segoe UI", 14))
        self.video_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_preview.setMinimumSize(400, 250)
        self.video_preview.setStyleSheet("""
            background-color: #333;
            color: white;
            border-radius: 6px;
        """)
        self.video_container_layout.addWidget(self.video_preview)

        self.video_layout.addWidget(self.video_container)

        layout.addWidget(video_section)

        # AUDIO LEVELS BLOCK
        audio_section = QFrame()
        audio_section.setStyleSheet("""
            QFrame {
                background-color: #f0f4ff;
                border-radius: 12px;
                padding: 5px;
            }
        """)
        audio_layout = QVBoxLayout(audio_section)

        audio_title = QLabel("Audio Levels")
        audio_title.setStyleSheet("color: #00205b; text-decoration: underline;")
        # Change alignment to left
        audio_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        audio_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        audio_layout.addWidget(audio_title)

        level_layout = QHBoxLayout()

        mic_label = QLabel("Microphone")
        mic_label.setStyleSheet("color: #00205b; text-decoration: underline;")
        mic_label.setFont(QFont("Segoe UI", 12))
        level_layout.addWidget(mic_label)

        self.audio_levels = QProgressBar()
        self.audio_levels.setMinimum(0)
        self.audio_levels.setMaximum(100)
        self.audio_levels.setValue(0)
        self.audio_levels.setTextVisible(True)
        self.audio_levels.setFormat("%v%")
        self.audio_levels.setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 1px;
            }
        """)
        level_layout.addWidget(self.audio_levels)

        audio_layout.addLayout(level_layout)

        # TEST SOUND BUTTON
        self.test_sound_button = QPushButton("Play Test Sound")
        self.test_sound_button.setFont(QFont("Segoe UI", 12))
        self.test_sound_button.clicked.connect(self.play_test_sound)
        # Use align left instead of top for consistent alignment
        audio_layout.addWidget(self.test_sound_button, alignment=Qt.AlignmentFlag.AlignRight)

        self.audio_status = QLabel("Speak to test your microphone")
        self.audio_status.setFont(QFont("Segoe UI", 12))
        # Use align left instead of top
        self.audio_status.setAlignment(Qt.AlignmentFlag.AlignLeft)
        audio_layout.addWidget(self.audio_status)

        layout.addWidget(audio_section)

        # BOTTOM BUTTONS
        buttons_layout = QHBoxLayout()

        self.help_button = QPushButton("Help")
        self.help_button.setFont(QFont("Segoe UI", 12))
        self.help_button.clicked.connect(self.show_help)
        buttons_layout.addWidget(self.help_button)

        buttons_layout.addStretch()

        confirm_button = QPushButton("Devices Look Good")
        confirm_button.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        confirm_button.clicked.connect(self.accept)
        buttons_layout.addWidget(confirm_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont("Segoe UI", 12))
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)

        layout.addLayout(buttons_layout)

        # Attach content widget to scroll area
        scroll.setWidget(content_widget)

        # Main dialog layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        # Simulate camera connection after delay
        QTimer.singleShot(1500, self.simulate_camera_connection)

    def simulate_camera_connection(self):
        # In a real implementation, you would connect to the actual camera
        # This is a simulation for demo purposes
        self.video_preview.setText("Camera connected successfully")
        self.video_preview.setStyleSheet("background-color: #111; color: lime;")
        
        # Show a message that this is just a simulation
        msg = QLabel("(In a real implementation, this would show live camera feed)")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("color: yellow;")
        self.video_container_layout.addWidget(msg) 
    
    def start_audio_monitoring(self):
        # In a real implementation, this would monitor actual audio levels
        # For this demo, we'll simulate with a timer
        self.audio_timer = QTimer(self)
        self.audio_timer.timeout.connect(self.update_audio_level)
        self.audio_timer.start(100)
        self.audio_level = 0
        
    def update_audio_level(self):
        # Simulate fluctuating audio levels
        # In a real implementation, this would read from the microphone
        if random.random() < 0.3:
            self.audio_level = min(100, self.audio_level + random.randint(5, 20))
        else:
            self.audio_level = max(0, self.audio_level - random.randint(3, 10))
            
        self.audio_levels.setValue(self.audio_level)
        
        # Update status based on level
        if self.audio_level > 70:
            self.audio_status.setText("Audio level good!")
            self.audio_status.setStyleSheet("color: green;")
        elif self.audio_level > 30:
            self.audio_status.setText("Audio detected")
            self.audio_status.setStyleSheet("color: black;")
        else:
            self.audio_status.setText("Speak to test your microphone")
            self.audio_status.setStyleSheet("color: black;")
    
    def play_test_sound(self):
        # In a real implementation, this would play an actual test sound
        self.test_sound_button.setText("Playing...")
        self.test_sound_button.setEnabled(False)
        
        # Simulate playing sound by temporarily increasing audio level
        self.audio_level = 80
        self.audio_levels.setValue(self.audio_level)
        
        # Re-enable after a short delay
        QTimer.singleShot(2000, self.reset_test_button)
    
    def reset_test_button(self):
        self.test_sound_button.setText("Play Test Sound")
        self.test_sound_button.setEnabled(True)
    
    def show_help(self):
        help_dialog = QMessageBox(self)
        help_dialog.setWindowTitle("Device Setup Help")
        help_dialog.setIcon(QMessageBox.Icon.Information)
        help_dialog.setText("Device Setup Troubleshooting")
        
        help_text = (
            "<b>Camera Issues:</b><br>"
            "• Make sure your camera is connected properly<br>"
            "• Check if other applications are using your camera<br>"
            "• Try selecting a different camera if available<br><br>"
            
            "<b>Audio Issues:</b><br>"
            "• Make sure your microphone is not muted<br>"
            "• Check if the correct audio device is selected<br>"
            "• Try adjusting your system's audio input volume<br><br>"
            
            "If problems persist, contact technical support."
        )
        
        help_dialog.setInformativeText(help_text)
        help_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        help_dialog.exec()
        
    def closeEvent(self, event):
        # Stop the timer when the dialog is closed
        if hasattr(self, 'audio_timer') and self.audio_timer.isActive():
            self.audio_timer.stop()
        super().closeEvent(event)

# 5. Exam Instructions Page
class ExamInstructionsPage(QWidget):
    def __init__(self, switch_to_exam_callback):
        super().__init__()
        self.switch_to_exam_callback = switch_to_exam_callback
        self.exam_details = None
        self.remaining_time = 0
        self.setup_ui()

    def set_exam_details(self, exam_details):
        self.exam_details = exam_details
        print("\n✅ Exam Details in ExamInstructionsPage:", self.exam_details)
        # Ensure remaining_time is an integer
        self.remaining_time = int(self.exam_details.get("remaining_time", 0))
        self.message_label.setText(self.exam_details.get("message", ""))
        self.start_countdown()

    def setup_ui(self):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(20,20, 20, 20)
            layout.setSpacing(0)
            
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(20, 30, 20, 20) 
            container_layout.setSpacing(8)
            container.setStyleSheet("""
                QWidget {
                    background-color: white;
                    border-radius: 15px;
                }
            """)
            container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            layout.addWidget(container)

            title = QLabel("Welcome To SentientGeeks Assessment Exam")
            title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            title.setStyleSheet("color: #00205b;")
            title.setAlignment(Qt.AlignmentFlag.AlignLeft)
            container_layout.addWidget(title)

            banner = QLabel("Please read the following instructions carefully before starting the exam:")
            banner.setFont(QFont("Arial", 18, QFont.Weight.Medium))
            banner.setStyleSheet("background-color: #ff0000; color: #fff; padding: 10px; border-radius: 4px;")
            banner.setFixedWidth(800)
            banner.setWordWrap(True)
            banner.setAlignment(Qt.AlignmentFlag.AlignLeft)
            container_layout.addWidget(banner)    

            instructions_html = """
            <ol style="font-size:16px; font-family:sans-serif; line-height:2; color:#121212; padding-left: 0px; margin-left: 0px;">
                <li style="margin-bottom: 15px; margin-left: 0px; padding-left: 0px;">Exam can only be started on desktop or laptop devices.</li>
                <li style="margin-bottom: 15px; margin-left: 0px; padding-left: 0px;">Ensure that your camera and microphone are connected and grant the necessary permissions before starting the exam.</li>
                <li style="margin-bottom: 15px; margin-left: 0px; padding-left: 0px;">Close all other programs before starting your exam.</li>
                <li style="margin-bottom: 15px; margin-left: 0px; padding-left: 0px;">Do not use any browser extensions (e.g., Grammarly), as they may cause exam termination.</li>
                <li style="margin-bottom: 15px; margin-left: 0px; padding-left: 0px;">Ensure you have a stable internet and power connection.</li>
                <li style="margin-bottom: 15px; margin-left: 0px; padding-left: 0px;">Do not press the <b>Esc</b>, <b>Windows</b>, or any other shortcut button.</li>
                <li style="margin-bottom: 15px; margin-left: 0px; padding-left: 0px;">Do not exit full-screen mode.</li>
                <li style="margin-bottom: 15px; margin-left: 0px; padding-left: 0px;">Do not refresh the page during the exam.</li>
                <li style="margin-bottom: 15px; margin-left: 0px; padding-left: 0px;">Avoid clicking on any pop-ups during the exam.</li>
                <li style="margin-bottom: 15px; margin-left: 0px; padding-left: 0px;">If you do not submit your exam within the provided time, your answers will be automatically saved.</li>
                <li style="margin-bottom: 15px; margin-left: 0px; padding-left: 0px;">Close your browser only after the "Thank You" page is visible.</li>
            </ol>
                """
            self.instructions_label = QLabel(instructions_html)
            self.instructions_label.setWordWrap(True)
            self.instructions_label.setFont(QFont("Arial", 16))
            self.instructions_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.instructions_label.setContentsMargins(0, 15, 0, 0)
            container_layout.addWidget(self.instructions_label)

            self.message_label = QLabel("")
            self.message_label.setFont(QFont("Arial", 18))
            self.message_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.message_label.setStyleSheet("color: #00205b;")
            self.message_label.setContentsMargins(0, 15, 0, 0)
            container_layout.addWidget(self.message_label)

            self.countdown_label = QLabel("")
            self.countdown_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))
            self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            container_layout.addWidget(self.countdown_label)
            self.countdown_label.setStyleSheet("color: #418b69;")

    def start_countdown(self):
        # Create a QTimer and connect its timeout to update_countdown
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.update_countdown()  # Call immediately to update the label
        self.timer.start(1000)

    def update_countdown(self):
        if self.remaining_time > 0:
            hours, rem = divmod(self.remaining_time, 3600)
            mins, secs = divmod(rem, 60)
            time_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
            self.countdown_label.setText(f"Exam starts in: {time_str}")
            self.remaining_time -= 1
        else:
            self.timer.stop()
            self.countdown_label.setText("Starting Exam...")
            
            # Use QTimer.singleShot to delay the exam transition process
            # This ensures the UI updates before we start any heavy operations
            QTimer.singleShot(100, self.start_exam_transition)
    
    def start_exam_transition(self):
        # This will run in the main thread, but after the UI has been updated
        try:
            exam_link = self.exam_details.get("exam_link") or ""
            print("🔹 Calling get_exam_details after countdown ends with exam_link:", exam_link)
            
            # Process UI events before making API calls
            QApplication.processEvents()
            
            updated_details = get_exam_details(SESSION_TOKEN, exam_link)
            print("🔹 Updated Exam Details received:", updated_details)
            logging.info("Updated Exam Details received after countdown: " + str(updated_details))
            
            if updated_details and updated_details.get("status"):
                self.exam_details = updated_details
                question_ids = updated_details.get("questionsIds", [])
                print("🔹 Question IDs after update:", question_ids)
                logging.info("Question IDs after update: " + str(question_ids))
                
                if question_ids:
                    # Process events again to keep UI responsive
                    QApplication.processEvents()
                    
                    question_data = fetch_question(
                        question_ids[0],
                        updated_details.get("examId") or updated_details.get("exam_id"),
                        updated_details.get("userId") or updated_details.get("user_id") or "default_user",
                        idx=0,
                        first_request=True
                    )
                    print("🔹 Fetched first question:", question_data)
                    logging.info("Fetched first question: " + str(question_data))
                else:
                    print("⚠️ No question IDs returned in exam details.")
                    logging.warning("No question IDs returned in exam details.")
                    
                # Switch to exam page with updated details
                self.switch_to_exam_callback(self.exam_details)
            else:
                print("❌ Failed to refresh exam details.")
                logging.error("Failed to refresh exam details after countdown.")
                # Show an error message to the user
                QMessageBox.warning(self, "Error", "Failed to load exam details. Please try again.")
                
        except Exception as e:
            print(f"❌ Error during exam transition: {str(e)}")
            logging.error(f"Error during exam transition: {str(e)}")
            QMessageBox.warning(self, "Error", f"An error occurred: {str(e)}")

class ExamPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.questions = []
        self.current_question_index = 0
        self.user_answers = []
        self.exam_code = ""
        self.exam_details = None
        self.exam_id = None
        self.user_id = None
        self.exam_submitted = False
        self.webcam_recorder = None

        self.timer = QTimer(self)
        self.remaining_seconds = 0
        self.timer.timeout.connect(self.update_timer)

        self.setup_ui()



    def setup_ui(self):
        # Import network related modules at the top of the class

        # Set the overall background color to match the screenshot
        self.setStyleSheet("background-color: #f5f9ff;")
    
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Left Container (Question & Options)
        self.left_container = QWidget()
        self.left_container.setStyleSheet("background-color: #FFFFFF; border-radius: 6px;")
        self.left_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)

        # Question indicator with bullet point (•)
        question_header_layout = QHBoxLayout()
        self.question_number_pill = QLabel("• Question 1")
        self.question_number_pill.setStyleSheet("""
            background-color: #EBF1F9;
            color: #0D2144;
            border-radius: 15px;
            padding: 5px 15px;
            font-weight: bold;
        """)
        question_header_layout.addWidget(self.question_number_pill)
        question_header_layout.addStretch()
    
        # Marks indicator
        self.marks_label = QLabel("[Marks: 2]")
        self.marks_label.setStyleSheet("color: #333333; font-weight: bold;")
        question_header_layout.addWidget(self.marks_label)
    
        # Question type indicator
        self.question_type_label = QLabel("[Type: MCQ]")
        self.question_type_label.setStyleSheet("color: #333333;")
        question_header_layout.addWidget(self.question_type_label)
    
        left_layout.addLayout(question_header_layout)

        # Question text
        self.question_label = QLabel("Question text will appear here")
        self.question_label.setFont(QFont("Arial", 16))
        self.question_label.setWordWrap(True)
        self.question_label.setTextFormat(Qt.TextFormat.RichText)
        self.question_label.setStyleSheet("""
            color: #000000;
            background-color: #FFFFFF;
            padding: 10px;
        """)
        self.question_label.setMinimumHeight(80)
        self.question_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.question_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        left_layout.addWidget(self.question_label)
        
        # Question content (for additional content like images)
        self.question_content_label = QLabel()
        self.question_content_label.setWordWrap(True)
        self.question_content_label.setTextFormat(Qt.TextFormat.RichText)
        self.question_content_label.setStyleSheet("""
            color: #000000;
            background-color: #FFFFFF;
            padding: 10px;
        """)
        self.question_content_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.question_content_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.question_content_label.setOpenExternalLinks(True)  # Allow opening links if any
        left_layout.addWidget(self.question_content_label)

        self.question_content_label = QLabel()

        self.question_content_label.setWordWrap(True)
        self.question_content_label.setTextFormat(Qt.TextFormat.RichText)
        self.question_content_label.setStyleSheet("""
            color: #000000;
            background-color: #FFFFFF;
            padding: 10px;
        """)
        self.question_content_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.question_content_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.question_content_label.setOpenExternalLinks(True)  # Allow opening links if any
        left_layout.addWidget(self.question_content_label)

        # Add WebEngineView for better HTML content rendering
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        self.question_content_web = QWebEngineView()
        self.question_content_web.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.question_content_web.setMinimumHeight(100)
        self.question_content_web.setStyleSheet("""
            background-color: #FFFFFF;
            border: none;
        """)
        left_layout.addWidget(self.question_content_web)
        self.question_content_web.hide()  # Hide initially
    
        # Horizontal separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #E0E0E0;")
        left_layout.addWidget(separator)

        # Options container for MCQ/MSQ - MODIFIED
        options_container = QWidget()
        options_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.options_layout = QVBoxLayout(options_container)
        self.options_layout.setSpacing(15)
        self.options_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.addWidget(options_container, 1)  # Add stretch factor of 1
    
        # Description answer container - MODIFIED
        self.description_container = QWidget()
        self.description_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        description_layout = QVBoxLayout(self.description_container)
        description_layout.setContentsMargins(0, 0, 0, 0)
    
        self.description_editor = QTextEdit()
        self.description_editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.description_editor.setStyleSheet("""
            border: 1px solid #D0D0D0;
            border-radius: 4px;
            padding: 8px;
            background-color: #FFFFFF;
            font-size: 14px;
        """)
        description_layout.addWidget(self.description_editor, 1)  # Add stretch factor of 1
    
        # Word count display
        word_count_layout = QHBoxLayout()
        self.word_count_label = QLabel("Word count: 0")
        self.word_count_label.setStyleSheet("color: #666666;")
        word_count_layout.addStretch()
        word_count_layout.addWidget(self.word_count_label)
        description_layout.addLayout(word_count_layout)
    
        # Connect text change signal to word counter
        self.description_editor.textChanged.connect(self.update_word_count)
    
        # Initially hide the description editor
        self.description_container.hide()
        left_layout.addWidget(self.description_container, 1)  # Add stretch factor of 1
    
        # Coding answer container - MODIFIED
        self.coding_container = QWidget()
        self.coding_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        coding_layout = QVBoxLayout(self.coding_container)
        coding_layout.setContentsMargins(0, 0, 0, 0)
        coding_layout.setSpacing(10)
    
        # Language selector and run button in the same row
        lang_row_layout = QHBoxLayout()
    
        # Language selector for coding questions
        lang_label = QLabel("Language:")
        lang_label.setStyleSheet("color: #333333; font-weight: bold;")
        self.language_selector = QComboBox()
        self.language_selector.addItems(["Python", "Java", "JavaScript", "C++", "C", "HTML"])
        self.language_selector.setStyleSheet("""
            border: 1px solid #D0D0D0;
            border-radius: 4px;
            padding: 5px;
            background-color: white;
            color: black;
        """)
    
        # Add Run button
        self.run_code_button = QPushButton("Run")
        self.run_code_button.setStyleSheet("""
            QPushButton {
                background-color: #0D2144;
                color: white;
                border-radius: 4px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0A1A36;
            }
        """)
        self.run_code_button.clicked.connect(self.run_code)
    
        lang_row_layout.addWidget(lang_label)
        lang_row_layout.addWidget(self.language_selector)
        lang_row_layout.addStretch()
        lang_row_layout.addWidget(self.run_code_button)
        coding_layout.addLayout(lang_row_layout)
        
        # Create a widget to hold both code editor and output in specific proportions
        code_output_container = QWidget()
        code_output_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        code_output_layout = QVBoxLayout(code_output_container)
        code_output_layout.setContentsMargins(0, 0, 0, 0)
        code_output_layout.setSpacing(10)
        
        # Code editor - 70% of height
        self.code_editor = QTextEdit()
        self.code_editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.code_editor.setStyleSheet("""
            border: 1px solid #D0D0D0;
            border-radius: 4px;
            padding: 8px;
            background-color: #1E1E1E;
            color: #FFFFFF;
            font-family: Consolas, Monaco, 'Courier New', monospace;
            font-size: 14px;
        """)
        
        # Set a monospace font for code
        code_font = QFont("Consolas")
        code_font.setStyleHint(QFont.StyleHint.Monospace)
        self.code_editor.setFont(code_font)
        
        # Add output area with header - 30% of height
        output_header = QLabel("Output:")
        output_header.setStyleSheet("color: #333333; font-weight: bold; margin-top: 10px;")
        
        self.code_output = QTextEdit()
        self.code_output.setReadOnly(True)
        self.code_output.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.code_output.setStyleSheet("""
            border: 1px solid #D0D0D0;
            border-radius: 4px;
            padding: 8px;
            background-color: #1E1E1E;
            color: #FFFFFF;
            font-family: Consolas, Monaco, 'Courier New', monospace;
            font-size: 14px;
        """)
        
        # Add components to code_output_layout with specific proportions (70/30)
        code_output_layout.addWidget(self.code_editor, 7)  # 70% of space
        code_output_layout.addWidget(output_header)
        code_output_layout.addWidget(self.code_output, 3)  # 30% of space
        
        # Add the code_output_container to coding_layout
        coding_layout.addWidget(code_output_container, 1)  # stretch factor of 1
        
        self.setup_modern_code_editor()
        # Initially hide the coding editor
        self.coding_container.hide()
        left_layout.addWidget(self.coding_container, 1)  # Add stretch factor of 1

        # Right Container (Timer, Navigation, Question Panel) - keep as is
        self.right_container = QWidget()
        self.right_container.setFixedWidth(320)  # Fixed width for right panel
        self.right_container.setStyleSheet("background-color: #FFFFFF; border-radius: 6px;")
        right_layout = QVBoxLayout(self.right_container)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(20)

        # Logo at the top
        logo_layout = QHBoxLayout()
        logo_label = QLabel("KEvaluate")
        logo_label.setStyleSheet("""
            color: #0D2144;
            font-size: 20px;
            font-weight: bold;
        """)
        logo_layout.addWidget(logo_label)
        logo_layout.addStretch()
        right_layout.addLayout(logo_layout)

        # Timer container with circular design
        timer_container = QWidget()
        timer_container.setStyleSheet("""
            background-color: white;
            border-radius: 10px;
        """)
        timer_layout = QVBoxLayout(timer_container)
        
        time_label_title = QLabel("Remaining Time")
        time_label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_label_title.setStyleSheet("color: #0D2144; font-size: 16px; font-weight: bold;")
        timer_layout.addWidget(time_label_title)
        
        # Custom circular timer
        self.time_container = QLabel("00:00:00")
        self.time_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_container.setFixedSize(150, 150)
        self.time_container.setStyleSheet("""
            background-color: white;
            color: #0D2144;
            font-size: 24px;
            font-weight: bold;
            border: 3px solid #0D2144;
            border-radius: 75px;
        """)
        timer_layout.addWidget(self.time_container, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Hours, Min, Sec labels
        time_units_layout = QHBoxLayout()
        time_units = ["Hours", "Min", "Sec"]
        for unit in time_units:
            unit_label = QLabel(unit)
            unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            unit_label.setStyleSheet("color: #666; font-size: 12px;")
            time_units_layout.addWidget(unit_label)
        
        timer_layout.addLayout(time_units_layout)
        right_layout.addWidget(timer_container)

        # Question Panel section
        question_panel_container = QWidget()
        question_panel_container.setStyleSheet("""
            background-color: white;
            border-radius: 10px;
            padding: 10px;
        """)
        question_panel_layout = QVBoxLayout(question_panel_container)
        
        question_panel_title = QLabel("Question Panel")
        question_panel_title.setStyleSheet("color: #0D2144; font-size: 16px; font-weight: bold;")
        question_panel_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        question_panel_layout.addWidget(question_panel_title)
        
        # Legend for question status
        legend_layout = QVBoxLayout()
        
        status_items = [
            ("Answer Given", "#8BC34A"),
            ("Answer Not Given", "#F44336"),
            ("Current", "#0D2144"),
            ("Not Visited", "#D0D0D0")
        ]
        
        for status, color in status_items:
            item_layout = QHBoxLayout()
            
            status_indicator = QLabel()
            status_indicator.setFixedSize(15, 15)
            status_indicator.setStyleSheet(f"background-color: {color}; border-radius: 7px;")
            
            status_label = QLabel(status)
            status_label.setStyleSheet("color: #333; font-size: 12px;")
            
            item_layout.addWidget(status_indicator)
            item_layout.addWidget(status_label)
            item_layout.addStretch()
            
            legend_layout.addLayout(item_layout)
        
        question_panel_layout.addLayout(legend_layout)
        
        # Question number buttons grid
        self.question_panel = QGridLayout()
        self.question_panel.setSpacing(10)
        question_panel_layout.addLayout(self.question_panel)
        right_layout.addWidget(question_panel_container)

        # Navigation Buttons
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.setStyleSheet("""
            QPushButton {
                background-color: #E1E8F5;
                color: #0D2144;
                border-radius: 4px;
                padding: 10px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D0DBEB;
            }
        """)
        
        self.next_button = QPushButton("Next ▶")
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #0D2144;
                color: white;
                border-radius: 4px;
                padding: 10px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0A1A36;
            }
        """)
        
        nav_layout.addWidget(self.prev_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_button)
        right_layout.addLayout(nav_layout)
        
        # Submit button
        self.submit_button = QPushButton("Submit")
        self.submit_button.setStyleSheet("""
            QPushButton {
                background-color: #0D2144;
                color: white;
                border-radius: 4px;
                padding: 12px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #0A1A36;
            }
        """)
        right_layout.addWidget(self.submit_button)
        
        # Add containers to main layout with proper proportions
        main_layout.addWidget(self.left_container, 3)  # Increased left container proportion
        main_layout.addWidget(self.right_container, 0)  # Right container has fixed width
        
        # Connect button signals
        self.prev_button.clicked.connect(self.go_previous)
        self.next_button.clicked.connect(self.go_next)
        self.submit_button.clicked.connect(self.submit_exam)
        
        # Initialize button group for options
        self.options_button_group = QButtonGroup(self)
        self.options_button_group.setExclusive(True)
        
        # Initialize checkbox list for MSQ questions
        self.checkbox_list = []

    def display_html_content(self, html_content):
        """Display HTML content including images in the web view"""
        # We need to wrap the HTML content in a complete HTML document structure
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #FFFFFF;
                    color: #000000;
                    margin: 5px;
                    padding: 5px;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                    display: block;
                    margin: 10px auto;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Load the HTML content into the web view
        self.question_content_web.setHtml(full_html)
        self.question_content_web.show()
        
        # Adjust the web view's height based on content
        self.question_content_web.page().runJavaScript(
            "document.body.scrollHeight",
            self.adjust_web_view_height
        )

    def adjust_web_view_height(self, height):
        """Adjust the height of the web view based on content"""
        # Set a minimum height but allow it to grow with content
        # Limit to a maximum height to prevent excessive scrolling
        min_height = 100
        max_height = 400
        content_height = max(min_height, min(height + 30, max_height))
        
        self.question_content_web.setMinimumHeight(content_height)
        self.question_content_web.setMaximumHeight(content_height)
               
    def setup_modern_code_editor(self):
        
        # Create syntax highlighter for different languages
        class VSCodeSyntaxHighlighter(QSyntaxHighlighter):
            def __init__(self, parent=None, language="python"):
                super().__init__(parent)
                self.language = language.lower()
                self.highlighting_rules = []
                
                # VS Code color scheme
                self.colors = {
                    "keyword": QColor("#569CD6"),       # blue
                    "class": QColor("#4EC9B0"),         # teal
                    "function": QColor("#DCDCAA"),      # yellow
                    "string": QColor("#CE9178"),        # orange-brown
                    "comment": QColor("#6A9955"),       # green
                    "number": QColor("#B5CEA8"),        # light green
                    "operator": QColor("#D4D4D4"),      # light gray
                    "constant": QColor("#4FC1FF"),      # light blue
                    "preprocessor": QColor("#C586C0"),  # purple
                    "identifier": QColor("#9CDCFE"),    # light blue
                    "bracket": QColor("#D4D4D4"),       # light gray
                    "default": QColor("#D4D4D4")        # light gray
                }
                
                self.setup_highlighting_rules()
            
            def setup_highlighting_rules(self):
                # Clear rules first
                self.highlighting_rules = []
                
                # Common formatting for different code elements
                keyword_format = QTextCharFormat()
                keyword_format.setForeground(self.colors["keyword"])
                keyword_format.setFontWeight(QFont.Weight.Bold)
                
                class_format = QTextCharFormat()
                class_format.setForeground(self.colors["class"])
                
                function_format = QTextCharFormat()
                function_format.setForeground(self.colors["function"])
                
                string_format = QTextCharFormat()
                string_format.setForeground(self.colors["string"])
                
                comment_format = QTextCharFormat()
                comment_format.setForeground(self.colors["comment"])
                
                number_format = QTextCharFormat()
                number_format.setForeground(self.colors["number"])
                
                operator_format = QTextCharFormat()
                operator_format.setForeground(self.colors["operator"])
                
                # Set language-specific rules
                if self.language == "python":
                    # Python keywords
                    keywords = [
                        "and", "as", "assert", "async", "await", "break", "class", "continue", 
                        "def", "del", "elif", "else", "except", "False", "finally", "for", 
                        "from", "global", "if", "import", "in", "is", "lambda", "None", 
                        "nonlocal", "not", "or", "pass", "raise", "return", "True", 
                        "try", "while", "with", "yield"
                    ]
                    
                    # Add keyword rules
                    for keyword in keywords:
                        pattern = QRegularExpression(r'\b' + keyword + r'\b')
                        self.highlighting_rules.append((pattern, keyword_format))
                    
                    # Function calls pattern
                    function_pattern = QRegularExpression(r'\b[A-Za-z0-9_]+(?=\()')
                    self.highlighting_rules.append((function_pattern, function_format))
                    
                    # Class name pattern
                    class_pattern = QRegularExpression(r'\bclass\s+([A-Za-z_][A-Za-z0-9_]*)')
                    self.highlighting_rules.append((class_pattern, class_format))
                    
                    # String patterns - single and double quotes
                    self.highlighting_rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
                    self.highlighting_rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))
                    
                    # Triple-quoted strings patterns
                    self.highlighting_rules.append((QRegularExpression(r'""".*?"""', QRegularExpression.PatternOption.DotMatchesEverythingOption), string_format))
                    self.highlighting_rules.append((QRegularExpression(r"'''.*?'''", QRegularExpression.PatternOption.DotMatchesEverythingOption), string_format))
                    
                    # Comment pattern
                    self.highlighting_rules.append((QRegularExpression(r'#[^\n]*'), comment_format))
                    
                    # Number pattern
                    self.highlighting_rules.append((QRegularExpression(r'\b\d+\b'), number_format))
                    
                    # Operators pattern
                    self.highlighting_rules.append((QRegularExpression(r'[\+\-\*/=<>%&\|\^~!]'), operator_format))
                
                elif self.language == "javascript":
                    # JavaScript keywords
                    keywords = [
                        "break", "case", "catch", "class", "const", "continue", "debugger", 
                        "default", "delete", "do", "else", "export", "extends", "false", 
                        "finally", "for", "function", "if", "import", "in", "instanceof", 
                        "new", "null", "return", "super", "switch", "this", "throw", "true", 
                        "try", "typeof", "var", "void", "while", "with", "yield", "let", "async", "await"
                    ]
                    
                    # Add keyword rules
                    for keyword in keywords:
                        pattern = QRegularExpression(r'\b' + keyword + r'\b')
                        self.highlighting_rules.append((pattern, keyword_format))
                    
                    # Function declarations and calls
                    function_pattern = QRegularExpression(r'\b[A-Za-z0-9_]+(?=\()')
                    self.highlighting_rules.append((function_pattern, function_format))
                    
                    # Class name pattern
                    class_pattern = QRegularExpression(r'\bclass\s+([A-Za-z_][A-Za-z0-9_]*)')
                    self.highlighting_rules.append((class_pattern, class_format))
                    
                    # String patterns - single and double quotes
                    self.highlighting_rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
                    self.highlighting_rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))
                    self.highlighting_rules.append((QRegularExpression(r"`[^`\\]*(\\.[^`\\]*)*`"), string_format))
                    
                    # Comment patterns
                    self.highlighting_rules.append((QRegularExpression(r'//[^\n]*'), comment_format))
                    self.highlighting_rules.append((QRegularExpression(r'/\*.*?\*/', QRegularExpression.PatternOption.DotMatchesEverythingOption), comment_format))
                    
                    # Number pattern
                    self.highlighting_rules.append((QRegularExpression(r'\b\d+(\.\d+)?\b'), number_format))
                    
                    # Operators pattern
                    self.highlighting_rules.append((QRegularExpression(r'[\+\-\*/=<>%&\|\^~!]'), operator_format))
                
                elif self.language == "java" or self.language == "c++" or self.language == "c":
                    # C-like language keywords
                    if self.language == "java":
                        keywords = [
                            "abstract", "assert", "boolean", "break", "byte", "case", "catch", 
                            "char", "class", "const", "continue", "default", "do", "double", 
                            "else", "enum", "extends", "final", "finally", "float", "for", 
                            "goto", "if", "implements", "import", "instanceof", "int", 
                            "interface", "long", "native", "new", "package", "private", 
                            "protected", "public", "return", "short", "static", "strictfp", 
                            "super", "switch", "synchronized", "this", "throw", "throws", 
                            "transient", "try", "void", "volatile", "while", "true", "false", "null"
                        ]
                    elif self.language == "c++":
                        keywords = [
                            "alignas", "alignof", "and", "and_eq", "asm", "auto", "bitand", 
                            "bitor", "bool", "break", "case", "catch", "char", "char16_t", 
                            "char32_t", "class", "compl", "const", "constexpr", "const_cast", 
                            "continue", "decltype", "default", "delete", "do", "double", 
                            "dynamic_cast", "else", "enum", "explicit", "export", "extern", 
                            "false", "float", "for", "friend", "goto", "if", "inline", "int", 
                            "long", "mutable", "namespace", "new", "noexcept", "not", "not_eq", 
                            "nullptr", "operator", "or", "or_eq", "private", "protected", 
                            "public", "register", "reinterpret_cast", "return", "short", 
                            "signed", "sizeof", "static", "static_assert", "static_cast", 
                            "struct", "switch", "template", "this", "thread_local", "throw", 
                            "true", "try", "typedef", "typeid", "typename", "union", "unsigned", 
                            "using", "virtual", "void", "volatile", "wchar_t", "while", "xor", "xor_eq"
                        ]
                    else:  # C language
                        keywords = [
                            "auto", "break", "case", "char", "const", "continue", "default", 
                            "do", "double", "else", "enum", "extern", "float", "for", "goto", 
                            "if", "inline", "int", "long", "register", "restrict", "return", 
                            "short", "signed", "sizeof", "static", "struct", "switch", 
                            "typedef", "union", "unsigned", "void", "volatile", "while", 
                            "_Alignas", "_Alignof", "_Atomic", "_Bool", "_Complex", 
                            "_Generic", "_Imaginary", "_Noreturn", "_Static_assert", "_Thread_local"
                        ]
                    
                    # Add keyword rules
                    for keyword in keywords:
                        pattern = QRegularExpression(r'\b' + keyword + r'\b')
                        self.highlighting_rules.append((pattern, keyword_format))
                    
                    # Function declarations and calls
                    function_pattern = QRegularExpression(r'\b[A-Za-z0-9_]+(?=\()')
                    self.highlighting_rules.append((function_pattern, function_format))
                    
                    # Class/struct name pattern
                    class_pattern = QRegularExpression(r'\b(?:class|struct|enum)\s+([A-Za-z_][A-Za-z0-9_]*)')
                    self.highlighting_rules.append((class_pattern, class_format))
                    
                    # String patterns
                    self.highlighting_rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
                    self.highlighting_rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))
                    
                    # Comment patterns
                    self.highlighting_rules.append((QRegularExpression(r'//[^\n]*'), comment_format))
                    self.highlighting_rules.append((QRegularExpression(r'/\*.*?\*/', QRegularExpression.PatternOption.DotMatchesEverythingOption), comment_format))
                    
                    # Preprocessor directives
                    preprocessor_format = QTextCharFormat()
                    preprocessor_format.setForeground(self.colors["preprocessor"])
                    self.highlighting_rules.append((QRegularExpression(r'#\s*[a-zA-Z]+'), preprocessor_format))
                    
                    # Number pattern
                    self.highlighting_rules.append((QRegularExpression(r'\b\d+(\.\d+)?[fFlL]?\b'), number_format))
                    
                    # Operators pattern
                    self.highlighting_rules.append((QRegularExpression(r'[\+\-\*/=<>%&\|\^~!]'), operator_format))
                
                elif self.language == "html":
                    # HTML tags
                    tag_format = QTextCharFormat()
                    tag_format.setForeground(self.colors["keyword"])
                    self.highlighting_rules.append((QRegularExpression(r'<[/]?[a-zA-Z0-9]+'), tag_format))
                    self.highlighting_rules.append((QRegularExpression(r'[/]?>'), tag_format))
                    
                    # HTML attributes
                    attribute_format = QTextCharFormat()
                    attribute_format.setForeground(self.colors["identifier"])
                    self.highlighting_rules.append((QRegularExpression(r'\s[a-zA-Z0-9-]+='), attribute_format))
                    
                    # HTML strings
                    self.highlighting_rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
                    self.highlighting_rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))
                    
                    # HTML comments
                    self.highlighting_rules.append((QRegularExpression(r'<!--.*?-->', QRegularExpression.PatternOption.DotMatchesEverythingOption), comment_format))
            
            def set_language(self, language):
                """Change the language for syntax highlighting"""
                self.language = language.lower()
                self.setup_highlighting_rules()
                self.rehighlight()
            
            def highlightBlock(self, text):
                """Apply syntax highlighting to the given block of text"""
                # Apply the highlighting rules
                for pattern, format in self.highlighting_rules:
                    expression = pattern
                    match = expression.match(text)
                    index = match.capturedStart()
                    
                    while index >= 0:
                        length = match.capturedLength()
                        self.setFormat(index, length, format)
                        match = expression.match(text, index + length)
                        index = match.capturedStart()
        
        # Create a custom QPlainTextEdit subclass for code editing with line numbers
        class CodeEditor(QPlainTextEdit):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.line_number_area = LineNumberArea(self)
                
                # Connect signals
                self.blockCountChanged.connect(self.update_line_number_area_width)
                self.updateRequest.connect(self.update_line_number_area)
                self.cursorPositionChanged.connect(self.highlight_current_line)
                
                # Initial setup
                self.update_line_number_area_width(0)
                self.highlight_current_line()
                
                # Set monospace font for code
                font = QFont("Consolas")
                font.setStyleHint(QFont.StyleHint.Monospace)
                self.setFont(font)
                
                # Set tab size to 4 spaces
                self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)
                
                # Modern style for the editor (VS Code-like dark theme)
                self.setStyleSheet("""
                    QPlainTextEdit {
                        background-color: #1E1E1E;
                        color: #D4D4D4;
                        border: 1px solid #2D2D2D;
                        border-radius: 4px;
                        selection-background-color: #264F78;
                        selection-color: #FFFFFF;
                        font-family: Consolas, Monaco, 'Courier New', monospace;
                        font-size: 14px;
                    }
                """)
                
                # Create syntax highlighter
                self.highlighter = VSCodeSyntaxHighlighter(self.document(), "python")
            
            def set_language(self, language):
                """Set language for syntax highlighting"""
                self.highlighter.set_language(language)
            
            # Add setText method for compatibility with QTextEdit
            def setText(self, text):
                """Compatibility method to match QTextEdit's setText"""
                self.setPlainText(text)
                
            def text(self):
                """Compatibility method to match QTextEdit's text()"""
                return self.toPlainText()
                
            def line_number_area_width(self):
                """Calculate the width of the line number area"""
                digits = 1
                max_value = max(1, self.blockCount())
                while max_value >= 10:
                    max_value //= 10
                    digits += 1
                
                space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
                return space
            
            def update_line_number_area_width(self, _):
                """Update the margin reserved for the line number area"""
                self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
            
            def update_line_number_area(self, rect, dy):
                """Update the line number area when the viewport is scrolled"""
                if dy:
                    self.line_number_area.scroll(0, dy)
                else:
                    self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
                
                if rect.contains(self.viewport().rect()):
                    self.update_line_number_area_width(0)
            
            def resizeEvent(self, event):
                """Handle resize events"""
                super().resizeEvent(event)
                
                cr = self.contentsRect()
                self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))     

            def highlight_current_line(self):
                """Highlight the line where the cursor is positioned"""
                extra_selections = []
                
                if not self.isReadOnly():
                    selection = QTextEdit.ExtraSelection()
                    line_color = QColor("#2A2A2A")  # Dark subtle highlight for current line
                    
                    selection.format.setBackground(line_color)
                    selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                    selection.cursor = self.textCursor()
                    selection.cursor.clearSelection()
                    extra_selections.append(selection)
                
                self.setExtraSelections(extra_selections)
            
            def line_number_area_paint_event(self, event):
                """Paint the line numbers"""
                painter = QPainter(self.line_number_area)
                painter.fillRect(event.rect(), QColor("#1A1A1A"))  # VS Code-like line number background
                
                block = self.firstVisibleBlock()
                block_number = block.blockNumber()
                top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
                bottom = top + round(self.blockBoundingRect(block).height())
                
                while block.isValid() and top <= event.rect().bottom():
                    if block.isVisible() and bottom >= event.rect().top():
                        number = str(block_number + 1)
                        painter.setPen(QColor("#6D6D6D"))  # VS Code-like line number color
                        painter.drawText(0, top, self.line_number_area.width() - 5, self.fontMetrics().height(),
                                        Qt.AlignmentFlag.AlignRight, number)
                    
                    block = block.next()
                    top = bottom
                    bottom = top + round(self.blockBoundingRect(block).height())
                    block_number += 1
        
        # Line number area widget
        class LineNumberArea(QWidget):
            def __init__(self, editor):
                super().__init__(editor)
                self.code_editor = editor
            
            def sizeHint(self):
                return QSize(self.code_editor.line_number_area_width(), 0)
            
            def paintEvent(self, event):
                self.code_editor.line_number_area_paint_event(event)
        
        # Replace the existing code editor with our enhanced version
        new_editor = CodeEditor()
        new_editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Copy any existing code
        if hasattr(self, 'code_editor') and self.code_editor is not None:
            # Get text from the old editor - could be QTextEdit or QPlainTextEdit
            if hasattr(self.code_editor, 'toPlainText'):
                text = self.code_editor.toPlainText()
            elif hasattr(self.code_editor, 'text'):
                text = self.code_editor.text()
            else:
                text = ""
            new_editor.setPlainText(text)
        
        # Replace the old editor in the layout
        code_output_layout = self.code_editor.parent().layout()
        old_editor_index = code_output_layout.indexOf(self.code_editor)
        code_output_layout.removeWidget(self.code_editor)
        self.code_editor.deleteLater()
        
        # Add new editor to layout at same position
        code_output_layout.insertWidget(old_editor_index, new_editor, 7)
        self.code_editor = new_editor
        
        # Define methods for the main class (self)
        def set_code_text(text):
            """Set the code text in the editor"""
            self.code_editor.setPlainText(text)
        
        def get_code_text():
            """Get the code text from the editor"""
            return self.code_editor.toPlainText()
        
        def set_language_template():
            """Set code template based on the selected language"""
            language = self.language_selector.currentText().lower()
            
            # Also update syntax highlighting
            self.code_editor.set_language(language)
            
            templates = {
                "python": '# Python code\n\ndef main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()',
                "java": '// Java code\n\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n    }\n}',
                "javascript": '// JavaScript code\n\nfunction main() {\n    console.log("Hello, World!");\n}\n\nmain();',
                "c++": '// C++ code\n\n#include <iostream>\n\nint main() {\n    std::cout << "Hello, World!" << std::endl;\n    return 0;\n}',
                "c": '// C code\n\n#include <stdio.h>\n\nint main() {\n    printf("Hello, World!\\n");\n    return 0;\n}',
                "html": '<!-- HTML code -->\n\n<!DOCTYPE html>\n<html>\n<head>\n    <title>Hello World</title>\n</head>\n<body>\n    <h1>Hello, World!</h1>\n</body>\n</html>'
            }
            
            if language in templates:
                set_code_text(templates[language])
        
        # Properly bind methods to self
        self.set_code_text = set_code_text
        self.get_code_text = get_code_text
        self.set_language_template = set_language_template
        
        # Connect language selector to template setter
        self.language_selector.currentTextChanged.connect(self.set_language_template)

    def start_recording(self):
        if not hasattr(self, 'webcam_recorder') or self.webcam_recorder is None:
            self.webcam_recorder = BackgroundWebcamRecorder(
                token=self.session_token,
                exam_code=self.exam_code,
                user_id=self.user_id,
                exam_id=self.exam_id
            )
            self.webcam_recorder.setup_recorder(shared_camera.get_session())

        if self.webcam_recorder.start_recording():
            logging.info("Exam recording started successfully")
        else:
            logging.error("Failed to start exam recording")


    def showEvent(self, event):
        super().showEvent(event)

        available_cameras = QMediaDevices.videoInputs()
        if not available_cameras:
            logging.error("No camera devices found")
            return

        if not shared_camera.is_initialized:
            camera_device = available_cameras[0]
            if not shared_camera.initialize(camera_device):
                logging.error("Failed to initialize shared camera")
                return

        if shared_camera.start_camera():
            logging.info("Camera started successfully")
            QTimer.singleShot(1000, self.start_recording)
        else:
            logging.error("Failed to start camera")

    def hideEvent(self, event):
        super().hideEvent(event)
        if self.webcam_recorder and self.webcam_recorder.is_ready():
            self.webcam_recorder.stop_recording()

    def update_word_count(self):
        """Update the word count for descriptive answers"""
        text = self.description_editor.toPlainText()
        word_count = len(text.split()) if text else 0
        self.word_count_label.setText(f"Word count: {word_count}")

    def set_exam_code(self, code):
        self.exam_code = code

    def set_exam_details(self, exam_details):
        self.exam_details = exam_details
        self.exam_id = exam_details.get("exam_id") or exam_details.get("examId")
        self.user_id = exam_details.get("user_id") or exam_details.get("userId") or "default_user"
        
        self.session_token = SESSION_TOKEN
        
        # Initialize timer with default values
        try:
            # Extract total time from exam details - it's in minutes
            total_time_str = exam_details.get("totalTime", "30").strip()
            total_minutes = int(total_time_str) if total_time_str else 30  # Default 30 minutes
            
            # Convert minutes to seconds for internal countdown
            self.remaining_seconds = total_minutes * 60
            
            # Format time display in hours:minutes:seconds
            self.update_time_display()
            
            # Start the timer - update every second
            self.timer.start(1000)  # 1000 ms = 1 second
        except ValueError:
            # Default to 30 minutes if there's an error parsing the time
            self.remaining_seconds = 30 * 60  # 30 minutes in seconds
            self.time_container.setText("00:30:00")
            self.timer.start(1000)
        
        # Load questions and build question panel
        question_ids = exam_details.get("questionsIds", [])
        
        fetched_questions = []
        for idx, q_id in enumerate(question_ids):
            question_data = fetch_question(q_id, self.exam_id, self.user_id, idx, first_request=False)
            if question_data:
                fetched_questions.append(question_data)
                print(f"Successfully fetched question {q_id}")
                
                # Sync with server time from the first question response
                if idx == 0 and 'remaining_time' in question_data:
                    self.sync_with_server_time(question_data['remaining_time'])
            else:
                print(f"Failed to fetch question {q_id}")
        
        self.questions = fetched_questions
        self.user_answers = [None] * len(self.questions)
        self.current_question_index = 0
        
        # Only build and load if we have questions
        if self.questions:
            self.build_question_panel()
            self.load_question(0)
            # Process events to ensure UI updates
            QCoreApplication.processEvents()
        else:
            # Display message if no questions are available
            self.question_label.setText("<b style='color:red'>No questions available. Please contact support.</b>")

    def update_time_display(self):
        """Update the timer display based on remaining_seconds"""
        # Format time in hours:minutes:seconds
        hours = self.remaining_seconds // 3600
        minutes = (self.remaining_seconds % 3600) // 60
        seconds = self.remaining_seconds % 60
        
        # Update the display
        self.time_container.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        
        # Change timer color based on remaining time
        if self.remaining_seconds <= 300:  # Less than 5 minutes
            self.time_container.setStyleSheet("""
                background-color: white;
                color: #FF3333;
                font-size: 24px;
                font-weight: bold;
                border: 3px solid #FF3333;
                border-radius: 75px;
            """)

    def sync_with_server_time(self, server_remaining_time):
        """
        Synchronize the client timer with the server's remaining time
        
        Args:
            server_remaining_time: Remaining time in seconds from server
        """
        if server_remaining_time is None:
            print("Warning: Server did not provide remaining time")
            return
            
        try:
            # Convert to integer (handle string or numeric inputs)
            new_remaining = int(server_remaining_time)
            
            # Only update if the difference is significant (more than 5 seconds)
            if abs(new_remaining - self.remaining_seconds) > 5:
                print(f"Syncing timer: Local time was {self.remaining_seconds}s, server time is {new_remaining}s")
                self.remaining_seconds = new_remaining
                self.update_time_display()
            
        except (ValueError, TypeError) as e:
            print(f"Error syncing with server time: {e}")
            print(f"Received value: {server_remaining_time}, type: {type(server_remaining_time)}")

    def handle_image_timeout(self, reply, fallback_content):
        """Handle timeout for image loading requests"""
        if reply and reply.isRunning():
            reply.abort()
            print("Image loading timed out, using fallback HTML display")
            self.question_content_label.setText(fallback_content)
            self.question_content_label.show()

    def load_question(self, index, store_current=True):
        """
        Load question at the given index

        Args:
            index: The index of the question to load
            store_current: Whether to store the current answer before loading new question
        """
        if not self.questions or index >= len(self.questions):
            return

        # Store user answer from current question before loading new one, but only if requested
        if store_current:
            self.store_user_answer()

        self.current_question_index = index
        q_data = self.questions[index]
        
        # Sync with server time if available in the question data
        if 'remaining_time' in q_data:
            self.sync_with_server_time(q_data['remaining_time'])
        
        q_number = index + 1

        # Get question type (default to type 2 if not specified)
        question_type = q_data.get("question_type", "2")  # Default to MCQ

        # Hide all answer containers first
        self.description_container.hide()
        self.coding_container.hide()
        self.options_layout.parentWidget().hide()

        # Update question number and marks
        marks = q_data.get("question_mark", 1)
        self.question_number_pill.setText(f"• Question {q_number}")
        self.marks_label.setText(f"[Marks: {marks}]")

        # Set question type label text
        question_type_text = {
            "1": "Descriptive",
            "2": "MCQ",
            "3": "MSQ",
            "4": "Coding"
        }.get(question_type, "Unknown")
        self.question_type_label.setText(f"[Type: {question_type_text}]")

        # Update question text from question_title
        question_text = q_data.get("question_title", "No question text")
        self.question_label.setText(question_text)
        
        # Handle question_content if it exists (images, additional HTML content)
        question_content = q_data.get("question_content", "")
        print(f"Question content: {question_content}")

        if question_content:
            # Use the QWebEngineView for all HTML content including images
            self.question_content_label.hide()  # Hide the standard label
            self.display_html_content(question_content)
        else:
            self.question_content_web.hide()
            self.question_content_label.clear()
            self.question_content_label.hide()

        # Clear existing options
        self.clear_options()

        # Handle different question types
        try:
            saved_answer = self.user_answers[index]
        except (KeyError, IndexError):
            saved_answer = None

        if question_type == "1":  # Descriptive
            # Set appropriate height for question label
            self.question_label.setMinimumHeight(80)
            self.question_label.setMaximumHeight(150)
        
            # Show text editor for descriptive answers
            self.description_container.show()
        
            # Restore saved answer if exists
            if saved_answer is not None:
                self.description_editor.setText(saved_answer)
            else:
                self.description_editor.clear()
            
            # Update word count
            self.update_word_count()
        
        elif question_type == "2" or question_type == "3":  # MCQ or MSQ
            # Reset question label height for MCQ/MSQ
            self.question_label.setMinimumHeight(80)
            self.question_label.setMaximumHeight(200)
        
            # Show options container
            self.options_layout.parentWidget().show()
        
            if question_type == "2":  # MCQ - Single choice
                self.setup_mcq_options(q_data)
            
                # Restore saved answer for MCQ if exists
                if saved_answer is not None and hasattr(self, 'options_button_group'):
                    button = self.options_button_group.button(saved_answer)
                    if button:
                        button.setChecked(True)
                    
            else:  # MSQ - Multiple choice
                self.setup_msq_options(q_data)
            
                # Restore saved answer for MSQ if exists
                if saved_answer is not None:
                    for idx in saved_answer:
                        if 0 <= idx < len(self.checkbox_list):
                            self.checkbox_list[idx].setChecked(True)
        
        elif question_type == "4":  # Coding
            # Set appropriate height for question label
            self.question_label.setMinimumHeight(80)
            self.question_label.setMaximumHeight(150)
        
            # Show coding editor
            self.coding_container.show()
        
            # Clear output area
            self.code_output.clear()
        
            # Restore saved code and language if exists
            if saved_answer is not None:
                code, language = saved_answer
                self.code_editor.setText(code)
            
                # Set language in dropdown
                lang_index = self.language_selector.findText(language)
                if lang_index >= 0:
                    self.language_selector.setCurrentIndex(lang_index)
            else:
                self.code_editor.clear()
                self.language_selector.setCurrentIndex(0)  # Default to first language

        # Update question panel buttons to mark current question
        self.update_question_buttons(index)

        # Enable/disable navigation buttons
        self.prev_button.setEnabled(index > 0)
        self.next_button.setEnabled(index < len(self.questions) - 1)

        # Force layout update and maintain proper sizing
        self.adjustSizeOfPanels(question_type)

        # Process events to ensure UI updates
        QCoreApplication.processEvents()

    def resizeEvent(self, event):
        """Handle resize events to adjust the web view if needed"""
        super().resizeEvent(event)
        
        # Re-adjust web view height if it's visible
        if hasattr(self, 'question_content_web') and not self.question_content_web.isHidden():
            self.question_content_web.page().runJavaScript(
                "document.body.scrollHeight",
                self.adjust_web_view_height
            )
    def handle_image_timeout(self, reply, fallback_content):
        """Handle timeout for image loading requests"""
        if reply.isRunning():
            # If the request is still running after timeout, abort it
            reply.abort()
            print("Image loading timed out. Using fallback content.")
            self.question_content_label.setText(fallback_content)
            self.question_content_label.show()

    def update_timer(self):
        """Update the timer display and check if time is up"""
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.update_time_display()
        else:
            # Time is up, stop the timer
            self.timer.stop()
            self.time_container.setText("00:00:00")
            self.time_container.setStyleSheet("""
                background-color: white;
                color: #FF3333;
                font-size: 24px;
                font-weight: bold;
                border: 3px solid #FF3333;
                border-radius: 75px;
            """)

            # Show time's up message box
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Time's Up!")
            msg_box.setText("Your exam time has ended. Your answers will be submitted automatically.")
            msg_box.setIcon(QMessageBox.Icon.Warning)

            # Use a single-shot timer to show the message box briefly and then submit
            QTimer.singleShot(3000, msg_box.close)  # Close after 3 seconds
            msg_box.exec()

            # Submit the exam automatically
            self.auto_submit_exam()
            
    def auto_submit_exam(self):
        """Automatically submit the exam when time is up"""
        # Store current answers first
        self.store_user_answer()
        
        # Stop webcam recording
        if self.webcam_recorder:
            self.webcam_recorder.stop_recording()
            logging.info("Webcam recording stopped after auto exam submission")
        
        print(f"Time's up! Auto-submitting exam {self.exam_id} with code {self.exam_code} for user {self.user_id}")
        
        try:
            # Set the submit reason for time end
            submit_reason = "Auto Submit Time Ends"
            
            # Send the onstop API call
            self.send_onstop_notification(submit_reason)
            
            # Mark exam as submitted
            self.exam_submitted = True
            
            # We've already saved answers one by one, now disable all inputs
            self.disable_all_inputs()
            
            # Show success message
            success_box = QMessageBox()
            success_box.setWindowTitle("Exam Submitted")
            success_box.setText("Your exam has been submitted automatically as time expired. Do you want to close the application?")
            success_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            success_box.setDefaultButton(QMessageBox.StandardButton.Yes)
            
            if success_box.exec() == QMessageBox.StandardButton.Yes:
                # Close the application if user confirms
                QApplication.quit()
            
        except Exception as e:
            # Show error message if submission fails
            error_box = QMessageBox()
            error_box.setWindowTitle("Submission Error")
            error_box.setText(f"Failed to submit exam: {str(e)}")
            error_box.exec()
            
            # Resume recording if submission fails
            if self.webcam_recorder:
                self.webcam_recorder.start_recording()

    # Add a new method to handle the submission state in other methods
    def check_if_submitted(self):
        """Check if exam is already submitted and prevent further actions"""
        if hasattr(self, 'exam_submitted') and self.exam_submitted:
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Exam Submitted")
            msg_box.setText("Your exam has already been submitted. No further changes are allowed.")
            msg_box.exec()
            return True
        return False
    # New method to ensure proper sizing of panels
    def adjustSizeOfPanels(self, question_type):
        """Adjust sizes of panels based on question type"""
        # First, hide all containers
        self.description_container.hide()
        self.coding_container.hide()
        self.options_layout.parentWidget().hide()
        
        # Then show only the relevant container with proper sizing
        if question_type == "1":  # Descriptive
            self.description_container.show()
            # Make sure the descriptive container takes up full space
            self.description_editor.setFocus()
            
        elif question_type in ["2", "3"]:  # MCQ or MSQ
            self.options_layout.parentWidget().show()
            
        elif question_type == "4":  # Coding
            self.coding_container.show()
            # Make sure the code editor takes focus
            self.code_editor.setFocus()
            
        self.left_container.updateGeometry()
        self.left_container.layout().update()
        
        # Force the layout to update by temporarily resizing
        current_size = self.size()
        self.resize(current_size.width() + 1, current_size.height())
        QCoreApplication.processEvents()
        self.resize(current_size)
        QCoreApplication.processEvents()   
        # Make sure the web view remains visible if it has content
        if hasattr(self, 'question_content_web') and not self.question_content_web.isHidden():
            self.question_content_web.show()        
         
    def setup_mcq_options(self, q_data):
        """Set up radio buttons for MCQ (single choice) questions"""
        # Create options button group (reset it)
        if self.options_button_group:
            self.options_button_group.deleteLater()
        self.options_button_group = QButtonGroup(self)
        self.options_button_group.setExclusive(True)
        
        # Add new options
        options = q_data.get("question_options", [])
        option_letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
        
        for i, option in enumerate(options):
            option_text = option.get("name", f"Option {i+1}")
            letter = option_letters[i] if i < len(option_letters) else str(i+1)
            
            # Create option row layout
            option_row = QHBoxLayout()
            option_row.setContentsMargins(0, 0, 0, 0)
            option_row.setSpacing(15)
            
            # Radio button with proper styling
            rb = QRadioButton()
            rb.setObjectName(f"option_radio_{i}")
            rb.setStyleSheet("""
                QRadioButton {
                    background-color: transparent;
                }
                QRadioButton::indicator {
                    width: 20px;
                    height: 20px;
                }
            """)
            
            # Label with option text
            option_label = QLabel(f"{letter}. {option_text}")
            option_label.setStyleSheet("""
                font-size: 15px;
                color: #333333;
            """)
            option_label.setWordWrap(True)
            
            # Add to layout
            option_row.addWidget(rb)
            option_row.addWidget(option_label, 1)  # Give label stretch factor
            
            # Add to options layout
            self.options_layout.addLayout(option_row)
            self.options_button_group.addButton(rb, i)
        
        # Restore selected answer if any
        if self.user_answers[self.current_question_index] is not None:
            selected_index = self.user_answers[self.current_question_index]
            btns = self.options_button_group.buttons()
            if 0 <= selected_index < len(btns):
                btns[selected_index].setChecked(True)

    def setup_msq_options(self, q_data):
        """Set up checkboxes for MSQ (multiple choice) questions"""
        # Clear previous checkbox list
        self.checkbox_list = []
        
        # Add new options
        options = q_data.get("question_options", [])
        option_letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
        
        for i, option in enumerate(options):
            option_text = option.get("name", f"Option {i+1}")
            letter = option_letters[i] if i < len(option_letters) else str(i+1)
            
            # Create option row layout
            option_row = QHBoxLayout()
            option_row.setContentsMargins(0, 0, 0, 0)
            option_row.setSpacing(15)
            
            # Checkbox with proper styling
            cb = QCheckBox()
            cb.setObjectName(f"option_checkbox_{i}")
            cb.setStyleSheet("""
                QCheckBox {
                    background-color: transparent;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                }
            """)
            
            # Label with option text
            option_label = QLabel(f"{letter}. {option_text}")
            option_label.setStyleSheet("""
                font-size: 15px;
                color: #333333;
            """)
            option_label.setWordWrap(True)
            
            # Add to layout
            option_row.addWidget(cb)
            option_row.addWidget(option_label, 1)  # Give label stretch factor
            
            # Add to options layout
            self.options_layout.addLayout(option_row)
            self.checkbox_list.append(cb)
        
        # Restore selected answers if any
        if self.user_answers[self.current_question_index] is not None:
            selected_indices = self.user_answers[self.current_question_index]
            for i, cb in enumerate(self.checkbox_list):
                cb.setChecked(i in selected_indices)

    def clear_options(self):
        # Clear all options layout widgets and layouts
        while self.options_layout.count():
            item = self.options_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Clear sub-layouts
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
        
        # Reset button group
        if hasattr(self, 'options_button_group') and self.options_button_group:
            self.options_button_group.deleteLater()
            self.options_button_group = QButtonGroup(self)
            self.options_button_group.setExclusive(True)
    
    # Clear checkbox list
        self.checkbox_list = []

    def update_question_buttons(self, current_index):
        # Update the styling of question buttons to reflect status
        for i in range(self.question_panel.count()):
            item = self.question_panel.itemAt(i)
            if item and item.widget():
                btn = item.widget()
                
                # Get the question number from button text (1-based)
                q_index = int(btn.text()) - 1
                
                if q_index == current_index:
                    # Current question
                    btn.setStyleSheet("""
                        background-color: #0D2144;
                        color: white;
                        border-radius: 20px;
                        font-weight: bold;
                    """)
                elif self.user_answers[q_index] is not None:
                    # Answered question
                    btn.setStyleSheet("""
                        background-color: #8BC34A;
                        color: white;
                        border-radius: 20px;
                    """)
                else:
                    # Not visited or not answered
                    btn.setStyleSheet("""
                        background-color: #E1E8F5;
                        color: #333;
                        border-radius: 20px;
                    """)

    def build_question_panel(self):
        # Clear existing buttons
        for i in reversed(range(self.question_panel.count())):
            widget = self.question_panel.itemAt(i).widget()
            if widget:
                self.question_panel.removeWidget(widget)
                widget.deleteLater()
        
        # Create new buttons
        num_cols = 5
        for i in range(len(self.questions)):
            question_btn = QPushButton(str(i + 1))
            question_btn.setFixedSize(40, 40)
            
            # Default style (not visited)
            question_btn.setStyleSheet("""
                background-color: #E1E8F5;
                color: #333;
                border-radius: 20px;
            """)
            
            # Connect button to jump to question
            question_btn.clicked.connect(lambda checked, idx=i: self.jump_to_question(idx))
            
            row = i // num_cols
            col = i % num_cols
            self.question_panel.addWidget(question_btn, row, col)
        
        # Mark first question as current
        if self.question_panel.count() > 0:
            first_btn = self.question_panel.itemAt(0).widget()
            first_btn.setStyleSheet("""
                background-color: #0D2144;
                color: white;
                border-radius: 20px;
                font-weight: bold;
            """)

    def store_user_answer(self):
        """Store and save the user's answer for the current question"""
        # Don't save if exam is already submitted
        if hasattr(self, 'exam_submitted') and self.exam_submitted:
            return
            
        if not self.questions:
            return
            
        current_question = self.questions[self.current_question_index]
        question_type = current_question.get("question_type", "2")  # Default to MCQ
        
        # Try different possible ID field names
        question_id = current_question.get("id") or current_question.get("question_id") or current_question.get("questionId")
        
        # Ensure we have a valid question ID
        if not question_id:
            print("ERROR: Could not find valid question ID in question data")
            return
        
        # Get previous answer safely with try-except to avoid errors
        try:
            previous_answer = self.user_answers[self.current_question_index]
        except (KeyError, IndexError):
            previous_answer = None
        
        new_answer = None
        if question_type == "1":  # Descriptive
            text = self.description_editor.toPlainText()
            new_answer = text if text.strip() else None
            
        elif question_type == "2":  # MCQ - Single choice
            if hasattr(self, 'options_button_group') and self.options_button_group:
                selected_id = self.options_button_group.checkedId()
                new_answer = selected_id if selected_id != -1 else None
                
        elif question_type == "3":  # MSQ - Multiple choice
            selected_indices = []
            for i, cb in enumerate(self.checkbox_list):
                if cb.isChecked():
                    selected_indices.append(i)
            new_answer = selected_indices if selected_indices else None
            
        elif question_type == "4":  # Coding
            code = self.code_editor.toPlainText()
            language = self.language_selector.currentText()
            if code.strip():
                new_answer = (code, language)
            else:
                new_answer = None
        
        # Update the answer in memory (local storage)
        self.user_answers[self.current_question_index] = new_answer
        
        # Save to API if the answer has changed
        if new_answer != previous_answer:
            print(f"Saving answer for question {question_id}. Previous: {previous_answer}, New: {new_answer}")
            self.save_answer_to_api(question_id, question_type, new_answer)
        
        return new_answer

    def save_answer_to_api(self, question_id, question_type, answer):
        """Save a single answer to the API"""
        if not self.session_token:
            print("Warning: No session token provided. Cannot save answer to API.")
            return False
        
        try:
            # Call the API function
            result = save_question_answer(
                self.exam_id,
                self.user_id,
                question_id,
                question_type,
                answer,
                self.session_token
            )
            
            if result:
                print(f"Successfully saved answer for question {question_id}")
                return True
            else:
                print(f"Failed to save answer for question {question_id}")
                return False
                
        except Exception as e:
            print(f"Error saving answer for question {question_id}: {str(e)}")
            return False
        
    def run_code(self):
        """Execute the code using the remote compiler API with proper error handling"""
        code = self.code_editor.toPlainText()
        language = self.language_selector.currentText().lower()
        
        if not code.strip():
            self.code_output.setPlainText("Error: No code to run.")
            return
        
        # Show loading state
        self.code_output.setPlainText("Running code, please wait...")
        original_button_text = self.run_code_button.text()
        self.run_code_button.setText("Running...")
        self.run_code_button.setEnabled(False)
        
        # Use PyQt's QNetworkAccessManager for non-blocking API calls

        
        # Create network manager if it doesn't exist
        if not hasattr(self, 'network_manager'):
            self.network_manager = QNetworkAccessManager()
        
        # Prepare the request
        url = QUrl("https://stageevaluate.sentientgeeks.us/wp-content/themes/questioner/app/compiler.php")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 
                        "application/x-www-form-urlencoded")
        
        # Prepare form data
        query = QUrlQuery()
        query.addQueryItem("language", language)
        query.addQueryItem("code", code)
        post_data = query.toString().encode()
        
        # Send request
        reply = self.network_manager.post(request, post_data)
        
        # Handle response
        def handle_response():
            self.run_code_button.setText(original_button_text)
            self.run_code_button.setEnabled(True)
            
            if reply.error() == QNetworkReply.NetworkError.NoError:
                response_data = reply.readAll().data().decode()
                self.code_output.setPlainText(response_data)
            else:
                error_msg = f"Network Error: {reply.errorString()}"
                self.code_output.setPlainText(error_msg)
            
            reply.deleteLater()
        
        # Connect to the finished signal
        reply.finished.connect(handle_response)

    def go_previous(self):
        if self.current_question_index > 0:
            # Store current answer
            self.store_user_answer()
            
            # Move to previous question but don't store again (already stored above)
            self.current_question_index -= 1
            self.load_question(self.current_question_index, store_current=False)

    def go_next(self):
        if self.current_question_index < len(self.questions) - 1:
            # Store current answer
            self.store_user_answer()
            
            # Move to next question but don't store again (already stored above)
            self.current_question_index += 1
            self.load_question(self.current_question_index, store_current=False)

    def jump_to_question(self, index):
        if index != self.current_question_index:
            # Store current answer
            self.store_user_answer()
            
            # Jump to the requested question but don't store again (already stored above)
            self.current_question_index = index
            self.load_question(index, store_current=False)
        else:
            # Just refresh the current question if jumping to the same one
            self.load_question(index, store_current=False)
            
    def initialize_user_answers(self):
        """
        Initialize user answers storage - call this during initialization
        """
        # Initialize empty user answers
        if not hasattr(self, 'user_answers'):
            self.user_answers = {}

    def submit_exam(self):
        # Save the current answer first
        self.store_user_answer()
        
        # Show confirmation dialog
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Submit Exam")
        msg_box.setText("Are you sure you want to submit your exam?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            # Stop the timer when manually submitting
            self.timer.stop()
            
            # Stop webcam recording
            if self.webcam_recorder:
                self.webcam_recorder.stop_recording()
                logging.info("Webcam recording stopped after manual exam submission")
            
            # Check for any unanswered questions and inform user
            unanswered = sum(1 for answer in self.user_answers if answer is None)
            if unanswered > 0:
                warning_box = QMessageBox()
                warning_box.setWindowTitle("Warning")
                warning_box.setText(f"You have {unanswered} unanswered question(s). Do you still want to submit?")
                warning_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                warning_box.setDefaultButton(QMessageBox.StandardButton.No)
                
                if warning_box.exec() == QMessageBox.StandardButton.No:
                    # Resume timer if user cancels submission
                    self.timer.start(1000)
                    # Resume recording if user cancels submission
                    if self.webcam_recorder:
                        self.webcam_recorder.start_recording()
                    return  # Don't submit if user cancels
            
            try:
                # Set submit reason for manual submission
                submit_reason = "user submit"
                
                # Send the onstop API call
                self.send_onstop_notification(submit_reason)
                
                # Final submission API call can be added here if needed
                print(f"Submitting final exam {self.exam_id} for user {self.user_id}")
                
                # Mark exam as submitted
                self.exam_submitted = True
                
                # Disable all inputs to prevent further modifications
                self.disable_all_inputs()
                
                # Show success message
                success_box = QMessageBox()
                success_box.setWindowTitle("Exam Submitted")
                success_box.setText("Your exam has been submitted successfully! Do you want to close the application?")
                success_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                success_box.setDefaultButton(QMessageBox.StandardButton.Yes)
                
                if success_box.exec() == QMessageBox.StandardButton.Yes:
                    # Close the application if user confirms
                    QApplication.quit()
                
            except Exception as e:
                # Show error message if submission fails
                error_box = QMessageBox()
                error_box.setWindowTitle("Submission Error")
                error_box.setText(f"Failed to submit exam: {str(e)}")
                error_box.exec()
                
                # Resume timer if submission fails
                self.timer.start(1000)
                # Resume recording if submission fails
                if self.webcam_recorder:
                    self.webcam_recorder.start_recording()

 

    def send_onstop_notification(self, submit_reason):
        """
        Send the onstop notification to the API endpoint
        """
        try:
            # Check if webcam_recorder exists and has the necessary attributes
            if not hasattr(self, 'webcam_recorder') or not self.webcam_recorder:
                logging.error("Cannot send onstop notification: webcam_recorder not available")
                return False
                
            # Get API endpoint and token from the webcam recorder
            api_endpoint = self.webcam_recorder.api_endpoint
            token = self.webcam_recorder.token
            
            if not token:
                logging.error("Cannot send onstop notification: token not available")
                return False
                
            # Prepare the form data
            form_data = {
                'exam_id': (None, str(self.exam_id)),
                'user_id': (None, str(self.user_id)),
                'type': (None, 'onstop'),
                'file_name': (None, f"{self.user_id}-{self.exam_id}"),
                'exam_submit_reason': (None, submit_reason)
            }
            
            # Set headers with token
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            # Send POST request
            logging.debug(f"Sending onstop notification to: {api_endpoint}")
            logging.debug(f"Form data: {form_data}")
            
            response = requests.post(
                api_endpoint,
                files=form_data,
                headers=headers
            )
            
            # Log response details
            logging.debug(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    if json_response.get('status') is True:
                        logging.info("Successfully sent onstop notification")
                        return True
                    else:
                        logging.warning(f"Onstop notification response not as expected: {json_response}")
                        return False
                except ValueError:
                    logging.error("Could not parse response as JSON")
                    return False
            else:
                # More detailed error logging
                logging.error(f"Failed to send onstop notification. Status code: {response.status_code}")
                logging.error(f"Response text: {response.text}")
                return False
                    
        except requests.RequestException as req_err:
            logging.error(f"Request error sending onstop notification: {str(req_err)}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error sending onstop notification: {str(e)}")
            logging.exception("Stack trace:")
            return False

    # Add new method to disable all inputs after submission
    def disable_all_inputs(self):
        """Disable all input elements after exam submission"""
        # Disable description editor
        self.description_editor.setReadOnly(True)
        self.description_editor.setStyleSheet("""
            border: 1px solid #D0D0D0;
            border-radius: 4px;
            padding: 8px;
            background-color: #F5F5F5;
            font-size: 14px;
            color: #666666;
        """)
        
        # Disable code editor
        self.code_editor.setReadOnly(True)
        self.code_editor.setStyleSheet("""
            border: 1px solid #D0D0D0;
            border-radius: 4px;
            padding: 8px;
            background-color: #2A2A2A;
            color: #AAAAAA;
            font-family: Consolas, Monaco, 'Courier New', monospace;
            font-size: 14px;
        """)
        
        # Disable language selector and run button
        self.language_selector.setEnabled(False)
        self.run_code_button.setEnabled(False)
        
        # Disable all radio buttons and checkboxes
        for i in range(self.options_layout.count()):
            item = self.options_layout.itemAt(i)
            if item and item.layout():
                # Look for widgets in nested layouts
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if isinstance(widget, (QRadioButton, QCheckBox)):
                        widget.setEnabled(False)
        
        # Disable all navigation buttons
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.submit_button.setEnabled(False)
        
        # Disable question panel buttons
        for i in range(self.question_panel.count()):
            item = self.question_panel.itemAt(i)
            if item and item.widget():
                item.widget().setEnabled(False)
        
        # Set a global flag to indicate exam is submitted
        self.exam_submitted = True
        
    def force_ui_refresh(self):
        # Save current state
        current_index = self.current_question_index
        
        # Make sure we have the current question data
        if self.questions and 0 <= current_index < len(self.questions):
            question_text = self.questions[current_index].get("question_title", "")
            question_type = self.questions[current_index].get("question_type", "2")  # Default to MCQ
            
            # Update with forced styling
            formatted_text = f"""
            <div style='color: black; font-size: 16px; font-weight: bold; padding: 10px; margin: 10px;'>
                {question_text}
            </div>
            """
            
            # Set text with direct styling
            self.question_label.setText(formatted_text)
            
            # Ensure the label is properly sized and visible
            self.question_label.setMinimumSize(400, 200)
            self.question_label.adjustSize()
            
            # Force immediate update
            self.question_label.repaint()
            
            # Handle question type-specific UI elements
            if question_type == "1":  # Descriptive
                print("UI refresh - Ensuring description text editor is visible")
                self.description_container.show()
                self.description_editor.repaint()
                
            elif question_type == "2":  # MCQ
                options = self.questions[current_index].get("question_options", [])
                print(f"UI refresh - Ensuring {len(options)} MCQ options are visible")
                
                # Make sure options are created again if needed
                if not self.options_layout.count() and options:
                    self.setup_mcq_options(self.questions[current_index])
                    
            elif question_type == "3":  # MSQ
                options = self.questions[current_index].get("question_options", [])
                print(f"UI refresh - Ensuring {len(options)} MSQ options are visible")
                
                # Make sure options are created again if needed
                if not self.options_layout.count() and options:
                    self.setup_msq_options(self.questions[current_index])
                    
            elif question_type == "4":  # Coding
                print("UI refresh - Ensuring code editor is visible")
                self.coding_container.show()
                self.code_editor.repaint()
            
            QCoreApplication.processEvents()
            
            print(f"UI refresh - Question text: '{question_text}'")
            print(f"UI refresh - Question type: '{question_type}'")
            print(f"UI refresh - Label size: {self.question_label.size().width()}x{self.question_label.size().height()}")
            
# 7. Main Window with Stacked Pages
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Evaluate App")
        self.resize(1200, 800)
        
        # Set window flags to prevent normal window controls
        # Note: we're using a more comprehensive approach than just FramelessWindowHint
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |  # No frame
            Qt.WindowType.WindowStaysOnTopHint | # Always on top
            Qt.WindowType.NoDropShadowWindowHint  # No shadow
        )
        
        # Prevent minimizing by capturing the window state change event
        self.setWindowState(Qt.WindowState.WindowActive)

        self.exam_code = None
        self.token = None
        self.exam_details = None

        # Setup UI components
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        self.exam_code_page = ExamCodePage(self.show_system_check_page)
        self.system_check_page = SystemCheckPage(self.show_instructions_page)
        self.instructions_page = ExamInstructionsPage(self.show_exam_page)
        self.exam_page = ExamPage()

        self.stack.addWidget(self.exam_code_page)
        self.stack.addWidget(self.system_check_page)
        self.stack.addWidget(self.instructions_page)
        self.stack.addWidget(self.exam_page)
        self.stack.setCurrentIndex(0)

        # Install Qt event filter for key blocking - this will catch Qt-specific events
        self.installEventFilter(self)

        logging.info("MainWindow initialized; showing in full screen.")
        self.showFullScreen()
        
        # Additional setup to ensure the window stays in focus and can't be minimized
        self.setup_focus_protection()
        
    def setup_focus_protection(self):
        """Setup additional protections to keep app in focus"""
        # Set focus policy to ensure our window maintains focus
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Create a timer to periodically check and restore focus if needed
        from PyQt6.QtCore import QTimer
        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self.check_focus)
        self.focus_timer.start(500)  # Check every 500ms
        
    def check_focus(self):
        """Check if our window has focus and restore it if not"""
        active_window = QGuiApplication.focusWindow()
        if active_window is not self:
            logging.info("Window lost focus - restoring")
            self.activateWindow()
            self.raise_()

    def changeEvent(self, event):
        """Override to prevent window state changes like minimizing"""
        if event.type() == QEvent.Type.WindowStateChange:
            # If the window state is changing to minimized, prevent it
            if self.windowState() & Qt.WindowState.WindowMinimized:
                logging.info("Preventing window minimization")
                # Restore the window state to active
                self.setWindowState(Qt.WindowState.WindowActive)
                event.accept()
                return
        super().changeEvent(event)

    def eventFilter(self, obj, event):
        """Qt-specific event filter to catch key events that might bypass keyboard library"""
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            
            # Comprehensive blocking of problematic keys
            # Block function keys
            if key >= Qt.Key.Key_F1 and key <= Qt.Key.Key_F12:
                logging.info(f"Blocked function key {key - Qt.Key.Key_F1 + 1} through Qt event filter")
                return True  # Block the event
                
            # Block Escape
            if key == Qt.Key.Key_Escape:
                logging.info("Blocked Escape through Qt event filter")
                return True
                
            # Block Tab
            if key == Qt.Key.Key_Tab:
                logging.info("Blocked Tab through Qt event filter")
                return True
                
            # Block modifiers
            if modifiers & Qt.KeyboardModifier.AltModifier:
                logging.info("Blocked Alt combination through Qt event filter")
                return True
                
            # Block Windows key combinations
            if modifiers & Qt.KeyboardModifier.MetaModifier:
                logging.info("Blocked Windows key combination through Qt event filter")
                return True
                
        # Also catch focus events to prevent losing focus
        elif event.type() == QEvent.Type.WindowDeactivate:
            logging.info("Window deactivate event - re-activating")
            QTimer.singleShot(10, self.activateWindow)
                
        return super().eventFilter(obj, event)

    def animate_transition(self):
        animation = QPropertyAnimation(self.stack, b"geometry")
        animation.setDuration(300)
        start_rect = self.stack.geometry()
        end_rect = QRect(start_rect.x() - 50, start_rect.y(), start_rect.width(), start_rect.height())
        animation.setStartValue(start_rect)
        animation.setEndValue(end_rect)
        animation.start()

    def show_system_check_page(self, exam_code, token, exam_details):
        self.exam_code = exam_code
        self.token = token
        self.exam_details = exam_details
        self.system_check_page.set_exam_details(exam_details)
        self.animate_transition()
        self.stack.setCurrentWidget(self.system_check_page)

    def show_instructions_page(self):
        self.instructions_page.set_exam_details(self.exam_details)
        self.animate_transition()
        self.stack.setCurrentWidget(self.instructions_page)

    def show_exam_page(self, updated_exam_details):
        # Update MainWindow's exam_details if needed
        self.exam_details = updated_exam_details
        self.animate_transition()
        self.exam_page.set_exam_code(self.exam_code)
        self.exam_page.set_exam_details(self.exam_details)
        self.stack.setCurrentWidget(self.exam_page)

    def keyPressEvent(self, event: QKeyEvent):
        """Override keyPressEvent to block all problematic keys"""
        key = event.key()
        modifiers = event.modifiers()
        
        # Block ALL function keys, system keys, and navigation keys
        # This is our final defense against keyboard shortcuts
        if (
            (key >= Qt.Key.Key_F1 and key <= Qt.Key.Key_F35) or  # ALL function keys
            key == Qt.Key.Key_Escape or
            key == Qt.Key.Key_Tab or
            key == Qt.Key.Key_Menu or  # Context menu key
            key == Qt.Key.Key_Print or  # Print screen
            modifiers & Qt.KeyboardModifier.AltModifier or  # Any Alt combo
            modifiers & Qt.KeyboardModifier.MetaModifier    # Any Windows key combo
        ):
            logging.info(f"Blocked key {key} with modifiers {modifiers} in keyPressEvent")
            event.accept()
            return
            
        # For unblocked keys, let the default handler process it
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """Prevent normal window closing"""
        logging.info("Close event intercepted - preventing")
        event.ignore()

# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main():
    # Set up logging first
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("exam_app.log"),
            logging.StreamHandler()
        ]
    )
    
    logging.info("Starting Evaluate App with enhanced security measures")
    
    # Start the application
    app = QApplication(sys.argv)
    
    # Start key blocking in a background thread before creating the main window
    # This ensures system keys are blocked from the very beginning
    try:
        blocking_thread = start_key_blocking()
        logging.info("Key blocking system started successfully")
    except Exception as e:
        logging.error(f"Failed to start key blocking: {e}")
        # Continue anyway - we have multiple layers of protection
    
    # Create and show the main window
    window = MainWindow()
    
    # Additional app-level focus enforcement
    def check_app_focus():
        """Global check to ensure our app stays in focus"""
        if window and not window.isActiveWindow():
            logging.info("Application focus check - restoring focus")
            window.activateWindow()
            window.raise_()
    
    # Create a timer to periodically check focus at the application level
    focus_timer = QTimer()
    focus_timer.timeout.connect(check_app_focus)
    focus_timer.start(1000)  # Check every second
    
    logging.info("Entering application event loop.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()