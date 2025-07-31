import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PIL import Image
import pydicom
import numpy as np
import os

class ImageModeChecker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Mode Checker")
        self.setGeometry(100, 100, 600, 400)

        # 중앙 위젯 및 레이아웃 설정
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # 드래그 앤 드롭 안내 레이블
        self.instruction_label = QLabel("Drag and drop JPG, JPEG, PNG, WebP, TIF, TIFF, or DCM files here")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.instruction_label)

        # 파일명 표시 레이블
        self.file_name_label = QLabel("No file loaded")
        self.file_name_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.file_name_label)

        # 결과 출력 레이블
        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignCenter)
        # 폰트 크기 2배로 설정
        default_font = self.result_label.font()
        default_size = default_font.pointSize()
        new_font = QFont(default_font.family(), default_size * 2)
        self.result_label.setFont(new_font)
        self.layout.addWidget(self.result_label)

        # 드래그 앤 드롭 활성화
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        # 파일 드래그 시 허용된 확장자 확인
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff', '.dcm')):
                    event.acceptProposedAction()
                    return
            # 지원되지 않는 파일 확장자일 경우 팝업
            QMessageBox.warning(self, "Unsupported File", "Not supported file")
        event.ignore()

    def dropEvent(self, event):
        # 드롭된 파일 처리
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff', '.dcm')):
                # 파일명 표시
                file_name = os.path.basename(file_path)
                self.file_name_label.setText(f"File: {file_name}")
                self.process_file(file_path)
                break  # 첫 번째 유효 파일만 처리
        event.acceptProposedAction()

    def process_file(self, file_path):
        try:
            if file_path.lower().endswith('.dcm'):
                # DICOM 파일 처리
                dicom = pydicom.dcmread(file_path)
                if hasattr(dicom, 'PhotometricInterpretation'):
                    mode = dicom.PhotometricInterpretation
                    self.result_label.setText(mode)
                else:
                    self.result_label.setText("Unknown mode (DICOM)")
            else:
                # JPG, JPEG, PNG, WebP, TIF, TIFF 처리
                with Image.open(file_path) as img:
                    mode = img.mode
                    if mode == 'RGB':
                        self.result_label.setText("RGB")
                    elif mode == 'RGBA':
                        # 알파 채널 평균값 계산
                        alpha = np.array(img.split()[-1])  # 알파 채널 추출
                        alpha_mean = np.mean(alpha) / 255.0  # 0~255를 0~1로 정규화
                        self.result_label.setText(f"RGBA(Alpha={alpha_mean:.1f})")
                    elif mode == 'LA':
                        # LA 모드 알파 채널 평균값 계산
                        alpha = np.array(img.split()[-1])  # 알파 채널 추출
                        alpha_mean = np.mean(alpha) / 255.0
                        self.result_label.setText(f"LA(Alpha={alpha_mean:.1f})")
                    else:
                        self.result_label.setText(mode)
        except Exception as e:
            self.result_label.setText(f"Error: Invalid or unsupported file format ({str(e)})")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ImageModeChecker()
    window.show()
    sys.exit(app.exec_())
