import serial #pip install PySerial
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline
import os
import time

def roast_profile(port="/dev/cu.usbmodem14101", animated=True, cycle=30):  #"/dev/cu.usbmodem301"
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

    if cycle:
        serialPort.write(b'r')
        # TODO send cycle profile
        
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
                        break
            else:
                time.sleep(1)
                serialPort.write(b's')
                
    except KeyboardInterrupt:
        serialPort.close()

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
    return data

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
    spl = UnivariateSpline(x, y, k=4, s=0)
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

