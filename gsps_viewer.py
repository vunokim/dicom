import sys
import os
import numpy as np
import pydicom
from pydicom.dataelem import DataElement
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout,
    QWidget, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont, QCursor
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from colormath.color_objects import LabColor, sRGBColor
from colormath.color_conversions import convert_color
import matplotlib.patheffects as PathEffects

TARGET_TAGS = [
    ('0010', '0010'), ('0010', '0020'), ('0008', '1090'), ('0020', '4000'),
    ('1001', '1001'), ('1001', '1008'), ('1001', '1009'), ('1001', '1011'), ('1001', '1015')
]

class DicomCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        self.fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
        super().__init__(self.fig)
        self.setParent(parent)
        self.image = None
        self.gsps_overlay = []
        self.gsps_texts = []
        self.overlay_enabled = True
        plt.rcParams['font.family'] = 'DejaVu Sans'

    def show_dicom(self, dicom_ds):
        self.ax.clear()
        self.image = dicom_ds.pixel_array
        self.ax.imshow(self.image, cmap='gray')
        self.ax.set_xlabel('Pixel X')
        self.ax.set_ylabel('Pixel Y')
        self.ax.tick_params(axis='x', which='both', bottom=True, labelbottom=True)
        self.ax.tick_params(axis='y', which='both', left=True, labelleft=True)
        self.draw()

    def apply_gsps(self, gsps_ds):
        if self.image is None:
            return
        self.gsps_overlay.clear()
        self.gsps_texts.clear()

        target_texts = []
        image_height, image_width = self.image.shape
        if "GraphicAnnotationSequence" in gsps_ds:
            for annotation in gsps_ds.GraphicAnnotationSequence:
                if "TextObjectSequence" in annotation:
                    for text in annotation.TextObjectSequence:
                        text_val_elem = text.get((0x0070, 0x0006), None)
                        if text_val_elem:
                            text_val = text_val_elem.value if isinstance(text_val_elem, DataElement) else str(text_val_elem)

                            # VUNO®, ROI 1\nCTR=0.40, Pleural space 포함 텍스트 필터링
                            if any(x in text_val.lower() for x in ['vuno', 'roi', 'ctr', 'pleural space']):
                                anchor = text.get((0x0070, 0x0014), None)
                                justification_elem = text.get((0x0070, 0x0012), None)
                                justification = justification_elem.value if isinstance(justification_elem, DataElement) else 'LEFT' if justification_elem else 'LEFT'
                                justification = justification.upper()

                                if justification == 'RIGHT':
                                    ha = 'right'
                                elif justification == 'CENTER':
                                    ha = 'center'
                                else:
                                    ha = 'left'

                                # 정규화된 Anchor Point를 이미지 크기로 스케일링
                                pos = anchor.value if anchor else [0.5, 0.05]
                                x = pos[0] * image_width
                                y = pos[1] * image_height  # Matplotlib에 맞게 y축 조정

                                # Pleural space의 경우 Bounding Box 좌표 사용
                                if 'pleural space' in text_val.lower():
                                    bbox_top_left = text.get((0x0070, 0x0010), None)
                                    if bbox_top_left:
                                        x, y = bbox_top_left.value

                                color = 'white'
                                size = 12
                                weight = 'normal'
                                style = 'normal'

                                if anchor or bbox_top_left:
                                    target_texts.append((text_val, [x, y], ha, color, size, weight, style))

                if "GraphicObjectSequence" in annotation:
                    for obj in annotation.GraphicObjectSequence:
                        if obj.GraphicType == 'POLYLINE':
                            pts = np.array(obj.GraphicData).reshape(-1, 2)
                            self.gsps_overlay.append(pts)

        self.gsps_texts = target_texts
        self.refresh_overlay()

    def refresh_overlay(self):
        self.ax.clear()
        if self.image is not None:
            self.ax.imshow(self.image, cmap='gray')
            self.ax.set_xlabel('Pixel X')
            self.ax.set_ylabel('Pixel Y')
            self.ax.tick_params(axis='x', which='both', bottom=True, labelbottom=True)
            self.ax.tick_params(axis='y', which='both', left=True, labelleft=True)
            if self.overlay_enabled:
                for pts in self.gsps_overlay:
                    self.ax.plot(pts[:, 0], pts[:, 1], 'r-', linewidth=2)
                for txt, pos, align, color, size, weight, style in self.gsps_texts:
                    text = self.ax.text(pos[0], pos[1], txt, color=color, fontsize=size, weight=weight, style=style, ha=align)
                    text.set_path_effects([PathEffects.withStroke(linewidth=2, foreground='black')])
        self.draw()

class DicomGspsViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DICOM + GSPS Viewer")
        self.setGeometry(100, 100, 900, 1300)
        self.setAcceptDrops(True)

        self.dicom_ds = None
        self.gsps_ds = None

        self.canvas = DicomCanvas(self)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Group", "Element", "Value"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        layout.addWidget(self.canvas, stretch=5)
        layout.addWidget(self.table, stretch=2)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            try:
                ds = pydicom.dcmread(file_path, force=True)
                print(f"Loaded dataset: {file_path}")
                # 모든 태그 출력
                all_elements = list(ds.iterall())
                print(f"All tags: {[str(elem.tag) for elem in all_elements]}")
            except Exception as e:
                QMessageBox.warning(self, "파일 오류", f"DICOM 파일이 아닙니다: {file_path} - {str(e)}")
                continue

            sop_class_uid = ds.SOPClassUID
            if sop_class_uid.name == "Grayscale Softcopy Presentation State Storage":
                if self.dicom_ds is None:
                    QMessageBox.warning(self, "로드 순서 오류", "먼저 원본 DICOM 파일을 불러오세요.")
                    continue
                ref_uid = ds.ReferencedSeriesSequence[0].ReferencedImageSequence[0].ReferencedSOPInstanceUID
                if ref_uid != self.dicom_ds.SOPInstanceUID:
                    QMessageBox.warning(self, "GSPS 매칭 오류", "GSPS가 현재 원본 이미지와 매칭되지 않습니다.")
                    continue
                self.gsps_ds = ds
                self.canvas.apply_gsps(ds)
                self.populate_table(ds)
            else:
                self.dicom_ds = ds
                self.gsps_ds = None
                self.canvas.show_dicom(ds)
                self.setWindowTitle(f"DICOM + GSPS Viewer    [ {os.path.basename(file_path)} ]")

    def populate_table(self, ds):
        self.table.setRowCount(0)
        # TARGET_TAGS 순서에 따라 태그를 필터링, 복수 개 지원
        tag_elements = {}
        for element in ds.iterall():
            tag_key = (f"{element.tag.group:04x}", f"{element.tag.element:04x}")
            if tag_key in TARGET_TAGS:
                if tag_key not in tag_elements:
                    tag_elements[tag_key] = []
                tag_elements[tag_key].append(element)

        # TARGET_TAGS 순서대로 테이블에 추가, 복수 개일 경우 모두 표시
        for tag_key in TARGET_TAGS:
            if tag_key in tag_elements:
                for value_element in tag_elements[tag_key]:
                    print(f"Tag ({tag_key[0]}, {tag_key[1]}): {value_element}, Type: {type(value_element)}, Value: {value_element.value if value_element.value is not None else 'None'}")
                    if isinstance(value_element, DataElement):
                        try:
                            value = str(value_element.value) if value_element.value is not None else 'None'
                        except Exception as e:
                            value = f"Error parsing: {str(e)}"
                    else:
                        value = str(value_element) if value_element else 'None'

                    display_value = value[:70] + '...' if len(value) > 73 else value
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(tag_key[0]))
                    self.table.setItem(row, 1, QTableWidgetItem(tag_key[1]))
                    value_item = QTableWidgetItem(display_value)
                    if len(value) > 70:
                        value_item.setToolTip(value)
                    self.table.setItem(row, 2, value_item)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = DicomGspsViewer()
    viewer.show()
    sys.exit(app.exec_())
