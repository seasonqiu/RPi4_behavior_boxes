from picamera2.encoders import H264Encoder
from picamera2 import Picamera2, Preview
import time
import datetime as dt
import sys
import os
import signal

def signal_handler(signum, frame):
    print("SIGINT detected")
    camera.stop_recording()
    camera.stop_preview()
    print('Recording Stopped')
    output.close()
    print('Closing Output File')
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

base_path = '~/test'
camId = str(0)
# VIDEO_FILE_NAME = base_path + "_cam" + camId + "_output_" + str(dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")) + ".h264"

camera = Picamera2()
video_config = camera.create_video_configuration()
camera.configure(video_config)
encoder = H264Encoder(bitrate=10000000)
output = "~/test.h264"
camera.start_preview(Preview.DRM)
camera.start()
time.sleep(2)
camera.start_recording(encoder, output)
signal.signal(signal.SIGINT, signal_handler)
signal.pause()
# time.sleep(10)
# picam2.stop_recording()