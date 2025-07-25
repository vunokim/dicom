<<<<<<< HEAD
import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QPushButton, QWidget,
    QVBoxLayout, QLabel, QStackedLayout, QHBoxLayout
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QMovie
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import wfdb
import numpy as np
from scipy.signal import butter, filtfilt


def bandpass_filter(signal, lowcut, highcut, fs, order=3):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, signal, axis=0)


class DropCanvas(FigureCanvas):
    def __init__(self, figure, drop_callback):
        super().__init__(figure)
        self.setAcceptDrops(True)
        self.drop_callback = drop_callback

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith('.dat'):
                base_path = os.path.splitext(file_path)[0]
                self.drop_callback(base_path)


class ECGViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ECG Viewer (PTB-XL)")
        self.current_path = None
        self.setGeometry(100, 100, 1600, 1200)

        # 중앙 위젯
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        # 파일 열기 버튼
        self.load_button = QPushButton('ECG 파일 열기 (.dat)', self)
        self.load_button.clicked.connect(self.load_ecg)
        self.layout.addWidget(self.load_button)

        # 그래프 + 스피너를 위한 Stack
        self.stack_layout = QStackedLayout()
        self.layout.addLayout(self.stack_layout)

        # 그래프 영역
        self.figure = Figure(figsize=(16, 12))
        self.canvas = DropCanvas(self.figure, self.load_and_plot)
        self.stack_layout.addWidget(self.canvas)

        # 로딩 스피너
        self.spinner_widget = QWidget()
        self.spinner_layout = QVBoxLayout(self.spinner_widget)
        self.spinner_layout.setAlignment(Qt.AlignCenter)

        self.spinner_label = QLabel()
        self.spinner_label.setAlignment(Qt.AlignCenter)
        self.spinner_movie = QMovie("spinner.gif")
        self.spinner_movie.setScaledSize(QSize(64, 64))  # 크기를 절반 정도로 설정
        self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_layout.addWidget(self.spinner_label)

        self.stack_layout.addWidget(self.spinner_widget)

        # 드래그 안내 텍스트
        self.canvas_text = self.figure.text(0.5, 0.5, 'Drag and Drop ECG File Here',
                                            ha='center', va='center', fontsize=20, alpha=0.3)

    def load_ecg(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "ECG 데이터 파일 선택", "", "DAT Files (*.dat)", options=options)

        if file_path:
            base_path = os.path.splitext(file_path)[0]
            self.load_and_plot(base_path)

    def load_and_plot(self, base_path):
        self.spinner_movie.start()
        self.stack_layout.setCurrentWidget(self.spinner_widget)
        QTimer.singleShot(100, lambda: self._load_and_plot(base_path))

    def _load_and_plot(self, base_path):
        self.current_path = base_path
        filename = os.path.basename(base_path)
        self.setWindowTitle(f"ECG Viewer (PTB-XL) - {filename}")
        try:
            signal, fields = wfdb.rdsamp(base_path)
            fs = fields['fs']
            signal = bandpass_filter(signal, 0.5, 40, fs)
            self.plot_ecg(signal, fields)
        except Exception as e:
            print(f"파일 로딩 오류: {e}")
        self.spinner_movie.stop()
        self.stack_layout.setCurrentWidget(self.canvas)

    def plot_ecg(self, signal, fields):
        self.figure.clear()
        fs = fields['fs']
        short_duration = int(fs * 2.5)
        long_duration = int(fs * 12)
        time_short = np.arange(short_duration) / fs
        time_long = np.arange(long_duration) / fs

        layout_order = [
            'I', 'aVR', 'V1', 'V4',
            'II', 'aVL', 'V2', 'V5',
            'III', 'aVF', 'V3', 'V6'
        ]
        lead_indices = {name.upper(): idx for idx, name in enumerate(fields['sig_name'])}
        valid_leads = [lead for lead in layout_order if lead.upper() in lead_indices]

        sec_per_mm = 0.04
        mv_per_mm = 0.1

        for i, lead in enumerate(valid_leads):
            idx = lead_indices[lead.upper()]
            ax = self.figure.add_subplot(4, 4, i + 1)
            ecg = signal[:short_duration, idx]
            ax.plot(time_short[:len(ecg)], ecg, linewidth=0.8)
            ax.set_title(f"{lead}", fontsize=16)
            ax.set_xlabel("Time (s)", fontsize=7)
            ax.set_ylabel("Amplitude (mV)", fontsize=7)
            ax.tick_params(axis='both', which='major', labelsize=6)
            ax.set_ylim([-2.0, 2.0])
            ax.set_xticks(np.arange(0, 2.5, 0.2))
            ax.set_xticks(np.arange(0, 2.5, sec_per_mm), minor=True)
            ax.set_yticks(np.arange(-2.0, 2.1, 0.5))
            ax.set_yticks(np.arange(-2.0, 2.1, mv_per_mm), minor=True)
            ax.grid(True, which='major', linestyle='--', linewidth=0.5)
            ax.grid(True, which='minor', linestyle=':', linewidth=0.3, color='gray')

        if 'II' in lead_indices:
            ax = self.figure.add_subplot(4, 1, 4)
            idx = lead_indices['II']
            ecg = signal[:long_duration, idx]
            ax.plot(time_long[:len(ecg)], ecg, linewidth=0.8)
            ax.set_title("II (repeat)", fontsize=16)
            ax.set_xlabel("Time (s)", fontsize=7)
            ax.set_ylabel("Amplitude (mV)", fontsize=7)
            ax.tick_params(axis='both', which='major', labelsize=6)
            ax.set_ylim([-2.0, 2.0])
            ax.set_xticks(np.arange(0, time_long[-1], 0.2))
            ax.set_xticks(np.arange(0, time_long[-1], sec_per_mm), minor=True)
            ax.set_yticks(np.arange(-2.0, 2.1, 0.5))
            ax.set_yticks(np.arange(-2.0, 2.1, mv_per_mm), minor=True)
            ax.grid(True, which='major', linestyle='--', linewidth=0.5)
            ax.grid(True, which='minor', linestyle=':', linewidth=0.3, color='gray')

        try:
            self.figure.texts.remove(self.canvas_text)
        except ValueError:
            pass

        self.figure.tight_layout()
        self.canvas.draw()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = ECGViewer()
    viewer.show()
    sys.exit(app.exec_())
