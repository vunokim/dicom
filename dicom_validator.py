import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QTextEdit, QVBoxLayout, QFileDialog, QCheckBox
)
from PyQt5.QtCore import Qt

class DICOMValidatorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DICOM Validator GUI")
        self.setGeometry(200, 200, 700, 500)
        self.setAcceptDrops(True)

        # Widgets
        self.label = QLabel("Drag and drop a DICOM file here or click 'Load DICOM File'")
        self.label.setAlignment(Qt.AlignCenter)
        self.textbox = QTextEdit()
        self.textbox.setReadOnly(True)
        self.checkbox_verbose = QCheckBox("--verbose (각 태그 및 검증 과정을 자세히 출력)")
        self.checkbox_suppress = QCheckBox("--suppress-vr-warnings (VR (Value Representation) 관련 경고 메시지 숨김)")
        self.load_btn = QPushButton("Load DICOM File")
        self.validate_btn = QPushButton("Run Validation")

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.load_btn)
        layout.addWidget(self.checkbox_verbose)
        layout.addWidget(self.checkbox_suppress)
        layout.addWidget(self.validate_btn)
        layout.addWidget(self.textbox)
        self.setLayout(layout)

        # Connections
        self.load_btn.clicked.connect(self.load_file)
        self.validate_btn.clicked.connect(self.run_validation)
        self.file_path = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith('.dcm'):
                self.file_path = path
                self.label.setText(f"Loaded: {os.path.basename(path)}")
                break

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open DICOM File", "", "DICOM Files (*.dcm)")
        if path:
            self.file_path = path
            self.label.setText(f"Loaded: {os.path.basename(path)}")

    def run_validation(self):
        if not self.file_path:
            self.textbox.setText("⚠️ Please load a DICOM file first.")
            return

        cmd = ["validate_iods", self.file_path]
        if self.checkbox_verbose.isChecked():
            cmd.append("--verbose")
        if self.checkbox_suppress.isChecked():
            cmd.append("--suppress-vr-warnings")

        self.textbox.setText("🔄 검증 중입니다...\n잠시만 기다려 주세요.")

        # 새로운 방식: 실시간 출력 처리
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        output = ""
        while True:
            line = process.stdout.readline()
            if not line:
                break
            output += line
            self.textbox.setText(output)
            QApplication.processEvents()  # GUI 업데이트

        process.wait()
        if process.returncode != 0:
            self.textbox.append("\n❌ 오류가 발생했습니다.")

if __name__ == "__main__":
    app = QApplication([])
    window = DICOMValidatorGUI()
    window.show()
    app.exec_()
