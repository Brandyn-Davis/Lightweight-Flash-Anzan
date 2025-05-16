import threading
import time
import struct
import random
import sounddevice as sd
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QListWidget, QSlider, QVBoxLayout, QLayout, QStackedWidget
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QFont, QFontDatabase

class BeepPlayer:
    def __init__(self, samplerate=9680):
        self.samplerate = samplerate
        self.buffer = bytearray()
        self.lock = threading.Lock()
        self.event = threading.Event()

        self.stream = sd.RawOutputStream(
            samplerate=self.samplerate,
            channels=1,
            dtype='int16',
            callback=self.callback
        )
        self.stream.start()

    def callback(self, outdata, frames, time_info, status):
        with self.lock:
            n_bytes = frames * 2
            chunk = self.buffer[:n_bytes]
            outdata[:len(chunk)] = chunk
            if len(chunk) < n_bytes:
                outdata[len(chunk):] = b'\x00' * (n_bytes - len(chunk))
            self.buffer = self.buffer[n_bytes:]

    def play_once(self, wave_bytes):
        with self.lock:
            self.buffer += wave_bytes
        self.event.set()

    def close(self):
        self.stream.stop()
        self.stream.close()

class AnzanApp(QWidget):
    def __init__(self):
        super().__init__()
        self.settings()
        self.initVars()
        #self.warmup_stream()
        self.initUI()

        # Set layout stack
        self.stack_initUI.setLayout(self.layout_init)
        self.stack_playUI.setLayout(self.layout_play)
        self.Stack.setCurrentIndex(0)

    def settings(self):
        self.setWindowTitle("Flash Anzan")
        self.setGeometry(800, 500, 600, 300)

    def triangleWave(self, frequency=440, duration=0.05, samplerate=9680, volume=0.3):
        n = int(samplerate * duration)
        t = [i * (duration / n) for i in range(n)]
        return [volume * (2 * abs(2 * (x * frequency % 1) - 1) - 1) for x in t]

    #def waveBuffer(self):
    #    self.wave = triangle_wave(440)
    #    self.wave_bytes = b''.join(struct.pack('<h', int(s * 32767)) for s in wave)

    def play_once(self):
        pos = 0

        def callback(outdata, frames, time, status):
            nonlocal pos
            if status:
                print(status)
            length = frames * 2
            chunk = self.wave_bytes[pos:pos+length]
            outdata[:len(chunk)] = chunk
            if len(chunk) < length:
                outdata[len(chunk):] = b'\x00' * (length - len(chunk))
            pos += length

        with sd.RawOutputStream(
            samplerate=9680,
            channels=1,
            dtype='int16',
            callback=callback
        ) as stream:
            sd.sleep(int(len(self.wave) / 9680 * 1000))

    #def warmup_stream(self, samplerate=9680):
    #    def silent_callback(outdata, frames, time, status):
    #        outdata[:] = b'\x00' * (frames * 2)
    #    with sd.RawOutputStream(samplerate=samplerate, channels=1, dtype='int16', callback=silent_callback):
    #        sd.sleep(100)  # ~0.1 sec silent warm-up

    def initVars(self):
        self.randNums = list()

        #self.wave = self.triangleWave(440)
        self.wave = self.triangleWave(frequency=440, samplerate=9680)
        self.wave_bytes = b''.join(struct.pack('<h', int(s * 32767)) for s in self.wave)
        self.player = BeepPlayer()

        self.id = QFontDatabase.addApplicationFont("soroban.ttf")
        if self.id < 0: print("Error")
        families = QFontDatabase.applicationFontFamilies(self.id)
        #print(families)

        self.stack_initUI = QWidget()
        self.stack_playUI = QWidget()
        self.Stack = QStackedWidget(self)
        self.Stack.addWidget(self.stack_initUI)
        self.Stack.addWidget(self.stack_playUI)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateNumber)

        self.label_number = QLabel("")
        self.label_number.setFont(QFont(families[0], 32))
        self.label_number.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label_terms = QLabel("")
        self.label_terms.setFont(QFont("Arial", 18))
        self.label_terms.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label_time = QLabel("Seconds per number: 5.0")
        self.label_digits = QLabel("Digits per number: 1")
        self.label_count = QLabel("Numbers per round: 10")
        self.slider_time = QSlider(Qt.Orientation.Horizontal)
        self.slider_digits = QSlider(Qt.Orientation.Horizontal)
        self.slider_count = QSlider(Qt.Orientation.Horizontal)
        self.slider_time.setRange(1, 100)
        self.slider_time.setValue(50)
        self.slider_digits.setRange(1, 10)
        self.slider_digits.setValue(1)
        self.slider_count.setRange(2, 50)
        self.slider_count.setValue(10)

        self.btn_play = QPushButton("Play")

        self.layout_time = QVBoxLayout()
        self.layout_digits = QVBoxLayout()
        self.layout_count = QVBoxLayout()
        self.layout_buttons = QVBoxLayout()

        self.layout_init = QVBoxLayout()

        self.layout_time.addWidget(self.label_time)
        self.layout_time.addWidget(self.slider_time)
        self.slider_time.valueChanged.connect(self.timeChanged)
        self.layout_init.addLayout(self.layout_time)

        self.layout_digits.addWidget(self.label_digits)
        self.layout_digits.addWidget(self.slider_digits)
        self.slider_digits.valueChanged.connect(self.digitsChanged)
        self.layout_init.addLayout(self.layout_digits)

        self.layout_count.addWidget(self.label_count)
        self.layout_count.addWidget(self.slider_count)
        self.slider_count.valueChanged.connect(self.countChanged)
        self.layout_init.addLayout(self.layout_count)

        self.layout_buttons.addWidget(self.btn_play)
        self.btn_play.pressed.connect(self.playPressed)
        self.layout_init.addLayout(self.layout_buttons)

        self.layout_play = QVBoxLayout()
        self.layout_play.addWidget(self.label_terms)
        self.layout_play.addWidget(self.label_number)

        self.btn_quit = QPushButton("Quit")
        self.layout_play.addWidget(self.btn_quit)
        self.btn_quit.pressed.connect(self.quit)

        self.layout_master = QVBoxLayout(self)
        self.layout_master.addWidget(self.Stack)

    def initUI(self):
        self.time = self.slider_time.value() / 10
        self.label_time.setText(f"Seconds per number: {self.time}")

        self.digits = self.slider_digits.value()
        self.label_digits.setText(f"Digits per number: {self.digits}")

        self.count = self.slider_count.value()
        self.label_count.setText(f"Numbers per round: {self.count}")

    def playUI(self):
        self.btn_quit.setEnabled(True)
        self.startTimer()

    def getReady(self):
        self.btn_quit.setEnabled(False)
        self.label_number.setText("Get ready.")
        QTimer.singleShot(1000, self.getReady1)
    def getReady1(self):
        self.label_number.setText("Get ready..")
        QTimer.singleShot(1000, self.getReady2)
    def getReady2(self):
        self.label_number.setText("Get ready...")
        QTimer.singleShot(1000, self.playUI)

    def startTimer(self):
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.btn_play.setEnabled(False)
            self.updateNumber()
            self.timer.start(int(self.time * 1000))

    def stopTimer(self):
        self.timer.stop()
        self.label_terms.setText("")
        self.btn_play.setEnabled(True)

    def generateRandNums(self):
        randNum = lambda d : random.randint(10 ** (d - 1), 10 ** d - 1)
        self.randNums.clear()

        # Append 1st rand num
        num = randNum(self.digits)
        self.randNums.append(num)

        # Append rest of sequentially unique rand nums
        for _ in range(self.count - 1):
            num = randNum(self.digits)
            while num == self.randNums[-1]:
                num = randNum(self.digits)
            self.randNums.append(num)

    def updateNumber(self):
        self.count -= 1
        if self.count >= 0:
            #sd.play(self.wave, samplerate=9680)
            #self.play_once()
            self.player.play_once(self.wave_bytes)
            self.label_number.setText(str(self.randNums[self.count]))
        else:
            self.stopTimer()
            self.label_terms.setText('+'.join(map(str, self.randNums[::-1])))
            self.label_number.setText(str(sum(self.randNums)))

    def quit(self):
        self.stopTimer()
        self.initUI()
        self.Stack.setCurrentIndex(0)

    def timeChanged(self, value):
        self.time = value / 10
        self.label_time.setText(f"Seconds per number: {self.time}")

    def digitsChanged(self, value):
        self.digits = value
        self.label_digits.setText(f"Digits per number: {self.digits}")

    def countChanged(self, value):
        self.count = value
        self.label_count.setText(f"Numbers per round: {self.count}")

    def playPressed(self):
        if not self.timer.isActive():
            self.btn_play.setEnabled(False)
            self.generateRandNums()
            self.label_terms.setText("")
            self.Stack.setCurrentIndex(1)
            self.getReady()


if __name__ in "__main__":
    app = QApplication([])
    main = AnzanApp()
    main.show()
    app.exec()
