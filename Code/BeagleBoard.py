import socket
import threading
import queue
import cv2
import pyaudio
import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.ADC as ADC
import time

# Motor Configuration
LEFT_MOTOR_IN1 = "P8_10"
LEFT_MOTOR_IN2 = "P8_12"
RIGHT_MOTOR_IN3 = "P8_14"
RIGHT_MOTOR_IN4 = "P8_16"

GPIO.setup(LEFT_MOTOR_IN1, GPIO.OUT)
GPIO.setup(LEFT_MOTOR_IN2, GPIO.OUT)
GPIO.setup(RIGHT_MOTOR_IN3, GPIO.OUT)
GPIO.setup(RIGHT_MOTOR_IN4, GPIO.OUT)

def motor_control(cmd):
    if cmd == 'forward':
        GPIO.output(LEFT_MOTOR_IN1, GPIO.HIGH)
        GPIO.output(LEFT_MOTOR_IN2, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_IN3, GPIO.HIGH)
        GPIO.output(RIGHT_MOTOR_IN4, GPIO.LOW)
    elif cmd == 'backward':
        GPIO.output(LEFT_MOTOR_IN1, GPIO.LOW)
        GPIO.output(LEFT_MOTOR_IN2, GPIO.HIGH)
        GPIO.output(RIGHT_MOTOR_IN3, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_IN4, GPIO.HIGH)
    elif cmd == 'left':
        GPIO.output(LEFT_MOTOR_IN1, GPIO.LOW)
        GPIO.output(LEFT_MOTOR_IN2, GPIO.HIGH)
        GPIO.output(RIGHT_MOTOR_IN3, GPIO.HIGH)
        GPIO.output(RIGHT_MOTOR_IN4, GPIO.LOW)
    elif cmd == 'right':
        GPIO.output(LEFT_MOTOR_IN1, GPIO.HIGH)
        GPIO.output(LEFT_MOTOR_IN2, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_IN3, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_IN4, GPIO.HIGH)
    elif cmd == 'stop':
        GPIO.output(LEFT_MOTOR_IN1, GPIO.LOW)
        GPIO.output(LEFT_MOTOR_IN2, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_IN3, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_IN4, GPIO.LOW)

# Air Quality Sensor Setup
ADC.setup()
AIR_QUALITY_PIN = "AIN0"

# Network Configuration
DATA_QUEUE = queue.Queue()
LAPTOP_IP = "192.168.1.100"  # Update this
DATA_PORT = 5000

# Initialize Data Socket
data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
data_socket.connect((LAPTOP_IP, DATA_PORT))

def data_sender():
    while True:
        data_type, payload = DATA_QUEUE.get()
        header = data_type.ljust(5).encode()
        size = len(payload).to_bytes(4, 'big')
        data_socket.sendall(header + size + payload)

sender_thread = threading.Thread(target=data_sender, daemon=True)
sender_thread.start()

# Video Capture
def video_stream():
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if ret:
            _, jpeg = cv2.imencode('.jpg', frame)
            DATA_QUEUE.put(('VIDEO', jpeg.tobytes()))
        time.sleep(0.05)

video_thread = threading.Thread(target=video_stream, daemon=True)
video_thread.start()

# Audio Capture
audio = pyaudio.PyAudio()
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

def audio_stream():
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                       rate=RATE, input=True, frames_per_buffer=CHUNK)
    while True:
        DATA_QUEUE.put(('AUDIO', stream.read(CHUNK)))
    stream.stop_stream()
    stream.close()

audio_thread = threading.Thread(target=audio_stream, daemon=True)
audio_thread.start()

# Sensor Data
def sensor_data():
    while True:
        value = ADC.read(AIR_QUALITY_PIN)
        DATA_QUEUE.put(('SENSOR', str(value).encode()))
        time.sleep(1)

sensor_thread = threading.Thread(target=sensor_data, daemon=True)
sensor_thread.start()
def command_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 5001))
    server.listen(1)
    while True:
        conn, _ = server.accept()
        while True:
            cmd = conn.recv(1024).decode().strip()
            if cmd:
                motor_control(cmd)
        conn.close()

cmd_thread = threading.Thread(target=command_server, daemon=True)
cmd_thread.start()

while True:
    time.sleep(1)