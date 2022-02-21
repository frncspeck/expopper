import serial #pip install PySerial
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline
import os
import time

def roast_profile(port=1, animated=True, cycle_up=30, cycle_down=15, record_cracks=True, file_prefix=None):
    from serial.tools.list_ports import comports
    comoptions = comports()
    port = comoptions[port].device
    
    if animated:
        plt.ion()
        ax = make_animated_plot([], [])
        tax = ax.twinx()
        plt.draw()
        
    serialPort = serial.Serial(
        port=port,
        baudrate=115200,
        bytesize=8,
        timeout=2,
        stopbits=serial.STOPBITS_ONE,
    )

    # Sleep 5
    time.sleep(5)

    # Init recording
    if record_cracks:
        import sounddevice as sd
        import numpy as np
        fs = 44100  # Sample rate
        minute = 60
        seconds = 10 * minute
        recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
    else:
        recording = None
    
    serialPort.write(b'g')
    if cycle_up:
        serialPort.write(b'r' + chr(cycle_up).encode() + chr(cycle_down).encode())
        
    times = []
    hotjunctions = []
    coldjunctions = []
    cracks = []

    # Request first data point
    serialPort.write(b's')
    try:
        while True:
            if serialPort.in_waiting:
                line = serialPort.readline()
                #print(line)
                if b'Time' in line:
                    times.append(int(line.strip().split()[1]))
                elif b'Hot' in line:
                    hotjunctions.append(float(line.strip().split()[-1]))
                elif b'Cold' in line:
                    coldjunctions.append(float(line.strip().split()[-1]))
                elif b'Crack' in line:
                    cracks.append(int(line.strip().split()[1]))
                    if animated:
                        # When crack is appended we should have everything for one sample point
                        make_animated_plot(times, hotjunctions, ax, tax)
                elif b'ADC' in line: continue
                else:
                    if not times:
                        continue
                    else:
                        serialPort.write(b'a')
                        break
            else:
                time.sleep(1)
                serialPort.write(b's')
                
    except KeyboardInterrupt:
        serialPort.write(b'a')
        serialPort.close()
        if record_cracks:
            sd.stop()
            # Delete non recorded part of array
            recording = recording[:-np.argmax((recording != 0)[::-1])]
            #ax.plot(range(len(recording)), np.abs(recording) > 0.05)
            
    #Process data
    if len(cracks) > len(times):
        cracks = cracks[:len(times)]
    data = pd.DataFrame({
        "time": times[:len(cracks)],
        "cold": coldjunctions[:len(cracks)],
        "hot": hotjunctions[:len(cracks)],
        "cracks": cracks
    })
    data.cracks = (data.cracks.shift(-1) != data.cracks).shift().fillna(False)
    make_single_plot(data)

    if file_prefix:
        data.to_csv(file_prefix+'.csv')
        if recording:
            from scipy.io import wavfile
            wavfile.write(file_prefix+'.wav', fs, recording)
    
    return data, recording

# Figure
def make_single_plot(data, ax=None, label='Hot junction', cracks='r', cold_too=True):
    if not ax:
        fig, ax = plt.subplots(figsize=(8, 4))
    ax.scatter(data.time, data.hot, label=label)
    if cold_too:
        ax.scatter(data.time, data.cold, label='Cold junction')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Temperature (°C)')
    if cracks:
        ax.vlines(data.time[data.cracks],ymin=0,ymax=250,color=cracks)
    ax.legend()
    calculate_derivative(data.time, data.hot, ax)
    return ax

def calculate_derivative(x, y, ax=None): # hot ~ RoR
    try: spl = UnivariateSpline(x, y, k=4, s=0)
    except ValueError:
        # with s=0 ValueError in certain conditions
        spl = UnivariateSpline(x, y, k=4, s=None)
    spl.derivative()
    der = spl.derivative()

    if ax:
        tax = ax.twinx()
        tax.scatter(x, der(x), label='RoR')

    return der

def make_animated_plot(x,y,ax=None, tax=None):
    if not ax:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(x,y, c='b')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Temperature (°C)')
        return ax
    else:
        ax.lines.clear()
        ax.plot(x, y, c='b')
        if tax and len(x) > 10:
            der = calculate_derivative(x, y)
            tax.lines.clear()
            tax.plot(x, der(x), c='r')
        ax.relim()
        ax.autoscale_view()
        plt.draw()
        plt.pause(0.05);
    
def compare_profiles(*filenames, reset_times=None):
    if reset_times and isinstance(reset_times, list):
        reset_times = dict(zip([os.path.basename(f) for f in filenames], reset_times))
    data = {os.path.basename(f):pd.read_csv(f) for f in filenames}

    # Figure
    fig, ax = plt.subplots(figsize=(8, 4))
    for d in data:
        ax.scatter(data[d].time - (reset_times[d] if reset_times else 0), data[d].hot, label=d)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Temperature (°C)')
    ax.legend()
    return data
