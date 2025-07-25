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
        self.setGeometry(100, 100, 960, 730)
        self.setAcceptDrops(True)
        layout = QVBoxLayout()

        h_layout = QHBoxLayout()
        self.open_button = QPushButton("File Open", self)
        self.open_button.setFixedWidth(100)
        self.open_button.clicked.connect(self.openFile)
        h_layout.addWidget(self.open_button)

        self.file_path = QLabel("File path will appear here")
        h_layout.addWidget(self.file_path)
        layout.addLayout(h_layout)

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

                # Specific Character Set 설정
                specific_charset = dicom_data.get("SpecificCharacterSet", "ISO_IR_100")
                if isinstance(specific_charset, list):
                    specific_charset = specific_charset[0] if specific_charset else "ISO_IR_100"
                if isinstance(specific_charset, str):
                    specific_charset = specific_charset.lstrip("\\")
                if "149" in specific_charset:
                    specific_charset = "euc_kr"
                elif "100" in specific_charset:
                    specific_charset = "latin1"
                elif "192" in specific_charset or "UTF-8" in specific_charset:
                    specific_charset = "utf-8"
                elif "ISO 2022 IR 87" in specific_charset:
                    specific_charset = "iso2022_jp"  # 일본어 Kanji 지원
                else:
                    specific_charset = "iso8859"

                # Patient's Name 디코딩 시도
                try:
                    raw_name = dicom_data[0x0010, 0x0010].value
                    if isinstance(raw_name, bytes):
                        patient_name = raw_name.decode(specific_charset)
                    else:
                        patient_name = raw_name
                    dicom_data.PatientName = patient_name
                except (UnicodeDecodeError, AttributeError):
                    print(f"Warning: Failed to decode Patient's Name with encoding {specific_charset}")
                    dicom_data.PatientName = "Unknown"

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
                    self.tabs.setCurrentIndex(0)

                # 기존 검색 필터 복원
                self.restoreFilters()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error reading DICOM file: {e}")
            return dicom_data

    def addTab(self, dicom_data, tag_type):
        table = QTableWidget()
        elements = []
        tag_values = {}  # (group, element) -> [(value, element)] 저장

        if tag_type == "All":
            if hasattr(dicom_data, "file_meta"):
                for element in dicom_data.file_meta:
                    tag_key = (element.tag.group, element.tag.element)
                    value = str(element.value) if element.value is not None else "None"
                    if tag_key not in tag_values:
                        tag_values[tag_key] = []
                    tag_values[tag_key].append((value, element))

        if dicom_data:
            for element in dicom_data.iterall():
                tag_key = (element.tag.group, element.tag.element)
                value = str(element.value) if element.value is not None else "None"
                if tag_key not in tag_values:
                    tag_values[tag_key] = []
                tag_values[tag_key].append((value, element))

            # 동일한 value는 첫 번째 element만 추가
            for tag_key, value_elements in tag_values.items():
                seen_values = set()
                for value, element in value_elements:
                    if value not in seen_values:
                        seen_values.add(value)
                        if element.name in ["PixelHeight", "PixelWidth"] and element.value == 0:
                            element.value = 1
                            print(f"Warning: Invalid value for {element.name}. Defaulting to 1.")
                        if tag_key == (0x7FE0, 0x0010):
                            self.pixel_data_value = np.copy(element.value)
                            display_value = "Encoded graphical image data"
                        if tag_type == "All":
                            elements.append(element)
                        elif tag_type == "Patient" and tag_key[0] == 0x0010:
                            elements.append(element)
                        elif tag_type == "Study/Series" and (
                            "Study" in element.name or "Series" in element.name
                        ):
                            elements.append(element)
                        elif tag_type == "Image" and (
                            tag_key[0] == 0x0028
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
                table.setItem(row, 5, QTableWidgetItem(str(display_value)))
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

    def copyValue(self, table):
        selected_row = table.currentRow()
        clipboard = QApplication.clipboard()
        row_data = []
        if selected_row >= 0:
            group_item = table.item(selected_row, 0)
            element_item = table.item(selected_row, 1)
            if (
                group_item
                and element_item
                and group_item.text().strip().upper() == "7FE0"
                and element_item.text().strip().upper() == "0010"
            ):
                row_data.append(np.array2string(self.pixel_data_value))
            else:
                item = table.item(selected_row, 5)
                if item:
                    row_data.append(item.text())
            clipboard.setText("\t".join(row_data))
        else:
            print("No row selected.")

    def copyAll(self):
        table = self.tabs.currentWidget()
        selected_row = table.currentRow()
        clipboard = QApplication.clipboard()
        row_data = []
        if selected_row >= 0:
            for col in range(table.columnCount()):
                item = table.item(selected_row, col)
                if item:  # '在外' 제거, 올바른 조건문
                    if (
                        col == 5
                        and table.item(selected_row, 0).text().strip().upper() == "7FE0"
                        and table.item(selected_row, 1).text().strip().upper() == "0010"
                    ):
                        row_data.append(
                            np.array2string(self.pixel_data_value)
                        )
                    else:
                        row_data.append(item.text())
            clipboard.setText("\t".join(row_data))
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
    app.setWindowIcon(QIcon("D:\\dicom_tag_loader\\tag.ico"))
    viewer = DicomTagLoader()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("D:\\github\\dicom\\tagLoader\\tag.ico"))
    viewer = DicomTagLoader()
    viewer.show()
    sys.exit(app.exec_())
