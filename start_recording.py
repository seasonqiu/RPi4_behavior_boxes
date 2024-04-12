from picamera2.encoders import H264Encoder
from picamera2 import Picamera2
import time
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

picam2 = Picamera2()
video_config = picam2.create_video_configuration()
picam2.configure(video_config)
encoder = H264Encoder(bitrate=10000000)
output = "test.h264"
picam2.start_recording(encoder, output)
# time.sleep(10)
# picam2.stop_recording()