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
from PyQt5.QtGui import QIcon  # QIcon 임포트
import numpy as np
from pydicom.misc import is_dicom  # DICOM 파일 확인 함수


class DicomTagLoader(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.pixel_data_value = None  # Store the actual Pixel Data value here
        self.current_filters = {
            "group": "",
            "element": "",
            "description": "",
        }  # 🔹 추가된 필터 저장 변수

    def initUI(self):
        self.setWindowTitle("DICOM Tag Loader")
        self.setGeometry(
            100, 100, 960, 730
        )  # 창 위치 모니터 좌상단으로부터 가로/세로 100px, 창 크기 900px*700px
        self.setAcceptDrops(True)  # Enable drag & drop
        layout = QVBoxLayout()

        # File Open 버튼 및 File path 표시 레이블 가로 레이아웃
        h_layout = QHBoxLayout()
        # File Open 버튼
        self.open_button = QPushButton("File Open", self)
        self.open_button.setFixedWidth(100)
        self.open_button.clicked.connect(self.openFile)
        h_layout.addWidget(self.open_button)

        # File path 뿌려주는 라벨
        self.file_path = QLabel("File path will appear here")
        h_layout.addWidget(self.file_path)
        layout.addLayout(h_layout)

        # 검색 및 버튼 Layout 설정
        function_layout = QHBoxLayout()

        # 검색 입력 레이아웃 추가
        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("Group")
        self.group_input.setFixedWidth(60)
        self.group_input.setValidator(QIntValidator(0, 9999))  # 4자리 숫자만 입력 가능

        self.element_input = QLineEdit()
        self.element_input.setPlaceholderText("Element")
        self.element_input.setFixedWidth(60)
        self.element_input.setValidator(QIntValidator(0, 9999))

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Description")
        self.description_input.setFixedWidth(200)

        # 초기화 버튼 (X 버튼)
        self.clear_button = QPushButton("X")
        self.clear_button.setFixedWidth(20)
        self.clear_button.clicked.connect(self.clearSearchFields)

        # 입력 필드 및 버튼 배치
        function_layout.addWidget(self.group_input)
        function_layout.addWidget(self.element_input)
        function_layout.addWidget(self.description_input)
        function_layout.addWidget(self.clear_button)
        function_layout.addStretch()

        # 스페이서 추가하여 좌우 공간을 분리
        function_layout.addSpacerItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )

        # All Copy, Value Copy 버튼
        self.copy_all_button = QPushButton("All Copy", self)
        self.copy_all_button.setFixedWidth(75)
        self.copy_value_button = QPushButton("Value Copy", self)
        self.copy_value_button.setFixedWidth(95)

        self.copy_all_button.clicked.connect(self.copyAll)
        self.copy_value_button.clicked.connect(
            lambda: self.copyValue(self.tabs.currentWidget())
        )

        # 우측 영역에 버튼 추가
        function_layout.addStretch()  # 오른쪽에 버튼과 여유 두기
        function_layout.addWidget(self.copy_all_button)
        function_layout.addWidget(self.copy_value_button)
        layout.addLayout(function_layout)

        # Tabs for DICOM tags
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # 최초 실행 시 탭 모두 비워두기, 처음에는 파일을 로드해야만 탭이 나왔음
        # 최초 실행 시 부터 탭을 나오게 하고, 그 탭을 비워두는 역할
        self.initEmptyTabs()

        # 검색 입력 필드 이벤트 연결 (모든 탭에 동일한 검색어를 적용)
        self.group_input.textChanged.connect(self.filterTable)
        self.element_input.textChanged.connect(self.filterTable)
        self.description_input.textChanged.connect(self.filterTable)

    def initEmptyTabs(self):
        # 처음엔 더미 데이터 채워서 나오게 해서 비워두게 함
        self.addTab(None, "All")
        self.addTab(None, "Patient")
        self.addTab(None, "Study/Series")
        self.addTab(None, "Image")

    def openFile(self, filepath=None):
        # File Open 창
        if not filepath:
            file_dialog = QFileDialog.getOpenFileName(
                self, "Open DICOM File", "", "DICOM Files (*.dcm)"
            )
            filepath = file_dialog[0]
        if filepath:
            # 불러오면 file path 갱신
            self.file_path.setText(filepath)
            try:
                # 확장자와 상관없이 파일이 DICOM인지 확인
                if not is_dicom(filepath):
                    QMessageBox.critical(
                        self, "Error", "The selected file is not a valid DICOM file."
                    )
                    return
                # DICOM file 읽기, force=True안하니까 계속 0002와 같은 meta data는 안불러옴
                dicom_data = pydicom.dcmread(filepath, force=True)
                # Dicom file 다른 거 다시 읽어오면 보고 있던 tag 정보는 클리어
                self.tabs.clear()

                # Specific Character Set 설정
                specific_charset = dicom_data.get("SpecificCharacterSet", "ISO_IR 100")

                # 리스트인 경우 첫 번째 값만 사용
                if isinstance(specific_charset, list):
                    specific_charset = (
                        specific_charset[0] if specific_charset else "ISO_IR 100"
                    )

                # 앞에 '\'가 있으면 제거
                if isinstance(specific_charset, str):
                    specific_charset = specific_charset.lstrip("\\")

                # 특정 패턴이 포함된 경우 인코딩 매핑
                if "149" in specific_charset:  # ISO_IR 149, ISO 2022 IR 149 등 포함
                    specific_charset = "euc_kr"
                elif "100" in specific_charset:  # ISO_IR 100
                    specific_charset = "latin1"
                elif "192" in specific_charset or "UTF-8" in specific_charset:
                    specific_charset = "utf-8"
                else:
                    specific_charset = "iso8859"

                # Patient's Name 디코딩 시도
                try:
                    raw_name = dicom_data[0x00100010].value
                    if isinstance(raw_name, bytes):  # 바이트 데이터일 경우만 디코딩
                        patient_name = raw_name.decode(specific_charset)
                    else:
                        patient_name = raw_name
                    dicom_data.PatientName = patient_name
                except (UnicodeDecodeError, AttributeError):
                    print(
                        f"Warning: Failed to decode Patient's Name with encoding {specific_charset}"
                    )
                    dicom_data.PatientName = "Unknown"

                # Pixel Data value 리셋
                self.pixel_data_value = None
                # Tab을 All, Patient, Study/Series, Image 탭으로 구분함
                self.addTab(dicom_data, "All")
                self.addTab(dicom_data, "Patient")
                self.addTab(dicom_data, "Study/Series")
                self.addTab(dicom_data, "Image")

                # 새로운 파일을 로드한 후 기존 검색어로 필터링 적용
                self.restoreFilters()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error reading DICOM file: {e}")

            return dicom_data

    def addTab(self, dicom_data, tag_type):
        table = QTableWidget()
        elements = []

        # Meta 정보 tag도 All 탭에는 읽어서 나오게 함. 이렇게 안하면 meta 정보는 빠지고 나옴
        if tag_type == "All":
            if hasattr(dicom_data, "file_meta"):
                for element in dicom_data.file_meta:
                    elements.append(element)

        # 여기서부터는 각 탭별 나오게 하는 tag들을 구분
        if dicom_data:
            seen_tags = set()  # 중복을 방지하기 위한 Set

            for element in dicom_data.iterall():  # 모든 태그 포함 (Standard + Private)
                tag_key = (
                    element.tag.group,
                    element.tag.element,
                )  # (Group, Element) 튜플 생성

                if tag_key not in seen_tags:  # 중복 체크
                    seen_tags.add(tag_key)  # 새로운 태그 추가

                    # PixelHeight, PixelWidth 값이 0이면 경고 출력 후 1로 변경
                    if (
                        element.name in ["PixelHeight", "PixelWidth"]
                        and element.value == 0
                    ):
                        element.value = 1  # 값이 0이면 기본값 1로 설정
                        print(
                            f"Warning: Invalid value for {element.name}. Defaulting to 1."
                        )
                    # Group 7FE0, Element 0010는 Pixel Data인데 바이너리 값이라 너무 큼
                    if element.tag.group == 0x7FE0 and element.tag.element == 0x0010:
                        # NumPy array 에 실제 pixel data값을 담고
                        self.pixel_data_value = np.copy(element.value)
                        # tag 리스트에 뿌려주는 것은 Encoded graphical image data로 뿌려줌. 이래야 안느려짐
                        display_value = "Encoded graphical image data"
                    # 탭 별 보여줄 필터
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

        # 정렬 안하니 중구난방으로 나와서 tag Group+Element별 정렬
        elements.sort(key=lambda x: (x.tag.group, x.tag.element))

        # Tag 리스트 속성 설정
        table.setRowCount(len(elements))
        table.setColumnCount(6)  # Number of columns
        table.setHorizontalHeaderLabels(
            ["Group", "Element", "Description", "VR", "Size", "Value"]
        )

        # 열 별로 지정안하니 너비가 다 똑같이 나와 보기 싫어 너비 배분, 마지막 Value는 나머지 값 다
        table.setColumnWidth(0, 55)  # Group
        table.setColumnWidth(1, 55)  # Element
        table.setColumnWidth(2, 230)  # Description
        table.setColumnWidth(3, 25)  # VR
        table.setColumnWidth(4, 30)  # Size
        # 열 너비 조정이 안되길래 조정되게 해달라고 해서 GPT한테서 받은 코드
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)

        # 정렬된 요소로 tag 리스트 채우기
        for row, element in enumerate(elements):
            table.setItem(row, 0, QTableWidgetItem(f"{element.tag.group:04X}"))
            table.setItem(row, 1, QTableWidgetItem(f"{element.tag.element:04X}"))
            table.setItem(row, 2, QTableWidgetItem(element.name))
            table.setItem(row, 3, QTableWidgetItem(element.VR))
            size = len(str(element.value)) if element.value else 0
            table.setItem(row, 4, QTableWidgetItem(str(size)))
            # 0010,0010 Patient's Name은 캐릭터셋으로 디코딩한 것으로 표시
            if element.tag.group == 0x0010 and element.tag.element == 0x0010:
                table.setItem(row, 5, QTableWidgetItem(str(dicom_data.PatientName)))
            # 7EF0,0010 tag값을 표시는 Encoded graphical image data로 하고 실제 바이너리 값은 담고 있음
            elif element.tag.group == 0x7FE0 and element.tag.element == 0x0010:
                table.setItem(row, 5, QTableWidgetItem(str(display_value)))
            else:
                table.setItem(row, 5, QTableWidgetItem(str(element.value)))

            # 짝수 행에 배경색 추가
            if row % 2 == 0:
                for col in range(table.columnCount()):
                    item = table.item(row, col)
                    if item:
                        item.setBackground(
                            QColor(0xFB, 0xFA, 0xFB)
                        )  # 짝수 행 배경색 설정

        # 탭 추가
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
                # 파일이 실제 DICOM 파일인지 확인
                if not is_dicom(filepath):
                    QMessageBox.warning(
                        self, "Error", "The dropped file is not a valid DICOM file."
                    )
                    return

                # DICOM 파일 로드
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
            # 버튼 클릭했는데 그 행이 (7FE0,0010)이면 보이는 값이 아니라 실제 값 복사하도록 if함
            if (
                group_item
                and element_item
                and group_item.text().strip().upper() == "7FE0"
                and element_item.text().strip().upper() == "0010"
            ):
                # self.pixel_data_value에 저장된 실제 픽셀 데이터 복사
                row_data.append(np.array2string(self.pixel_data_value))  # 실제 값 사용
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
                if item:
                    if (
                        col == 5
                        and table.item(selected_row, 0).text().strip().upper() == "7FE0"
                        and table.item(selected_row, 1).text().strip().upper() == "0010"
                    ):
                        row_data.append(
                            np.array2string(self.pixel_data_value)
                        )  # 실제 값 사용
                    else:
                        row_data.append(item.text())
            clipboard.setText("\t".join(row_data))
        else:
            print("No row selected.")

    # 필터링 함수
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
        """기존 검색 필터를 유지하면서 새로운 파일을 로드"""
        self.group_input.setText(self.current_filters["group"])
        self.element_input.setText(self.current_filters["element"])
        self.description_input.setText(self.current_filters["description"])
        self.filterTable()

    # 검색 초기화 함수
    def clearSearchFields(self):
        self.group_input.clear()
        self.element_input.clear()
        self.description_input.clear()
        self.filterTable()  # 모든 행을 보이도록 업데이트


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 애플리케이션 아이콘 설정
    app.setWindowIcon(QIcon("D:\\dicom_tag_loader\\tag.ico"))
    viewer = DicomTagLoader()
    viewer.show()
    sys.exit(app.exec_())
