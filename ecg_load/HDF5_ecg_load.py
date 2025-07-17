import sys
import os
import h5py
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QPushButton, QWidget,
    QVBoxLayout, QLabel, QStackedLayout
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QMovie
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.signal import butter, filtfilt


def bandpass_filter(signal, lowcut, highcut, fs, order=3):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, signal, axis=0)


def load_ecg_from_hdf5(file_path):
    with h5py.File(file_path, 'r') as f:
        ecg = f['ecg'][:]  # (12, 5000)
    ecg = ecg.T  # (5000, 12)
    fs = 500
    return ecg, fs


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
            if file_path.lower().endswith(".h5"):
                self.drop_callback(file_path)


class ECGViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1600, 1200)

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        self.load_button = QPushButton("ECG 파일 열기 (.h5)")
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
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "ECG 데이터 파일 선택", "", "HDF5 Files (*.h5)", options=options)
        if file_path:
            self.load_and_plot(file_path)

    def load_and_plot(self, file_path):
        self.current_file = file_path
        self.spinner_movie.start()
        self.stack_layout.setCurrentWidget(self.spinner_widget)
        QTimer.singleShot(100, lambda: self.plot_ecg(file_path))

    def plot_ecg(self, file_path):
        try:
            ecg, fs = load_ecg_from_hdf5(file_path)
            self.setWindowTitle(f"ECG HDF5 Viewer - {os.path.basename(self.current_file)}")
            ecg = bandpass_filter(ecg, 0.5, 40, fs)

            layout_order = ['I', 'aVR', 'V1', 'V4',
                            'II', 'aVL', 'V2', 'V5',
                            'III', 'aVF', 'V3', 'V6']

            lead_mapping = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF',
                            'V1', 'V2', 'V3', 'V4', 'V5', 'V6']

            self.figure.clear()
            short_duration = int(2.5 * fs)
            long_duration = int(10 * fs)
            sec_per_mm = 0.04
            mv_per_mm = 0.1
            lead_indices = {name: i for i, name in enumerate(lead_mapping)}

            for i, lead in enumerate(layout_order):
                ax = self.figure.add_subplot(4, 4, i + 1)
                idx = lead_indices[lead]
                data = ecg[:short_duration, idx]
                time = np.arange(len(data)) / fs
                ax.plot(time, data, linewidth=0.8, color='blue')
                ax.set_xlim(0, 2.5)
                ax.set_ylim(-2, 2)
                ax.set_xticks(np.arange(0, 2.6, 0.2))
                ax.set_yticks(np.arange(-2.0, 2.1, 0.5))
                ax.set_xticks(np.arange(0, 2.6, sec_per_mm), minor=True)
                ax.set_yticks(np.arange(-2.0, 2.1, mv_per_mm), minor=True)
                ax.grid(True, which='major', linestyle='--', linewidth=0.5)
                ax.grid(True, which='minor', linestyle=':', linewidth=0.3, color='gray')
                ax.set_title(lead, fontsize=12)
                ax.tick_params(labelsize=6)
                ax.set_xlabel("Time (s)", fontsize=7)
                ax.set_ylabel("Amplitude (mV)", fontsize=7)

            ax = self.figure.add_subplot(4, 1, 4)
            idx = lead_indices['II']
            data = ecg[:long_duration, idx]
            time = np.arange(len(data)) / fs
            ax.plot(time, data, linewidth=0.8, color='blue')
            ax.set_xlim(0, 10)
            ax.set_ylim(-2, 2)
            ax.set_xticks(np.arange(0, 10.1, 0.2))
            ax.set_yticks(np.arange(-2.0, 2.1, 0.5))
            ax.set_xticks(np.arange(0, 10.1, sec_per_mm), minor=True)
            ax.set_yticks(np.arange(-2.0, 2.1, mv_per_mm), minor=True)
            ax.grid(True, which='major', linestyle='--', linewidth=0.5)
            ax.grid(True, which='minor', linestyle=':', linewidth=0.3, color='gray')
            ax.set_title("II (repeat)", fontsize=12)
            ax.tick_params(labelsize=6)
            ax.set_xlabel("Time (s)", fontsize=7)
            ax.set_ylabel("Amplitude (mV)", fontsize=7)

            self.figure.tight_layout()
            self.canvas.draw()
            self.stack_layout.setCurrentWidget(self.canvas)
        finally:
            self.spinner_movie.stop()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = ECGViewer()
    viewer.show()
    sys.exit(app.exec_())
