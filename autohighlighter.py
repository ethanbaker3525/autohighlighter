import os
from subprocess import call
import matplotlib.pyplot as plt
import numpy as np
from scipy.io import wavfile
from math import ceil
from pathlib import Path

'''
to do

fix case (snake case)
do xml formatting with simple string manip
fix xml formatting (maybe switch to something simpler)
make sure everything works for files in different folders, etc

'''

FCPXML_TEMPLATE = '''
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.9">
    <resources>
        <asset hasVideo="1" name="{file_name}" hasAudio="1" id="r1" start="0s" duration="999999s" audioChannels="2" format="r0">
            <media-rep src="file://localhost/{file_path}" kind="original-media"/>
        </asset>
    </resources>
    <library>
        <event name="Timeline">
            <project name="Timeline">
                <sequence tcFormat="NDF" format="r0">
                    <spine>
{asset_clips}
                    </spine>
                </sequence>
            </project>
        </event>
    </library>
</fcpxml>
'''
ASSET_CLIP_TEMPLATE = '''
                        <asset-clip name="{file_name}" ref="r1" offset="{offset}" start="{start}" duration="{duration}" enabled="1" tcFormat="NDF" format="r0">
                        </asset-clip>
'''

MARKERS = {
    'Hotkey 1 was pressed':1,
    'Hotkey 2 was pressed':2,
    'Hotkey 3 was pressed':3,
    'Hotkey 4 was pressed':4,
    'Hotkey 5 was pressed':5
        }

def to_frames(str_hhmmss, fps=60):

    time_list = str_hhmmss.split(':')

    h = int(time_list[0])
    m = int(time_list[1])
    s = int(time_list[2])

    return (h*3600+m*60+s)*fps

def make_fcpxml(video_path, output_path, clip_list, fps=60, path=''):

    video_name = Path(video_path)
    output_name = Path(output_path)

    if not video_name().exists():
        print("File does not extist")

    else:

        clips = ''
        video_duration = 0

        for clip in clip_list:
            clips += ASSET_CLIP_TEMPLATE.format(file_name=video_name.name, offset=str(video_duration), start=str(clip['start_frame']), duration=str(clip['total_frames']))
            video_duration += str(clip['total_frames'])

        with output_name.open() as file:
            file.write(FCPXML_TEMPLATE.format(
                file_name=video_name.name, 
                file_path=video_name.as_posix().replace(' ','%')),
                asset_clips=clips
                ) # formatting the template with specific paramaters

def get_markers(source_path, logs_path, fps=60):

    # modify this code later to work with other paths instead of the cwd
    sourceName = source_path.split('\\')[-1]
    print(sourceName)

    # reads the log file and saves the relevant logs in a list
    with open(logs_path, 'r') as all_logs:
        p_vod_dir = sourceName.split(' ')
        start_text = p_vod_dir[0] + ' ' + p_vod_dir[1].replace('-',':')[0:-4]
        print(start_text)
        o_logs = all_logs.read().split('EVENT:START RECORDING @ ' + start_text)[1].split('EVENT:STOP RECORDING')[0].split('\n\n')[1:-1]

    # creates a dict of values corresponding to MARKERS and their corresponding times in the format H:MM:SS
    logs = []
    for log in o_logs:
        if 'HOTKEY' in log:
            marker = log.split(' @ ')[0].split('HOTKEY:')[1]
            try:
                logs.append({
                    'marker':MARKERS[marker],
                    'frame':to_frames(log.split('\n')[1].split(' Record Time Marker')[0], fps=fps)
                    })
            except:
                print('NO MARKER EQUALING '+marker)
        # more can be added here for scene changes or other things
    return logs

def getMaxVolume(s):
    maxv = float(np.max(s))
    minv = float(np.min(s))
    return max(maxv,-minv)

def getWav(source_file, fps=60):

    # maybe edit to use a temp folder
    call('ffmpeg -i "{}" temp.wav'.format(source_file.replace(' ',' ')), shell=True)
    samplerate, data = wavfile.read('temp.wav')
    os.remove('temp.wav')
    return samplerate, data

if __name__ == '__main__':

    # TO MAKE SURE EVERYTHING WORKS,
    # INSTEAD OF DOING THE AUDIOTHRESHOLD STUFF, JUST DO A FEW SECONDS BEFORE OR AFTER OR BOTH

    RECORDING = 'X:\\vods\\2021-12-23 22-40-10.mp4'
    LOGS = 'C:\\Users\\ethan\\Documents\\infowriter\\logs.txt'
    fps = 60
    audioThreshold = 0.1 # 0<x<1
    #file = input('FILE: ')
    markers = get_markers(sourcePath=RECORDING, logs_path=LOGS)
    audioSamplerate, audioData = getWav(RECORDING)
    maxVolume = getMaxVolume(audioData)
    samplesPerFrame =  int(audioSamplerate/fps)
    totalFrameCount = ceil(len(audioData)/samplesPerFrame)

    assert audioSamplerate/fps == samplesPerFrame

    print(markers)

    frameVolumes = []
    for i in range(totalFrameCount):
        frameRange = audioData[i*samplesPerFrame:(i+1)*samplesPerFrame-1]
        frameVolumes.append(getMaxVolume(frameRange))

    clips = []
    for m in markers:
        if m['marker'] != None: #this can be changed so that different hotkeys can control how the script edits the video
            # finding lower bound
            lowerFrameBound = m['frame']-60 # lower bound starts 1 secound before the hotkey was pressed
            while frameVolumes[lowerFrameBound]/maxVolume >= audioThreshold:
                lowerFrameBound -= 1

            # finding upper bound
            upperFrameBound = m['frame'] # upper bound starts as the hotkey was pressed
            while frameVolumes[upperFrameBound]/maxVolume >= audioThreshold:
                upperFrameBound += 1

            clips.append({'total_frames':upperFrameBound-lowerFrameBound,'start_frame':lowerFrameBound})

    make_fcpxml(RECORDING, RECORDING.replace('.mp4', '.fcpxml'), clips)
