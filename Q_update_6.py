import os
import sys
import time
from datetime import datetime
import logging
import threading
import subprocess
import json

import ctypes
from ctypes import wintypes

import psutil
import numpy as np
import sounddevice as sd
import keyboard  # third-party module for global key events
import requests

from PyQt6.QtCore import (
    Qt,
    QCoreApplication,
    QTimer,
    QEvent,
    QPropertyAnimation,
    QRect,
)
from PyQt6.QtGui import QFont, QPixmap, QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QStackedWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QLineEdit,
    QRadioButton,
    QGridLayout,
    QFrame,
    QCheckBox,
    QButtonGroup,
    QTextEdit,
    QPlainTextEdit,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtMultimedia import (
    QMediaRecorder,
    QMediaFormat,
    QMediaCaptureSession,
    QMediaDevices,
    QCamera,
    QCameraDevice
)
from PyQt6.QtMultimediaWidgets import (
    QVideoWidget
)

from PyQt6.QtCore import QUrl,QSize


# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
logging.basicConfig(filename="keyblock.log", level=logging.INFO, format="%(asctime)s - %(message)s")
logging.info("Application starting...")

# -----------------------------------------------------------------------------
# Key Blocking
# -----------------------------------------------------------------------------
def block_keys():
    for key in ['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12']:
        keyboard.block_key(key)
        logging.info(f"Blocking {key}")
    keyboard.block_key('left windows')
    keyboard.block_key('right windows')
    logging.info("Blocking Windows keys")
    keyboard.block_key('esc')
    logging.info("Blocking 'esc' key")

def start_blocking():
    try:
        block_keys()
    except Exception as e:
        logging.error(f"Error blocking keys: {e}")

blocking_thread = threading.Thread(target=start_blocking, daemon=True)
blocking_thread.start()

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
        default_output = sd.default.device[1]
        device_info = sd.query_devices(default_output)
        hostapi_info = sd.query_hostapis()[device_info['hostapi']]
        print(f"Using device: {device_info['name']} ({device_info['hostapi']})")
        if "WASAPI" in hostapi_info['name']:
            print("Using WASAPI Loopback for audio check.")
            recording = sd.rec(
                int(duration * fs),
                samplerate=fs,
                channels=1,
                dtype='float32',
                device=default_output,
                blocking=True,
                extra_settings=sd.WasapiSettings(loopback=True)
            )
        else:
            print("WASAPI Loopback not available, using microphone instead.")
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
            sd.wait()
        amplitude = np.max(np.abs(recording))
        print(f"Detected audio amplitude: {amplitude}")
        result = "Failed" if amplitude > 0.05 else "OK"
        logging.info(f"Audio check result: {result} (amplitude={amplitude})")
        return result
    except Exception as e:
        logging.error(f"Audio check error: {e}")
        print(f"Audio check failed: {e}")
        return "Failed"

def check_video():
    available = QMediaDevices.videoInputs()
    result = "OK" if available else "Failed"
    logging.info(f"Video check: {result}")
    return result

def check_screen_sharing():
    known_keywords = {"zoom", "skype", "teamviewer"}
    for proc in psutil.process_iter(['name']):
        try:
            proc_name = proc.info['name']
            if proc_name and any(keyword in proc_name.lower() for keyword in known_keywords):
                logging.info(f"Screen sharing app detected: {proc_name}")
                return "Failed"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    logging.info("Screen sharing check: OK")
    return "OK"

