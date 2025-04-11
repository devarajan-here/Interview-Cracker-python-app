import pyaudio

p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    print(f"Device {i}: {p.get_device_info_by_index(i)['name']}")
p.terminate()
