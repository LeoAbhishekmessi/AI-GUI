import os
import sys
import time
import datetime
import psutil
import sounddevice as sd
import numpy as np
import ctypes
import ctypes.wintypes
import logging
import subprocess
import threading
import keyboard  # third-party module for global key events
import requests  # For API calls

# PyQt6 Imports
from PyQt6.QtCore import QEvent, Qt, QTimer, QPropertyAnimation, QRect
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QRadioButton, QButtonGroup, QGroupBox, QGridLayout
)
from PyQt6.QtGui import QFont, QPixmap, QKeyEvent
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtMultimedia import QCamera, QMediaDevices, QMediaCaptureSession

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
logging.basicConfig(filename="keyblock.log", level=logging.INFO, format="%(asctime)s - %(message)s")
logging.info("Application starting...")

# -----------------------------------------------------------------------------
# Key Blocking
# -----------------------------------------------------------------------------
def block_keys():
    # Block F1-F12 keys
    for key in ['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12']:
        keyboard.block_key(key)
        logging.info(f"Blocking {key}")
    # Block Windows keys
    keyboard.block_key('left windows')
    keyboard.block_key('right windows')
    logging.info("Blocking Windows keys")
    # Block the 'esc' key
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

            # Remove "Bearer " prefix if it exists
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