def check_monitor():
    result = "OK" if len(QApplication.screens()) == 1 else "Failed"
    logging.info(f"Monitor check: {result}")
    return result

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
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        form_layout = QVBoxLayout()
        form_layout.addStretch()

        welcome_label = QLabel("Welcome to Evaluate")
        welcome_label.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(welcome_label)

        title_label = QLabel("Enter Exam Code")
        title_label.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(title_label)

        self.exam_code_edit = QLineEdit()
        self.exam_code_edit.setPlaceholderText("Exam Code")
        self.exam_code_edit.setFont(QFont("Arial", 24))
        self.exam_code_edit.setMinimumHeight(50)
        self.exam_code_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(self.exam_code_edit)

        submit_button = QPushButton("Submit")
        submit_button.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        submit_button.setMinimumHeight(60)
        submit_button.setStyleSheet("""
            QPushButton { background-color: #00205b; color: white; border-radius: 6px; padding: 10px 20px; }
            QPushButton:hover { background-color: #001b4f; }
        """)
        submit_button.clicked.connect(self.handle_exam_code)
        form_layout.addWidget(submit_button, alignment=Qt.AlignmentFlag.AlignCenter)
        form_layout.addStretch()

        main_layout.addLayout(form_layout)

        logo_layout = QVBoxLayout()
        logo_label = QLabel(self)
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        logo_width = int(screen_size.width() * 0.9)
        logo_height = int(screen_size.height() * 0.9)
        pixmap = QPixmap("772.png")
        if not pixmap.isNull():
            logo_label.setPixmap(pixmap.scaled(logo_width, logo_height,
                                               Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation))
        else:
            logo_label.setText("Logo")
            logo_label.setFont(QFont("Arial Cinzel", 20, QFont.Weight.Bold))
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignCenter)
        logo_layout.addStretch()
        main_layout.addLayout(logo_layout)

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
        self.start_checks()

    def set_exam_details(self, exam_details):
        self.exam_details = exam_details
        print("\n✅ Exam Details in SystemCheckPage:", self.exam_details)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(15)

        header = QLabel("System & Device Checks")
        header.setFont(QFont("Arial", 26, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        self.video_label = QLabel("Video Check: Pending")
        self.audio_label = QLabel("Audio Check: Pending")
        self.machine_label = QLabel("Machine Requirement: Pending")
        self.screen_label = QLabel("Screen Sharing App: Pending")
        self.funkey_label = QLabel("Function Key Block: Pending")
        self.monitor_label = QLabel("Monitor Check: Pending")

        for lbl in [self.video_label, self.audio_label, self.machine_label,
                    self.screen_label, self.funkey_label, self.monitor_label]:
            lbl.setFont(QFont("Arial", 18))
            layout.addWidget(lbl)

        self.select_devices_button = QPushButton("Select Devices")
        self.select_devices_button.setFont(QFont("Arial", 18))
        self.select_devices_button.clicked.connect(self.handle_select_devices)
        layout.addWidget(self.select_devices_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.status_message = QLabel("")
        self.status_message.setFont(QFont("Arial", 18))
        self.status_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_message)

        self.continue_button = QPushButton("Continue")
        self.continue_button.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.continue_button.setEnabled(False)
        self.continue_button.clicked.connect(self.on_continue)
        layout.addWidget(self.continue_button, alignment=Qt.AlignmentFlag.AlignCenter)

    def start_checks(self):
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.update_checks)
        self.check_timer.start(1000)
        self.check_counter = 0

    def update_checks(self):
        self.check_counter += 1
        if self.check_counter >= 3:
            self.video_label.setText("Video Check: " + check_video())
            self.audio_label.setText("Audio Check: " + check_audio())
            self.machine_label.setText("Machine Requirement: OK")
            self.screen_label.setText("Screen Sharing App: " + check_screen_sharing())
            self.funkey_label.setText("Function Key Block: OK")
            self.monitor_label.setText("Monitor Check: " + check_monitor())
            self.check_timer.stop()
            if all(lbl.text().endswith("OK") for lbl in [self.video_label, self.audio_label, self.machine_label,
                                                         self.screen_label, self.funkey_label, self.monitor_label]):
                self.status_message.setText("All checks passed!")
                self.continue_button.setEnabled(True)
            else:
                self.status_message.setText("One or more checks failed. Please contact admin.")
        else:
            for lbl in [self.video_label, self.audio_label, self.machine_label,
                        self.screen_label, self.funkey_label, self.monitor_label]:
                lbl.setText(f"{lbl.text().split(':')[0]}: Checking...")

    def handle_select_devices(self):
        dialog = DeviceSelectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            logging.info("Devices confirmed. Running system checks again...")
            self.check_timer.start(1000)
            self.check_counter = 0
        else:
            logging.info("Device selection cancelled.")

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
            self.recorder.stop()
            # Upload the current chunk
            self.upload_current_chunk()
            # Start a new chunk
            self.update_chunk_file()
            self.recorder.record()
    
    def upload_current_chunk(self):
        if not self.current_chunk_file or not os.path.exists(self.current_chunk_file):
            logging.error(f"Chunk file doesn't exist: {self.current_chunk_file}")
            return False
        
        try:
            # Create the filename in the format shown in Postman: userId-examId.mp4
            file_name = f"{self.user_id}-{self.exam_id}.mp4"
            
            # Log attempt to upload file
            file_size = os.path.getsize(self.current_chunk_file)
            logging.debug(f"Attempting to upload chunk: {self.current_chunk_file} (Size: {file_size} bytes)")
            
            # Prepare the form data exactly as shown in the Postman screenshot
            form_data = {
                'exam_id': (None, str(self.exam_id)),
                'user_id': (None, str(self.user_id)),
                'chunk': (file_name, open(self.current_chunk_file, 'rb'), 'multipart/form-data'),
                'type': (None, 'ondataavailable'),
                'file_name': (None, f"{self.user_id}-{self.exam_id}")  
            }
            
            # Set headers with token
            headers = {
                'Authorization': f'Bearer {self.token}'
            }
            
            # Send POST request with multipart form data
            logging.debug(f"Sending request to: {self.api_endpoint}")
            response = requests.post(
                self.api_endpoint,
                files=form_data,
                headers=headers
            )
            
            # Log response details
            logging.debug(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    if json_response.get('status') is True and json_response.get('message') == "Chunk save successful.":
                        logging.info(f"Successfully uploaded chunk: {file_name}")
                        # Delete the file after uploading
                        os.remove(self.current_chunk_file)
                        return True
                    else:
                        logging.warning(f"Upload response not as expected: {json_response}")
                        return False
                except ValueError:
                    logging.error("Could not parse response as JSON")
                    return False
            else:
                # More detailed error logging
                logging.error(f"Failed to upload chunk. Status code: {response.status_code}")
                logging.error(f"Response text: {response.text}")
                
                # Try to parse JSON response for more details
                try:
                    error_details = response.json()
                    logging.error(f"Error details: {error_details}")
                except:
                    logging.error("Could not parse error response as JSON")
                    
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

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        title_label = QLabel("Choose Your Audio & Video Device")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        audio_layout = QHBoxLayout()
        audio_label = QLabel("Select Audio Device:")
        audio_label.setFont(QFont("Arial", 14))
        self.audio_combo = QComboBox()
        self.audio_combo.setFont(QFont("Arial", 14))
        self.audio_combo.addItems([
            "Default - Microphone Array (Intel® Smart Sound Tech)",
            "External USB Microphone",
            "Bluetooth Headset"
        ])
        audio_layout.addWidget(audio_label)
        audio_layout.addWidget(self.audio_combo)
        layout.addLayout(audio_layout)

        video_layout = QHBoxLayout()
        video_label = QLabel("Select Video Device:")
        video_label.setFont(QFont("Arial", 14))
        self.video_combo = QComboBox()
        self.video_combo.setFont(QFont("Arial", 14))
        self.video_combo.addItems([
            "Integrated Camera (04f2:b725)",
            "External USB Camera",
            "Virtual Camera"
        ])
        video_layout.addWidget(video_label)
        video_layout.addWidget(self.video_combo)
        layout.addLayout(video_layout)

        self.show_demo_button = QPushButton("Show Demo")
        self.show_demo_button.setFont(QFont("Arial", 14))
        self.show_demo_button.clicked.connect(self.on_show_demo_clicked)
        layout.addWidget(self.show_demo_button, alignment=Qt.AlignmentFlag.AlignRight)

    def on_show_demo_clicked(self):
        audio_device = self.audio_combo.currentText()
        video_device = self.video_combo.currentText()
        demo_dialog = DemoPreviewDialog(audio_device, video_device, parent=self)
        if demo_dialog.exec() == QDialog.DialogCode.Accepted:
            logging.info("Devices confirmed via demo.")
            self.accept()
        else:
            logging.info("Device demo cancelled.")

# 4. Demo Preview Dialog
class DemoPreviewDialog(QDialog):
    def __init__(self, audio_device, video_device, parent=None):
        super().__init__(parent)
        self.audio_device = audio_device
        self.video_device = video_device
        self.setWindowTitle("Check Audio & Video")
        self.setModal(True)
        self.resize(600, 400)
        self.check_counter = 0
        self.setup_ui()
        self.start_camera_preview()
        self.start_real_time_check()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title_label = QLabel("Check Audio & Video")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(400, 250)
        layout.addWidget(self.video_widget)

        self.audio_label = QLabel(f"Audio Device: {self.audio_device}")
        self.audio_label.setFont(QFont("Arial", 14))
        self.audio_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.audio_label)

        red_note = QLabel("<p style='color:red;'>If the camera preview and audio device are OK, click 'Confirm'. Otherwise, click 'Select Again'.</p>")
        red_note.setWordWrap(True)
        red_note.setFont(QFont("Arial", 14))
        layout.addWidget(red_note)

        button_layout = QHBoxLayout()
        self.select_again_btn = QPushButton("Select Again")
        self.select_again_btn.clicked.connect(self.on_select_again)
        self.confirm_btn = QPushButton("Confirm")
        self.confirm_btn.clicked.connect(self.on_confirm)
        button_layout.addStretch()
        button_layout.addWidget(self.select_again_btn)
        button_layout.addWidget(self.confirm_btn)
        layout.addLayout(button_layout)

    def start_camera_preview(self):
        available_cameras = QMediaDevices.videoInputs()
        if available_cameras:
            # Initialize the shared camera with the selected device
            shared_camera.initialize(available_cameras[0])
            
            # Get the shared capture session and set video output to preview widget
            self.capture_session = shared_camera.get_session()
            self.capture_session.setVideoOutput(self.video_widget)
            
            # Start the camera
            shared_camera.start_camera()
            logging.info("Camera preview started using shared camera session.")
        else:
            error_label = QLabel("No camera available")
            error_label.setFont(QFont("Arial", 14))
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout().addWidget(error_label)
            logging.warning("No camera available.")

    def start_real_time_check(self):
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.update_device_status)
        self.check_timer.start(1000)

    def update_device_status(self):
        self.check_counter += 1
        if self.check_counter < 3:
            self.device_status = "Checking devices..."
        else:
            self.device_status = "Audio: OK | Video: OK"
            self.check_timer.stop()
            logging.info("Device status: " + self.device_status)

    def on_select_again(self):
        if hasattr(self, 'camera'):
            self.camera.stop()
            logging.info("Camera stopped on select again.")
        self.reject()

    def on_confirm(self):
        if hasattr(self, 'camera'):
            self.camera.stop()
            logging.info("Camera stopped on confirm.")
        self.accept()

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
        layout.setContentsMargins(40, 10, 40, 40)
        layout.setSpacing(15)

        title = QLabel("Welcome To SentientGeeks Assessment Exam")
        title.setFont(QFont("Arial", 26, QFont.Weight.Bold))
        title.setStyleSheet("color: #0080ff;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        banner = QLabel("Please read the following instructions carefully before starting the exam:")
        banner.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        banner.setStyleSheet("background-color: #ff0000; color: #fff; padding: 10px; border-radius: 4px;")
        layout.addWidget(banner, alignment=Qt.AlignmentFlag.AlignCenter)

        instructions_html = """
        <ol style="font-size:18px; line-height: 1.8;">
            <li>Exam can only be started on desktop or laptop devices.</li>
            <li>Ensure that your camera and microphone are connected and grant the necessary permissions before starting the exam.</li>
            <li>Close all other programs before starting your exam.</li>
            <li>Do not use any browser extensions (e.g., Grammarly), as they may cause exam termination.</li>
            <li>Ensure you have a stable internet and power connection.</li>
            <li>Do not press the <b>Esc</b>, <b>Windows</b>, or any other shortcut button.</li>
            <li>Do not exit full-screen mode.</li>
            <li>Do not refresh the page during the exam.</li>
            <li>Avoid clicking on any pop-ups during the exam.</li>
            <li>If you do not submit your exam within the provided time, your answers will be automatically saved.</li>
            <li>Close your browser only after the "Thank You" page is visible.</li>
        </ol>
        """
        instructions_label = QLabel(instructions_html)
        instructions_label.setWordWrap(True)
        instructions_label.setFont(QFont("Arial", 18))
        layout.addWidget(instructions_label)

        self.message_label = QLabel("")
        self.message_label.setFont(QFont("Arial", 18))
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)

        self.countdown_label = QLabel("")
        self.countdown_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.countdown_label)

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

            # Refresh exam details using a valid exam identifier (e.g., exam code)
            exam_link = self.exam_details.get("exam_link") or ""  # Adjust as needed
            print("🔹 Calling get_exam_details after countdown ends with exam_link:", exam_link)
            updated_details = get_exam_details(SESSION_TOKEN, exam_link)
            print("🔹 Updated Exam Details received:", updated_details)
            logging.info("Updated Exam Details received after countdown: " + str(updated_details))
            
            if updated_details and updated_details.get("status"):
                self.exam_details = updated_details
                question_ids = updated_details.get("questionsIds", [])
                print("🔹 Question IDs after update:", question_ids)
                logging.info("Question IDs after update: " + str(question_ids))
                
                if question_ids:
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
            else:
                print("❌ Failed to refresh exam details.")
                logging.error("Failed to refresh exam details after countdown.")

            # Call the callback to switch to the exam page with updated details
            self.switch_to_exam_callback(self.exam_details)
            


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
        self.language_selector.addItems(["Python", "Java", "JavaScript", "C++", "C#", "HTML"])
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
       
        self.session_token =SESSION_TOKEN 
        
        
        # Get total time and question details
        try:
            # Extract total time from exam details - it's in minutes
            total_time_str = exam_details.get("totalTime", "30").strip()
            total_minutes = int(total_time_str) if total_time_str else 30  # Default 30 minutes
            
            # Convert minutes to seconds for internal countdown
            self.remaining_seconds = total_minutes * 60
            
            # Format time display in hours:minutes:seconds
            hours = self.remaining_seconds // 3600
            minutes = (self.remaining_seconds % 3600) // 60
            seconds = self.remaining_seconds % 60
            self.time_container.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
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

    def load_question(self, index):
        if not self.questions or index >= len(self.questions):
            return
        
        # Store user answer from current question before loading new one
        self.store_user_answer()
        
        self.current_question_index = index
        q_data = self.questions[index]
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
        
        # Update question text
        question_text = q_data.get("question_title", "No question text")
        self.question_label.setText(question_text)
        
        # Clear existing options
        self.clear_options()
        
        # Handle different question types
        if question_type == "1":  # Descriptive
            # Set appropriate height for question label
            self.question_label.setMinimumHeight(80)
            self.question_label.setMaximumHeight(150)
            
            # Show text editor for descriptive answers
            self.description_container.show()
            
            # Restore saved answer if exists
            if self.user_answers[index] is not None:
                self.description_editor.setText(self.user_answers[index])
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
            else:  # MSQ - Multiple choice
                self.setup_msq_options(q_data)
            
        elif question_type == "4":  # Coding
            # Set appropriate height for question label
            self.question_label.setMinimumHeight(80)
            self.question_label.setMaximumHeight(150)
            
            # Show coding editor
            self.coding_container.show()
            
            # Clear output area
            self.code_output.clear()
            
            # Restore saved code and language if exists
            if self.user_answers[index] is not None:
                code, language = self.user_answers[index]
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
        # Add the new methods here, at the same level as other methods
    def update_timer(self):
        """Update the timer display and check if time is up"""
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            
            # Update display in hours:minutes:seconds format
            hours = self.remaining_seconds // 3600
            minutes = (self.remaining_seconds % 3600) // 60
            seconds = self.remaining_seconds % 60
            self.time_container.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
            # Change color when time is low (less than 5 minutes)
            if self.remaining_seconds <= 300:
                self.time_container.setStyleSheet("""
                    background-color: white;
                    color: #FF3333;
                    font-size: 24px;
                    font-weight: bold;
                    border: 3px solid #FF3333;
                    border-radius: 75px;
                """)
        else:
            # Time is up, stop the timer
            self.timer.stop()
            
            # Show time's up message
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
            # This gives the user a chance to see the message
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
        
        previous_answer = self.user_answers[self.current_question_index]
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
        
        # Update the answer in memory
        self.user_answers[self.current_question_index] = new_answer
        
        # Only save to API if the answer has changed and is not None
        if new_answer is not None and new_answer != previous_answer:
            self.save_answer_to_api(question_id, question_type, new_answer)

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
        """Execute the code and display output"""
        code = self.code_editor.toPlainText()
        language = self.language_selector.currentText()
        
        if not code.strip():
            self.code_output.setPlainText("Error: No code to run.")
            return
        
        # For demonstration purposes, we'll implement basic Python execution
        # In a real application, you would need proper sandboxing and language support
        try:
            if language.lower() == "python":
                # Create a StringIO object to capture print outputs
                import io
                import sys
                from contextlib import redirect_stdout
                
                output_buffer = io.StringIO()
                with redirect_stdout(output_buffer):
                    # Execute the code
                    exec(code)
                
                output = output_buffer.getvalue()
                if output:
                    self.code_output.setPlainText(output)
                else:
                    self.code_output.setPlainText("Code executed successfully (no output).")
                    
            else:
                self.code_output.setPlainText(f"Running {language} code is not implemented in this demo.\n\nSample output would appear here.")
                
        except Exception as e:
            error_message = f"Error: {str(e)}"
            self.code_output.setPlainText(error_message)



    def go_previous(self):
        self.store_user_answer()
        if self.current_question_index > 0:
            self.current_question_index -= 1
            self.load_question(self.current_question_index)

    def go_next(self):
        self.store_user_answer()
        if self.current_question_index < len(self.questions) - 1:
            self.current_question_index += 1
            self.load_question(self.current_question_index)

    def jump_to_question(self, index):
        # Save answer before navigating
        self.store_user_answer()
        self.load_question(index)
        
        # Force resize of content based on question type
        question_type = self.questions[index].get("question_type", "2")
        if question_type == "1":  # Descriptive
            self.description_editor.setMinimumWidth(self.left_container.width() - 40)
        elif question_type == "4":  # Coding
            self.code_editor.setMinimumWidth(self.left_container.width() - 40)
    
        # Process events to ensure UI updates
        QCoreApplication.processEvents()
    
    # Process events to ensure UI updates
    QCoreApplication.processEvents()

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
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.exam_code = None
        self.token = None
        self.exam_details = None

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

        logging.info("MainWindow initialized; showing in full screen.")
        self.showFullScreen()

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
        super().keyPressEvent(event)

# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    logging.info("Entering application event loop.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()