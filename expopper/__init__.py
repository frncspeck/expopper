import serial #pip install PySerial
import pandas as pd
import matplotlib.pyplot as plt

serialPort = serial.Serial(
    port="/dev/cu.usbmodem301", #"/dev/cu.usbmodem14101",
    baudrate=115200,
    bytesize=8,
    timeout=2,
    stopbits=serial.STOPBITS_ONE,
)
times = []
hotjunctions = []
coldjunctions = []
while True:
    if serialPort.in_waiting:
        line = serialPort.readline()
        if b'Time' in line:
            times.append(int(line.strip().split()[1]))
        elif b'Hot' in line:
            hotjunctions.append(float(line.strip().split()[-1]))
        elif b'Cold' in line:
            coldjunctions.append(float(line.strip().split()[-1]))
        elif b'ADC' in line: continue
        else:
            if not times:
                continue
            else:
                break
serialPort.close()

#Process data
data = pd.DataFrame({
    "time": times, "cold": coldjunctions, "hot": hotjunctions
})
fig, ax = plt.subplots(figsize=(8, 4))
ax.scatter(data.time, data.hot, label='Hot junction')
ax.scatter(data.time, data.cold, label='Cold junction')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Temperature (°C)')
ax.legend()