def send_authenticated_request(api_url, data=None):
    global SESSION_TOKEN
    if not SESSION_TOKEN:
        print("\n❌ Error: No token found. Please log in first.")
        return None
    headers = {
        "Authorization": f"Bearer {SESSION_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        logging.info(f"🔗 Sending Authenticated Request to {api_url}")
        response = requests.post(api_url, headers=headers, json=data) if data else requests.get(api_url, headers=headers)
        logging.debug(f"📡 Response Status Code: {response.status_code}")
        logging.debug(f"📜 Response Content: {response.text}")
        return response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        logging.error(f"⚠️ API Request Error: {e}")
        return None

def get_exam_details(token, exam_code=None):
    url = "https://stageevaluate.sentientgeeks.us/wp-json/api/v1/get-exam-details"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {"exam_link": exam_code} if exam_code else {}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        logging.debug(f"Response Status Code: {response.status_code}")
        logging.debug(f"Response Content: {response.text}")
        
        try:
            response_json = response.json()
        except Exception as parse_err:
            logging.error(f"Error parsing JSON: {parse_err}")
            print("❌ Error parsing JSON response:", response.text)
            return None
        
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

# -----------------------------------------------------------------------------
# System Check Functions
# -----------------------------------------------------------------------------
def check_audio():
    duration = 0.5  # seconds to record
    fs = 44100      # sample rate
    try:
        default_output = sd.default.device[1]  # Might need adjustment on some machines
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
    known_keywords = {"zoom", "teams", "skype", "teamviewer"}
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

        # Left side: exam code form
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
            QPushButton {
                background-color: #00205b;
                color: white;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #001b4f;
            }
        """)
        submit_button.clicked.connect(self.handle_exam_code)
        form_layout.addWidget(submit_button, alignment=Qt.AlignmentFlag.AlignCenter)
        form_layout.addStretch()

        main_layout.addLayout(form_layout)

        # Right side: logo or placeholder
        logo_layout = QVBoxLayout()
        logo_label = QLabel(self)
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        logo_width = int(screen_size.width() * 0.9)
        logo_height = int(screen_size.height() * 0.9)
        pixmap = QPixmap("772.png")  # Replace with your logo path
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
                    # Pass exam_code, token, and exam_details to the next page
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
        self.exam_details = None  # To store exam_details
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

        self.setLayout(layout)

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
            if (self.video_label.text().endswith("OK") and
                self.audio_label.text().endswith("OK") and
                self.machine_label.text().endswith("OK") and
                self.screen_label.text().endswith("OK") and
                self.funkey_label.text().endswith("OK") and
                self.monitor_label.text().endswith("OK")):
                self.status_message.setText("All checks passed!")
                self.continue_button.setEnabled(True)
            else:
                self.status_message.setText("One or more checks failed. Please contact admin.")
        else:
            self.video_label.setText("Video Check: Checking...")
            self.audio_label.setText("Audio Check: Checking...")
            self.machine_label.setText("Machine Requirement: Checking...")
            self.screen_label.setText("Screen Sharing App: Checking...")
            self.funkey_label.setText("Function Key Block: Checking...")
            self.monitor_label.setText("Monitor Check: Checking...")

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

        self.setLayout(layout)

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

        self.setLayout(layout)

    def start_camera_preview(self):
        available_cameras = QMediaDevices.videoInputs()
        if available_cameras:
            self.camera = QCamera(available_cameras[0])
            self.capture_session = QMediaCaptureSession()
            self.capture_session.setCamera(self.camera)
            self.capture_session.setVideoOutput(self.video_widget)
            self.camera.start()
            logging.info("Camera preview started.")
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
        self.exam_details = None  # To store exam_details
        self.remaining_time = 0   # Will be set from exam_details
        self.setup_ui()

    def set_exam_details(self, exam_details):
        self.exam_details = exam_details
        print("\n✅ Exam Details in ExamInstructionsPage:", self.exam_details)
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

        # Message and countdown labels in lieu of a Start Exam button
        self.message_label = QLabel("")
        self.message_label.setFont(QFont("Arial", 18))
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)

        self.countdown_label = QLabel("")
        self.countdown_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.countdown_label)

        self.setLayout(layout)

    def start_countdown(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.update_countdown()  # immediate update
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
            self.switch_to_exam_callback()

# 6. Exam Page
class ExamPage(QWidget):
    def __init__(self, questions, parent=None):
        super().__init__(parent)
        self.questions = questions
        self.current_question_index = 0
        self.user_answers = [None] * len(questions)
        self.exam_code = ""
        self.exam_details = None  # To store exam_details
        self.setup_ui()
        self.load_question(self.current_question_index)

    def set_exam_code(self, code):
        self.exam_code = code
        print("\n✅ Exam Code in ExamPage:", self.exam_code)

    def set_exam_details(self, exam_details):
        self.exam_details = exam_details
        print("\n✅ Exam Details in ExamPage:", self.exam_details)

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Left: Question Area
        self.left_container = QWidget()
        self.left_container.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 6px;
        """)
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)

        self.question_header = QLabel("Question 1 [Marks: 2]")
        self.question_header.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        left_layout.addWidget(self.question_header)

        self.question_label = QLabel("Which one is the right function to get folder path of child theme?")
        self.question_label.setFont(QFont("Arial", 16))
        self.question_label.setWordWrap(True)
        left_layout.addWidget(self.question_label)

        self.options_group_box = QGroupBox("Options")
        self.options_group_box.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.options_layout = QVBoxLayout()
        self.options_group_box.setLayout(self.options_layout)
        left_layout.addWidget(self.options_group_box)

        # Right: Sidebar
        self.right_container = QWidget()
        self.right_container.setStyleSheet("""
            background-color: #F2F8FF;
            border: 1px solid #ccc;
            border-radius: 6px;
        """)
        right_layout = QVBoxLayout(self.right_container)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)

        self.time_container = QLabel("00:29:58")
        self.time_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_container.setFixedSize(150, 150)
        self.time_container.setStyleSheet("""
            background-color: #FFFFFF;
            color: #00205b;
            font-size: 18px;
            font-weight: bold;
            border-radius: 75px;
            border: 2px solid #00205b;
        """)
        time_label_title = QLabel("Remaining Time")
        time_label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_label_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        time_label_title.setStyleSheet("color: #00205b;")

        time_layout = QVBoxLayout()
        time_layout.addWidget(time_label_title, alignment=Qt.AlignmentFlag.AlignCenter)
        time_layout.addWidget(self.time_container, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addLayout(time_layout)

        question_panel_title = QLabel("Question Panel")
        question_panel_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        question_panel_title.setStyleSheet("color: #00205b;")
        question_panel_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(question_panel_title)

        legend_label = QLabel("""
            <p><span style="color:black;">&#9679;</span> Answer Given</p>
            <p><span style="color:black;">&#9679;</span> Not Given</p>
            <p><span style="color:black;">&#9679;</span> Current</p>
            <p><span style="color:black;">&#9679;</span> Not Visited</p>
        """)
        legend_label.setStyleSheet("font-size: 14px; color: black;")
        right_layout.addWidget(legend_label)

        self.question_panel = QGridLayout()
        self.question_panel.setSpacing(8)
        num_cols = 5
        for i in range(len(self.questions)):
            question_btn = QPushButton(str(i + 1))
            question_btn.setFixedSize(40, 40)
            question_btn.setStyleSheet("""
                QPushButton {
                    background-color: #eeeeee;
                    color: #333;
                    border: 2px solid #ddd;
                    border-radius: 20px;
                }
            """)
            question_btn.clicked.connect(lambda checked, idx=i: self.jump_to_question(idx))
            row = i // num_cols
            col = i % num_cols
            self.question_panel.addWidget(question_btn, row, col)
        right_layout.addLayout(self.question_panel)

        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("Previous")
        self.prev_button.setStyleSheet("""
            QPushButton {
                background-color: #e6e6e6;
                color: #333;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #cccccc;
            }
        """)
        self.prev_button.clicked.connect(self.go_previous)

        self.next_button = QPushButton("Next")
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #e6e6e6;
                color: #333;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #cccccc;
            }
        """)
        self.next_button.clicked.connect(self.go_next)

        self.submit_button = QPushButton("Submit")
        self.submit_button.setStyleSheet("""
            QPushButton {
                background-color: #00205b;
                color: white;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #001b4f;
            }
        """)
        self.submit_button.clicked.connect(self.submit_exam)

        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        nav_layout.addWidget(self.submit_button)
        right_layout.addLayout(nav_layout)

        right_layout.addStretch()

        main_layout.addWidget(self.left_container, stretch=3)
        main_layout.addWidget(self.right_container, stretch=1)

    def load_question(self, index):
        if 0 <= index < len(self.questions):
            q_data = self.questions[index]
            q_number = index + 1
            marks = q_data.get("marks", 1)
            self.question_header.setText(f"Question {q_number} [Marks: {marks}]")
            self.question_label.setText(q_data["question"])

            # Clear old options
            for i in reversed(range(self.options_layout.count())):
                item = self.options_layout.itemAt(i)
                widget = item.widget()
                if widget:
                    self.options_layout.removeWidget(widget)
                    widget.deleteLater()

            self.options_button_group = QButtonGroup(self)
            self.options_button_group.setExclusive(True)
            for i, option_text in enumerate(q_data["options"]):
                rb = QRadioButton(option_text)
                rb.setFont(QFont("Arial", 14))
                self.options_layout.addWidget(rb)
                self.options_button_group.addButton(rb, i)

            if self.user_answers[index] is not None:
                selected_index = self.user_answers[index]
                btns = self.options_button_group.buttons()
                if 0 <= selected_index < len(btns):
                    btns[selected_index].setChecked(True)

            self.prev_button.setEnabled(index > 0)

    def store_user_answer(self):
        selected_id = self.options_button_group.checkedId()
        if selected_id != -1:
            self.user_answers[self.current_question_index] = selected_id
        else:
            self.user_answers[self.current_question_index] = None

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
        self.store_user_answer()
        self.current_question_index = index
        self.load_question(self.current_question_index)

    def submit_exam(self):
        self.store_user_answer()
        print("User submitted exam. Answers:", self.user_answers)
        print("Exam code was:", self.exam_code)
        # Implement submission logic here.

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

        questions_data = [
            {
                "question": "Which one is the right function to get folder path of child theme?",
                "options": [
                    "plugin_dir_url(__FILE__)",
                    "get_template_directory_uri()",
                    "get_stylesheet_directory_uri()",
                    "None of the above"
                ],
                "answer_index": 2,
                "marks": 2
            },
            {
                "question": "Which function prints to console in Python?",
                "options": ["echo()", "var_dump()", "print()", "console.log()"],
                "answer_index": 2,
                "marks": 1
            }
        ]

        self.exam_code_page = ExamCodePage(self.show_system_check_page)
        self.system_check_page = SystemCheckPage(self.show_instructions_page)
        self.instructions_page = ExamInstructionsPage(self.show_exam_page)
        self.exam_page = ExamPage(questions_data)

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

    def show_exam_page(self):
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
