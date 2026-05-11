import os
import sys
import pydicom
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLabel,
    QMessageBox,
    QLineEdit,
    QSizePolicy,
    QSpacerItem,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QIcon
import numpy as np
from pydicom.misc import is_dicom

def get_resource_path(filename):
    """Return the absolute path to a resource, supporting PyInstaller bundles."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(__file__), filename)

class DicomTagLoader(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.pixel_data_value = None
        self.current_filters = {
            "group": "",
            "element": "",
            "description": "",
        }

    def initUI(self):
        self.setWindowTitle("DICOM Tag Loader")
        self.setGeometry(100, 100, 1200, 900)
        self.setAcceptDrops(True)
        layout = QVBoxLayout()

        # File Open 버튼 및 File path 표시 레이블 가로 레이아웃
        h_layout = QHBoxLayout()
        self.open_button = QPushButton("File Open", self)
        self.open_button.setFixedWidth(100)
        self.open_button.clicked.connect(self.openFile)
        h_layout.addWidget(self.open_button)

        self.file_path = QLabel("File path will appear here")
        h_layout.addWidget(self.file_path)
        layout.addLayout(h_layout)

        # 검색 및 버튼 Layout 설정
        function_layout = QHBoxLayout()

        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("Group")
        self.group_input.setFixedWidth(60)
        self.group_input.setValidator(QIntValidator(0, 9999))

        self.element_input = QLineEdit()
        self.element_input.setPlaceholderText("Element")
        self.element_input.setFixedWidth(60)
        self.element_input.setValidator(QIntValidator(0, 9999))

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Description")
        self.description_input.setFixedWidth(200)

        self.clear_button = QPushButton("X")
        self.clear_button.setFixedWidth(20)
        self.clear_button.clicked.connect(self.clearSearchFields)

        function_layout.addWidget(self.group_input)
        function_layout.addWidget(self.element_input)
        function_layout.addWidget(self.description_input)
        function_layout.addWidget(self.clear_button)
        function_layout.addStretch()

        function_layout.addSpacerItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )

        self.copy_all_button = QPushButton("All Copy", self)
        self.copy_all_button.setFixedWidth(75)
        self.copy_value_button = QPushButton("Value Copy", self)
        self.copy_value_button.setFixedWidth(95)

        self.copy_all_button.clicked.connect(self.copyAll)
        self.copy_value_button.clicked.connect(
            lambda: self.copyValue(self.tabs.currentWidget())
        )

        function_layout.addStretch()
        function_layout.addWidget(self.copy_all_button)
        function_layout.addWidget(self.copy_value_button)
        layout.addLayout(function_layout)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.initEmptyTabs()

        self.group_input.textChanged.connect(self.filterTable)
        self.element_input.textChanged.connect(self.filterTable)
        self.description_input.textChanged.connect(self.filterTable)

    def initEmptyTabs(self):
        self.addTab(None, "All")
        self.addTab(None, "Patient")
        self.addTab(None, "Study/Series")
        self.addTab(None, "Image")

    def openFile(self, filepath=None):
        if not filepath:
            file_dialog = QFileDialog.getOpenFileName(
                self, "Open DICOM File", "", "DICOM Files (*.dcm)"
            )
            filepath = file_dialog[0]
        if filepath:
            self.file_path.setText(filepath)
            try:
                if not is_dicom(filepath):
                    QMessageBox.critical(
                        self, "Error", "The selected file is not a valid DICOM file."
                    )
                    return
                dicom_data = pydicom.dcmread(filepath, force=True)

                # 현재 선택된 탭 인덱스 저장
                current_tab_index = self.tabs.currentIndex()
                current_tab_name = self.tabs.tabText(current_tab_index) if current_tab_index >= 0 else "All"

                # 탭 유지 및 내용 갱신
                self.tabs.clear()
                self.pixel_data_value = None
                self.addTab(dicom_data, "All")
                self.addTab(dicom_data, "Patient")
                self.addTab(dicom_data, "Study/Series")
                self.addTab(dicom_data, "Image")

                # 이전 탭으로 복원
                for i in range(self.tabs.count()):
                    if self.tabs.tabText(i) == current_tab_name:
                        self.tabs.setCurrentIndex(i)
                        break
                else:
                    self.tabs.setCurrentIndex(0)  # 탭 이름이 없으면 All 탭으로

                # 기존 검색 필터 복원
                self.restoreFilters()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error reading DICOM file: {e}")
            return dicom_data

    def addTab(self, dicom_data, tag_type):
        table = QTableWidget()
        elements = []

        if tag_type == "All":
            if hasattr(dicom_data, "file_meta"):
                for element in dicom_data.file_meta:
                    elements.append(element)

        if dicom_data:
            seen_tags = set()

            for element in dicom_data.iterall():
                # 최소 수정안:
                # 기존에는 (group, element)만 같으면 뒤의 항목을 모두 숨겼습니다.
                # 이제는 같은 tag라도 value가 다르면 별도로 보여주고,
                # value까지 같을 때만 중복으로 간주합니다.
                try:
                    value_key = repr(element.value)
                except Exception:
                    value_key = str(element.value)

                tag_key = (element.tag.group, element.tag.element, value_key)

                if tag_key not in seen_tags:
                    seen_tags.add(tag_key)
                    if element.name in ["PixelHeight", "PixelWidth"] and element.value == 0:
                        element.value = 1
                        print(f"Warning: Invalid value for {element.name}. Defaulting to 1.")
                    if element.tag.group == 0x7FE0 and element.tag.element == 0x0010:
                        self.pixel_data_value = np.copy(element.value)
                    if tag_type == "All":
                        elements.append(element)
                    elif tag_type == "Patient" and element.tag.group == 0x0010:
                        elements.append(element)
                    elif tag_type == "Study/Series" and (
                        "Study" in element.name or "Series" in element.name
                    ):
                        elements.append(element)
                    elif tag_type == "Image" and (
                        element.tag.group == 0x0028
                        or "Pixel" in element.name
                        or "Bit" in element.name
                        or "Image" in element.name
                        or "Window" in element.name
                    ):
                        elements.append(element)

        elements.sort(key=lambda x: (x.tag.group, x.tag.element))

        table.setRowCount(len(elements))
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["Group", "Element", "Description", "VR", "Size", "Value"]
        )

        table.setColumnWidth(0, 55)
        table.setColumnWidth(1, 55)
        table.setColumnWidth(2, 230)
        table.setColumnWidth(3, 25)
        table.setColumnWidth(4, 30)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)

        for row, element in enumerate(elements):
            table.setItem(row, 0, QTableWidgetItem(f"{element.tag.group:04X}"))
            table.setItem(row, 1, QTableWidgetItem(f"{element.tag.element:04X}"))
            table.setItem(row, 2, QTableWidgetItem(element.name))
            table.setItem(row, 3, QTableWidgetItem(element.VR))
            size = len(str(element.value)) if element.value else 0
            table.setItem(row, 4, QTableWidgetItem(str(size)))
            if element.tag.group == 0x0010 and element.tag.element == 0x0010:
                table.setItem(row, 5, QTableWidgetItem(str(dicom_data.PatientName)))
            elif element.tag.group == 0x7FE0 and element.tag.element == 0x0010:
                table.setItem(row, 5, QTableWidgetItem("Encoded graphical image data"))
            else:
                table.setItem(row, 5, QTableWidgetItem(str(element.value)))

            if row % 2 == 0:
                for col in range(table.columnCount()):
                    item = table.item(row, col)
                    if item:
                        item.setBackground(QColor(0xFB, 0xFA, 0xFB))

        self.tabs.addTab(table, tag_type)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            file_url = event.mimeData().urls()[0]
            filepath = file_url.toLocalFile()
            try:
                if not is_dicom(filepath):
                    QMessageBox.warning(
                        self, "Error", "The dropped file is not a valid DICOM file."
                    )
                    return
                self.openFile(filepath)
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Error processing the dropped file: {e}"
                )
        else:
            QMessageBox.warning(
                self, "Error", "The dropped content is not a valid file."
            )

    def _get_row_data(self, table, selected_row, columns=None):
        """
        행 데이터를 가져옴
        columns=None: 모든 열 복사
        columns=정수: 해당 열만 복사
        """
        row_data = []

        if columns is None:
            cols_to_copy = range(table.columnCount())
        else:
            cols_to_copy = [columns]

        for col in cols_to_copy:
            item = table.item(selected_row, col)
            if item:
                # PixelData (0x7FE0, 0x0010) 특수처리
                if (col == 5 and
                    table.item(selected_row, 0).text().strip().upper() == "7FE0" and
                    table.item(selected_row, 1).text().strip().upper() == "0010"):
                    row_data.append(np.array2string(self.pixel_data_value))
                else:
                    row_data.append(item.text())

        return row_data

    def copyValue(self, table):
        """선택된 행의 Value 열(column 5)만 복사"""
        selected_row = table.currentRow()
        if selected_row >= 0:
            row_data = self._get_row_data(table, selected_row, columns=5)
            QApplication.clipboard().setText("\t".join(row_data))
        else:
            print("No row selected.")

    def copyAll(self):
        """선택된 행의 모든 열 복사"""
        table = self.tabs.currentWidget()
        selected_row = table.currentRow()
        if selected_row >= 0:
            row_data = self._get_row_data(table, selected_row)  # columns=None
            QApplication.clipboard().setText("\t".join(row_data))
        else:
            print("No row selected.")

    def filterTable(self):
        self.current_filters["group"] = self.group_input.text().strip()
        self.current_filters["element"] = self.element_input.text().strip()
        self.current_filters["description"] = self.description_input.text().strip().lower()

        group_id = self.current_filters["group"]
        element_id = self.current_filters["element"]
        description_txt = self.current_filters["description"]

        for i in range(self.tabs.count()):
            table = self.tabs.widget(i)
            for row in range(table.rowCount()):
                group_match = (
                    True
                    if not group_id
                    else table.item(row, 0)
                    and table.item(row, 0).text().startswith(group_id)
                )
                element_match = (
                    True
                    if not element_id
                    else table.item(row, 1)
                    and table.item(row, 1).text().startswith(element_id)
                )
                description_match = (
                    True
                    if not description_txt
                    else table.item(row, 2)
                    and description_txt in table.item(row, 2).text().lower()
                )
                table.setRowHidden(
                    row, not (group_match and element_match and description_match)
                )

    def restoreFilters(self):
        self.group_input.setText(self.current_filters["group"])
        self.element_input.setText(self.current_filters["element"])
        self.description_input.setText(self.current_filters["description"])
        self.filterTable()

    def clearSearchFields(self):
        self.group_input.clear()
        self.element_input.clear()
        self.description_input.clear()
        self.filterTable()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    icon_path = get_resource_path("tag.ico")
    app.setWindowIcon(QIcon(icon_path))
    viewer = DicomTagLoader()
    viewer.show()
    sys.exit(app.exec_())
