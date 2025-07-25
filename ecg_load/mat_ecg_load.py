<<<<<<< HEAD
import sys
import os
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QPushButton,
    QWidget, QVBoxLayout, QLabel, QStackedLayout
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QMovie
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.io import loadmat
import wfdb
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
            if file_path.endswith('.mat'):
                base_path = os.path.splitext(file_path)[0]
                self.drop_callback(base_path)

class MatECGViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ECG Viewer (.mat + .hea)")
        self.setGeometry(100, 100, 1600, 1200)

        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        self.load_button = QPushButton('ECG 파일 열기 (.mat)', self)
        self.load_button.clicked.connect(self.load_ecg)
        self.layout.addWidget(self.load_button)

        self.stack_layout = QStackedLayout()
        self.layout.addLayout(self.stack_layout)

        self.figure = Figure(figsize=(16, 12))
        self.canvas = DropCanvas(self.figure, self.load_and_plot)
        self.stack_layout.addWidget(self.canvas)

        self.spinner_widget = QWidget()
        self.spinner_layout = QVBoxLayout(self.spinner_widget)
        self.spinner_layout.setAlignment(Qt.AlignCenter)

        self.spinner_label = QLabel()
        self.spinner_label.setAlignment(Qt.AlignCenter)
        self.spinner_movie = QMovie("spinner.gif")
        self.spinner_movie.setScaledSize(QSize(64, 64))
        self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_layout.addWidget(self.spinner_label)

        self.stack_layout.addWidget(self.spinner_widget)

    def load_ecg(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "ECG .mat 파일 선택", "", "MAT Files (*.mat)")
        if file_path:
            base_path = os.path.splitext(file_path)[0]
            hea_path = base_path + ".hea"
            if not os.path.exists(hea_path):
                print(f"헤더 파일 누락: {hea_path}")
                return
            self.spinner_movie.start()
            self.stack_layout.setCurrentWidget(self.spinner_widget)
            QTimer.singleShot(100, lambda: self._load_and_plot(file_path, hea_path))

    def load_and_plot(self, base_path):
        mat_path = base_path + ".mat"
        hea_path = base_path + ".hea"
        if not os.path.exists(mat_path) or not os.path.exists(hea_path):
            print(f"파일 누락: {mat_path} 또는 {hea_path}")
            return
        self.spinner_movie.start()
        self.stack_layout.setCurrentWidget(self.spinner_widget)
        QTimer.singleShot(100, lambda: self._load_and_plot(mat_path, hea_path))

    def _load_and_plot(self, mat_path, hea_path):
        try:
            # Load file name and show
            filename = os.path.basename(mat_path)
            self.setWindowTitle(f"ECG Viewer (.mat + .hea) - {filename}")

            # Load header info
            header = wfdb.rdheader(os.path.splitext(hea_path)[0])
            fs = header.fs
            lead_names = header.sig_name

            # Load .mat ECG signal
            mat_data = loadmat(mat_path)
            signal = mat_data['val'].T  # shape: (samples, leads)
            signal = signal / 1000.0     # 단위 정규화: 원시값 → mV

            # Filtering
            signal = bandpass_filter(signal, 0.5, 40, fs)

            # Plot
            self.plot_ecg(signal, lead_names, fs)

        except Exception as e:
            print(f"파일 로딩 오류: {e}")
        self.spinner_movie.stop()
        self.stack_layout.setCurrentWidget(self.canvas)

    def plot_ecg(self, signal, lead_names, fs):
        self.figure.clear()

        short_duration = int(fs * 2.5)
        long_duration = int(fs * 12)
        time_short = np.arange(short_duration) / fs
        time_long = np.arange(long_duration) / fs

        layout_order = [
            'I', 'aVR', 'V1', 'V4',
            'II', 'aVL', 'V2', 'V5',
            'III', 'aVF', 'V3', 'V6'
        ]
        lead_indices = {name.upper(): idx for idx, name in enumerate(lead_names)}
        valid_leads = [lead for lead in layout_order if lead.upper() in lead_indices]

        sec_per_mm = 0.04  # 시간축 작은 눈금
        mv_per_mm = 0.1    # 진폭축 작은 눈금

        for i, lead in enumerate(valid_leads):
            idx = lead_indices[lead.upper()]
            ax = self.figure.add_subplot(4, 4, i + 1)
            ecg = signal[:short_duration, idx]
            ax.plot(time_short[:len(ecg)], ecg, linewidth=0.8)
            ax.set_title(f"{lead}", fontsize=14)
            ax.set_xlabel("Time (s)", fontsize=7)
            ax.set_ylabel("Amplitude (mV)", fontsize=7)
            ax.tick_params(axis='both', which='major', labelsize=6)
            ax.set_ylim([-2.0, 2.0])

            ax.set_xticks(np.arange(0, 2.5, 0.2))  # 주 눈금
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
            ax.set_title("II (repeat)", fontsize=14)
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

        self.figure.tight_layout()
        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = MatECGViewer()
    viewer.show()
    sys.exit(app.exec_())
