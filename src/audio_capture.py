# audio_capture.py
import pyaudiowpatch as pyaudio
import wave
import os
import configparser
#Obtain the absolute path of the current file, go up one level, find the config.ini with the absolute path, and read it
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
config_path = os.path.join(project_root, 'config.ini')
MYCONFIG = configparser.ConfigParser()
MYCONFIG.read(config_path,encoding='utf-8')

class LoopbackRecorder:
    def __init__(self, device_index=MYCONFIG['DEFAULT'].getint('SPEAKER_DEVICE_INDEX')):
        # 初始化
        self.p = None
        self.stream = None
        self.wave_file = None
        
        self.is_recording = False
        self.device_index = None if device_index < 0 else device_index
        self.device_info = self._get_device()
        
    def _cleanup(self):
        """Strictly follow the example of the order in which resources are released"""
        print("Resources are being cleaned up...")
        if self.is_recording:
            self.is_recording = False
        if self.stream:
            self.stream.close()
        if self.wave_file:
            self.wave_file.close()
        if self.p:
            self.p.terminate()

    def _get_device(self):
        """Strictly follow the official example of how the device is acquired"""
        self.p = pyaudio.PyAudio()
        try:
            if self.device_index is None:
                self.device_info = self.p.get_default_wasapi_loopback()
            else:
                self.device_info = self.p.get_device_info_by_index(self.device_index)
                
            # 验证设备是否支持loopback
            if self.device_info["maxInputChannels"] < 1:
                raise ValueError("The device does not support loopback input")
                
            return self.device_info
        except (OSError, LookupError) as e:
            raise RuntimeError(f"Device initialization failed: {str(e)}")

    def start_recording(self, filename="output.wav"):
        """Exactly as the stream initialization method of the official example"""
        try:
            self._get_device()
            
            # 参数直接从设备信息获取
            self.rate = int(self.device_info["defaultSampleRate"])
            self.channels = self.device_info["maxInputChannels"]
            self.format = pyaudio.paInt16
            self.sample_size = self.p.get_sample_size(self.format)

            # 初始化WAV文件
            self.wave_file = wave.open(filename, 'wb')
            self.wave_file.setnchannels(self.channels)
            self.wave_file.setsampwidth(self.sample_size)
            self.wave_file.setframerate(self.rate)

            # 创建音频流（与示例完全一致）
            self.stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.device_info["index"],
                frames_per_buffer=1024
            )

            self.is_recording = True
            print(f"Successfully start recording: {self.device_info['name']}")

        except Exception as e:
            self._cleanup()
            raise RuntimeError("self._cleanup()Error")

    def record(self, duration=None):
        if not self.is_recording:
            raise RuntimeError("Must be called first start_recording()")
        try:
            if duration:  # 定时录音模式
                print(f"Recording {duration} 秒...")
                for _ in range(0, int(self.rate / 1024 * duration)):
                    if not self.is_recording:  # 检查是否收到停止信号
                        break
                    data = self.stream.read(1024)
                    self.wave_file.writeframes(data)
            else:  # 持续录音模式
                print("Recordings are ongoing...")
                while self.is_recording:
                    data = self.stream.read(1024)
                    self.wave_file.writeframes(data)
                self.stop_recording()
        finally:
            self._cleanup()
            print("Recording has stopped")

    def stop_recording(self):
        """Strictly follow the example of the order in which resources are released"""
        if self.is_recording:
            self.is_recording = False
        if self.stream:
            self.stream.close()
        if self.wave_file:
            self.wave_file.close()
        if self.p:
            self.p.terminate()
        print("Recording has been safely stopped")

    @staticmethod
    def list_devices():
        """Device list query (directly using the official recommended method)"""
        with pyaudio.PyAudio() as p:
                # 打印默认输入设备信息
            print("\n=== Default input device ===")
            try:
                default = p.get_default_input_device_info()
                print(f"* Default device: [{default['index']}] {default['name']}")
            except Exception as e:
                print("!The default input device was not found ")

            # 打印默认输出设备信息
            print("\n=== Default output device ===")
            try:
                default = p.get_default_output_device_info()
                print(f"* Default device: [{default['index']}] {default['name']}")
            except Exception as e:
                print("!The default output device was not found ")

            print("\n=== The default loopback device ===")
            try:
                default = p.get_default_wasapi_loopback()
                print(f"*Default device : [{default['index']}] {default['name']}")
            except Exception as e:
                print("! The default loopback device was not found")

            print("\nAll devices that contain an InputChannel:")
            for i in range(p.get_device_count()):
                dev = p.get_device_info_by_index(i)
                if dev["maxInputChannels"] > 0:
                    print(f"[{dev['index']}] {dev['name']} (Input channel: {dev['maxInputChannels']})")

            print("\nAll devices that contain an OutputChannel:")
            for i in range(p.get_device_count()):
                dev = p.get_device_info_by_index(i)
                if dev["maxOutputChannels"] > 0:
                    print(f"[{dev['index']}] {dev['name']} (Output channel: {dev['maxOutputChannels']})")
            
            print("\nAll devices that contain a loopback:")
            for i in range(p.get_device_count()):
                dev = p.get_device_info_by_index(i)
                if dev["isLoopbackDevice"] > 0:
                    print(f"[{dev['index']}] {dev['name']} (Loopback: {dev['maxInputChannels']})")
if __name__ == "__main__":
    # 列出设备
    LoopbackRecorder.list_devices()
    
    try:
        recorder = LoopbackRecorder()  # 明确指定设备索引
        recorder.start_recording("output/test_record.wav")
        recorder.record(duration=5)  # 录制5秒
        recorder.stop_recording()
    except Exception as e:
        print(f"Recording failed: {str(e)}")