=======
import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QPushButton, QWidget,
    QVBoxLayout, QLabel, QStackedLayout, QHBoxLayout
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QMovie
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import wfdb
import numpy as np
from scipy.signal import butter, filtfilt


def bandpass_filter(signal, lowcut, highcut, fs, order=3):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, signal, axis=0)


class DropCanvas(FigureCanvas):
    def __init__(self, figure, drop_callback):
        super().__init__(figure)
        self.setAcceptDrops(True)
        self.drop_callback = drop_callback

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith('.dat'):
                base_path = os.path.splitext(file_path)[0]
                self.drop_callback(base_path)


class ECGViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ECG Viewer (PTB-XL)")
        self.current_path = None
        self.setGeometry(100, 100, 1600, 1200)

        # 중앙 위젯
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        # 파일 열기 버튼
        self.load_button = QPushButton('ECG 파일 열기 (.dat)', self)
        self.load_button.clicked.connect(self.load_ecg)
        self.layout.addWidget(self.load_button)

        # 그래프 + 스피너를 위한 Stack
        self.stack_layout = QStackedLayout()
        self.layout.addLayout(self.stack_layout)

        # 그래프 영역
        self.figure = Figure(figsize=(16, 12))
        self.canvas = DropCanvas(self.figure, self.load_and_plot)
        self.stack_layout.addWidget(self.canvas)

        # 로딩 스피너
        self.spinner_widget = QWidget()
        self.spinner_layout = QVBoxLayout(self.spinner_widget)
        self.spinner_layout.setAlignment(Qt.AlignCenter)

        self.spinner_label = QLabel()
        self.spinner_label.setAlignment(Qt.AlignCenter)
        self.spinner_movie = QMovie("spinner.gif")
        self.spinner_movie.setScaledSize(QSize(64, 64))  # 크기를 절반 정도로 설정
        self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_layout.addWidget(self.spinner_label)

        self.stack_layout.addWidget(self.spinner_widget)

        # 드래그 안내 텍스트
        self.canvas_text = self.figure.text(0.5, 0.5, 'Drag and Drop ECG File Here',
                                            ha='center', va='center', fontsize=20, alpha=0.3)

    def load_ecg(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "ECG 데이터 파일 선택", "", "DAT Files (*.dat)", options=options)

        if file_path:
            base_path = os.path.splitext(file_path)[0]
            self.load_and_plot(base_path)

    def load_and_plot(self, base_path):
        self.spinner_movie.start()
        self.stack_layout.setCurrentWidget(self.spinner_widget)
        QTimer.singleShot(100, lambda: self._load_and_plot(base_path))

    def _load_and_plot(self, base_path):
        self.current_path = base_path
        filename = os.path.basename(base_path)
        self.setWindowTitle(f"ECG Viewer (PTB-XL) - {filename}")
        try:
            signal, fields = wfdb.rdsamp(base_path)
            fs = fields['fs']
            signal = bandpass_filter(signal, 0.5, 40, fs)
            self.plot_ecg(signal, fields)
        except Exception as e:
            print(f"파일 로딩 오류: {e}")
        self.spinner_movie.stop()
        self.stack_layout.setCurrentWidget(self.canvas)

    def plot_ecg(self, signal, fields):
        self.figure.clear()
        fs = fields['fs']
        short_duration = int(fs * 2.5)
        long_duration = int(fs * 12)
        time_short = np.arange(short_duration) / fs
        time_long = np.arange(long_duration) / fs

        layout_order = [
            'I', 'aVR', 'V1', 'V4',
            'II', 'aVL', 'V2', 'V5',
            'III', 'aVF', 'V3', 'V6'
        ]
        lead_indices = {name.upper(): idx for idx, name in enumerate(fields['sig_name'])}
        valid_leads = [lead for lead in layout_order if lead.upper() in lead_indices]

        sec_per_mm = 0.04
        mv_per_mm = 0.1

        for i, lead in enumerate(valid_leads):
            idx = lead_indices[lead.upper()]
            ax = self.figure.add_subplot(4, 4, i + 1)
            ecg = signal[:short_duration, idx]
            ax.plot(time_short[:len(ecg)], ecg, linewidth=0.8)
            ax.set_title(f"{lead}", fontsize=16)
            ax.set_xlabel("Time (s)", fontsize=7)
            ax.set_ylabel("Amplitude (mV)", fontsize=7)
            ax.tick_params(axis='both', which='major', labelsize=6)
            ax.set_ylim([-2.0, 2.0])
            ax.set_xticks(np.arange(0, 2.5, 0.2))
            ax.set_xticks(np.arange(0, 2.5, sec_per_mm), minor=True)
            ax.set_yticks(np.arange(-2.0, 2.1, 0.5))
            ax.set_yticks(np.arange(-2.0, 2.1, mv_per_mm), minor=True)
            ax.grid(True, which='major', linestyle='--', linewidth=0.5)
            ax.grid(True, which='minor', linestyle=':', linewidth=0.3, color='gray')

        if 'II' in lead_indices:
            ax = self.figure.add_subplot(4, 1, 4)
            idx = lead_indices['II']
            ecg = signal[:long_duration, idx]
            ax.plot(time_long[:len(ecg)], ecg, linewidth=0.8)
            ax.set_title("II (repeat)", fontsize=16)
            ax.set_xlabel("Time (s)", fontsize=7)
            ax.set_ylabel("Amplitude (mV)", fontsize=7)
            ax.tick_params(axis='both', which='major', labelsize=6)
            ax.set_ylim([-2.0, 2.0])
            ax.set_xticks(np.arange(0, time_long[-1], 0.2))
            ax.set_xticks(np.arange(0, time_long[-1], sec_per_mm), minor=True)
            ax.set_yticks(np.arange(-2.0, 2.1, 0.5))
            ax.set_yticks(np.arange(-2.0, 2.1, mv_per_mm), minor=True)
            ax.grid(True, which='major', linestyle='--', linewidth=0.5)
            ax.grid(True, which='minor', linestyle=':', linewidth=0.3, color='gray')

        try:
            self.figure.texts.remove(self.canvas_text)
        except ValueError:
            pass

        self.figure.tight_layout()
        self.canvas.draw()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = ECGViewer()
    viewer.show()
    sys.exit(app.exec_())
>>>>>>> 0eb1d258402411ad34ee3ac09ddb137e034d4ea3