=======
import sys
import os
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QPushButton,
    QWidget, QVBoxLayout, QLabel, QStackedLayout
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QMovie
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.io import loadmat
import wfdb
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
            if file_path.endswith('.mat'):
                base_path = os.path.splitext(file_path)[0]
                self.drop_callback(base_path)

class MatECGViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ECG Viewer (.mat + .hea)")
        self.setGeometry(100, 100, 1600, 1200)

        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        self.load_button = QPushButton('ECG 파일 열기 (.mat)', self)
        self.load_button.clicked.connect(self.load_ecg)
        self.layout.addWidget(self.load_button)

        self.stack_layout = QStackedLayout()
        self.layout.addLayout(self.stack_layout)

        self.figure = Figure(figsize=(16, 12))
        self.canvas = DropCanvas(self.figure, self.load_and_plot)
        self.stack_layout.addWidget(self.canvas)

        self.spinner_widget = QWidget()
        self.spinner_layout = QVBoxLayout(self.spinner_widget)
        self.spinner_layout.setAlignment(Qt.AlignCenter)

        self.spinner_label = QLabel()
        self.spinner_label.setAlignment(Qt.AlignCenter)
        self.spinner_movie = QMovie("spinner.gif")
        self.spinner_movie.setScaledSize(QSize(64, 64))
        self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_layout.addWidget(self.spinner_label)

        self.stack_layout.addWidget(self.spinner_widget)

    def load_ecg(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "ECG .mat 파일 선택", "", "MAT Files (*.mat)")
        if file_path:
            base_path = os.path.splitext(file_path)[0]
            hea_path = base_path + ".hea"
            if not os.path.exists(hea_path):
                print(f"헤더 파일 누락: {hea_path}")
                return
            self.spinner_movie.start()
            self.stack_layout.setCurrentWidget(self.spinner_widget)
            QTimer.singleShot(100, lambda: self._load_and_plot(file_path, hea_path))

    def load_and_plot(self, base_path):
        mat_path = base_path + ".mat"
        hea_path = base_path + ".hea"
        if not os.path.exists(mat_path) or not os.path.exists(hea_path):
            print(f"파일 누락: {mat_path} 또는 {hea_path}")
            return
        self.spinner_movie.start()
        self.stack_layout.setCurrentWidget(self.spinner_widget)
        QTimer.singleShot(100, lambda: self._load_and_plot(mat_path, hea_path))

    def _load_and_plot(self, mat_path, hea_path):
        try:
            # Load file name and show
            filename = os.path.basename(mat_path)
            self.setWindowTitle(f"ECG Viewer (.mat + .hea) - {filename}")

            # Load header info
            header = wfdb.rdheader(os.path.splitext(hea_path)[0])
            fs = header.fs
            lead_names = header.sig_name

            # Load .mat ECG signal
            mat_data = loadmat(mat_path)
            signal = mat_data['val'].T  # shape: (samples, leads)
            signal = signal / 1000.0     # 단위 정규화: 원시값 → mV

            # Filtering
            signal = bandpass_filter(signal, 0.5, 40, fs)

            # Plot
            self.plot_ecg(signal, lead_names, fs)

        except Exception as e:
            print(f"파일 로딩 오류: {e}")
        self.spinner_movie.stop()
        self.stack_layout.setCurrentWidget(self.canvas)

    def plot_ecg(self, signal, lead_names, fs):
        self.figure.clear()

        short_duration = int(fs * 2.5)
        long_duration = int(fs * 12)
        time_short = np.arange(short_duration) / fs
        time_long = np.arange(long_duration) / fs

        layout_order = [
            'I', 'aVR', 'V1', 'V4',
            'II', 'aVL', 'V2', 'V5',
            'III', 'aVF', 'V3', 'V6'
        ]
        lead_indices = {name.upper(): idx for idx, name in enumerate(lead_names)}
        valid_leads = [lead for lead in layout_order if lead.upper() in lead_indices]

        sec_per_mm = 0.04  # 시간축 작은 눈금
        mv_per_mm = 0.1    # 진폭축 작은 눈금

        for i, lead in enumerate(valid_leads):
            idx = lead_indices[lead.upper()]
            ax = self.figure.add_subplot(4, 4, i + 1)
            ecg = signal[:short_duration, idx]
            ax.plot(time_short[:len(ecg)], ecg, linewidth=0.8)
            ax.set_title(f"{lead}", fontsize=14)
            ax.set_xlabel("Time (s)", fontsize=7)
            ax.set_ylabel("Amplitude (mV)", fontsize=7)
            ax.tick_params(axis='both', which='major', labelsize=6)
            ax.set_ylim([-2.0, 2.0])

            ax.set_xticks(np.arange(0, 2.5, 0.2))  # 주 눈금
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
            ax.set_title("II (repeat)", fontsize=14)
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

        self.figure.tight_layout()
        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = MatECGViewer()
    viewer.show()
    sys.exit(app.exec_())
>>>>>>> 0eb1d258402411ad34ee3ac09ddb137e034d4ea3
