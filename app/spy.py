from gpiozero import MotionSensor
from gcloud import storage
import logging
import configparser
from datetime import datetime
from subprocess import call
import picamera
import time
import os
import numpy as np
config = configparser.ConfigParser()
config.read('/home/pi/snowballspy/config/config.ini')

def video_to_gcs(filename_):
    client = storage.Client(config['storage']['project_name'])
    bucket = client.bucket(config['storage']['bucket_name'])
    blob = bucket.blob("videos/" + filename_)
    blob.upload_from_filename("/home/pi/videos/" + filename_)
    logging.info("wrote file {0} to GCS".format(filename_))
    os.remove("/home/pi/videos/" + filename_)
    logging.info("removed file {0} from local system".format(filename_))

def take_photo():
    with picamera.PiCamera() as camera:
        camera.resolution = (320, 240)
        camera.framerate = 24
        time.sleep(2)
        output = np.empty((240, 320, 3), dtype=np.uint8)
        camera.capture(output, 'rgb')
        return output

if not os.path.exists('/home/pi/snowball_log'):
    os.makedirs('/home/pi/snowball_log')

if not os.path.exists('/home/pi/videos'):
    os.makedirs('/home/pi/videos')


logfile = "/home/pi/snowball_log/trailcam_log-"+str(datetime.now().strftime("%Y%m%d-%H%M"))+".csv"
logging.basicConfig(filename=logfile, level=logging.DEBUG,
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%d, %H:%M:%S,')

duration = int(config['spyparams']['duration'])
threshold = int(config['spyparams']['threshold'])

print('Starting')
logging.info('Starting')

# Wait an initial duration to allow PIR to settle
print('Waiting for sensor to settle')
time.sleep(10)
print('Ready')
previous_image = take_photo()
while True:
    current_image = take_photo()
    if np.sum(np.abs(current_image - previous_image)) > threshold:
            logging.info('Motion detected')
            print('Motion detected')
            time_end = time.time() + duration
            ts = '{:%Y%m%d-%H%M%S}'.format(datetime.now())
            print(time_end)
            with picamera.PiCamera() as cam:
                cam.resolution=(1024,768)
                cam.annotate_background = picamera.Color('black')
                cam.start_recording('/home/pi/video.h264')
                while time.time() < time_end:
                    print(time.time())
                    cam.annotate_text = datetime.now().strftime('%d-%m-%y %H:%M:%S')
                    cam.wait_recording(0.2)
                cam.stop_recording()
            timestamp = datetime.now().strftime('%d-%m-%y_%H-%M-%S')
            input_video = "/home/pi/video.h264"
            logging.info('Attempting to save video')
            print('Attempting to save video')

            logging.info('Saving to /home/pi/videos/')
            print('Saving to /home/pi/videos/')
            output_video = "/home/pi/videos/{}.mp4".format(timestamp)
            call(["MP4Box", "-add", input_video, output_video])
            video_to_gcs("{}.mp4".format(timestamp))

            print('Motion ended - sleeping for 10 secs')
            logging.info('Motion Ended')
            time.sleep(120)
    previous_image = current_image
    time.sleep(10)
