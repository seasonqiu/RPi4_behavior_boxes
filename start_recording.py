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
#    output.close()
    print('Closing Output File')
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

base_path = '~/test'
camId = str(0)
video_file_name = base_path + "_cam" + camId + "_output_" + \
                  str(dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")) + ".h264"
time_stamp_file_name = base_path + "_cam" + camId + "_timestamp_" + \
                       str(dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")) + ".txt"

camera = Picamera2()
video_config = camera.create_video_configuration()
camera.configure(video_config)
encoder = H264Encoder(bitrate=10000000)

camera.start_preview(Preview.QT)
camera.start_recording(encoder, video_file_name, pts=time_stamp_file_name)
time.sleep(10)
camera.stop_recording()
camera.stop_preview()
