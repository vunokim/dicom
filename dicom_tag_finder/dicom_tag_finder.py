import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                             QLabel, QLineEdit, QPushButton, QRadioButton, QCheckBox,
                             QTextEdit, QGroupBox, QButtonGroup, QMessageBox)
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import (QRegExpValidator, QIcon)
import pydicom
import glob
from collections import defaultdict


class DICOMTagSearcher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DICOM 태그 정밀 검색기")
        self.setGeometry(100, 100, 1000, 900)

        self.dicom_index = defaultdict(list)  # tag: [file_paths]
        self.dicom_tag_values = defaultdict(dict)  # file_path: {tag: value}
        self.all_dicom_files = []
        self.tag_widgets = []  # (widget, group_edit, elem_edit, value_edit)

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 검색 경로
        path_group = QGroupBox("검색 경로")
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("예: C:/DICOM_DATA")
        self.index_btn = QPushButton("검색 시작")
        self.index_btn.clicked.connect(self.index_dicom_files)
        self.subdir_cb = QCheckBox("하위 폴더 포함")
        self.subdir_cb.setChecked(True)
        path_layout.addWidget(QLabel("경로:"))
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.index_btn)
        path_layout.addWidget(self.subdir_cb)
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)

        # 태그 입력 그룹
        self.tag_group = QGroupBox("태그 입력 (Group, Element, Value)")
        self.tag_layout = QVBoxLayout()
        self.add_tag_row()  # 첫 번째 행
        self.tag_group.setLayout(self.tag_layout)
        layout.addWidget(self.tag_group)

        # AND / OR
        logic_group = QGroupBox("검색 로직")
        logic_layout = QHBoxLayout()
        self.logic_group = QButtonGroup()
        self.and_radio = QRadioButton("AND (모든 조건 만족)")
        self.and_radio.setChecked(True)
        self.or_radio = QRadioButton("OR (하나 이상 만족)")
        self.logic_group.addButton(self.and_radio)
        self.logic_group.addButton(self.or_radio)
        logic_layout.addWidget(self.and_radio)
        logic_layout.addWidget(self.or_radio)
        logic_group.setLayout(logic_layout)
        layout.addWidget(logic_group)

        # 결과 출력
        self.result_text = QTextEdit()
        self.result_text.setPlaceholderText("검색 결과가 여기에 표시됩니다...")
        layout.addWidget(self.result_text)

    def add_tag_row(self):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        # Group ID
        group_edit = QLineEdit()
        group_edit.setPlaceholderText("0010")
        group_edit.setMaxLength(4)
        group_edit.setFixedWidth(60)  # 4자 고정

        # Element ID
        elem_edit = QLineEdit()
        elem_edit.setPlaceholderText("0010")
        elem_edit.setMaxLength(4)
        elem_edit.setFixedWidth(60)

        # Value 입력 박스 (가변 너비)
        value_edit = QLineEdit()
        value_edit.setPlaceholderText("값 (비워두면 Tag 존재 여부만 체크)")

        # 16진수 제한 (Group, Element)
        hex_validator = QRegExpValidator(QRegExp("[0-9A-Fa-f]*"))
        group_edit.setValidator(hex_validator)
        elem_edit.setValidator(hex_validator)

        # + / - 버튼 (반으로 줄임)
        plus_btn = QPushButton("+")
        plus_btn.setFixedWidth(30)
        plus_btn.clicked.connect(self.add_tag_row)
        minus_btn = QPushButton("-")
        minus_btn.setFixedWidth(30)
        minus_btn.clicked.connect(lambda: self.remove_tag_row(row_widget))

        # 레이아웃 배치
        row_layout.addWidget(QLabel("Group:"))
        row_layout.addWidget(group_edit)
        row_layout.addWidget(QLabel("Element:"))
        row_layout.addWidget(elem_edit)
        row_layout.addWidget(QLabel("Value:"))
        row_layout.addWidget(value_edit, 1)  # 남은 공간 모두 사용
        row_layout.addWidget(plus_btn)
        row_layout.addWidget(minus_btn)

        self.tag_layout.addWidget(row_widget)
        self.tag_widgets.append((row_widget, group_edit, elem_edit, value_edit))

    def remove_tag_row(self, widget):
        if len(self.tag_widgets) <= 1:
            QMessageBox.warning(self, "경고", "최소 1개의 태그 입력은 유지해야 합니다.")
            return
        for i, (w, _, _, _) in enumerate(self.tag_widgets):
            if w == widget:
                self.tag_layout.removeWidget(w)
                w.deleteLater()
                self.tag_widgets.pop(i)
                break

    def index_dicom_files(self):
        search_path = self.path_input.text().strip()

        # 1️⃣ 태그 유효성 검사 (가장 먼저)
        if not self.has_valid_tag_condition():
            QMessageBox.warning(
                self,
                "경고",
                "태그 ID를 입력한 후 검색을 실행하세요."
            )
            return

        # 2️⃣ 검색 경로 유효성 검사
        if not search_path or not os.path.exists(search_path):
            QMessageBox.warning(self, "경고", "유효한 검색 경로를 입력하세요.")
            return

        pattern = os.path.join(search_path, "**/*.dcm" if self.subdir_cb.isChecked() else "*.dcm")
        files = glob.glob(pattern, recursive=self.subdir_cb.isChecked())

        if not files:
            QMessageBox.information(self, "정보", "DICOM 파일을 찾을 수 없습니다.")
            return

        self.dicom_index.clear()
        self.dicom_tag_values.clear()
        self.all_dicom_files = files

        for file_path in files:
            try:
                ds = pydicom.dcmread(file_path, stop_before_pixels=True)
                file_tags = {}
                for elem in ds:
                    tag = elem.tag
                    full_tag = f"{tag.group:04X},{tag.element:04X}"
                    file_tags[full_tag] = str(elem.value) if elem.value is not None else ""
                    self.dicom_index[full_tag].append(file_path)
                self.dicom_tag_values[file_path] = file_tags
            except Exception as e:
                print(f"읽기 실패 {file_path}: {e}")

        # 팝업 후 자동 검색 실행
        QMessageBox.information(
            self, "인덱싱 완료",
            f"{len(files)}개 DICOM 파일 인덱싱 완료!"
        )

        # ✅ 태그가 있을 때만 자동 검색
        if self.has_valid_tag_condition():
            self.search_and_display()

    def has_valid_tag_condition(self):
        for _, group_edit, elem_edit, _ in self.tag_widgets:
            g = group_edit.text().strip()
            e = elem_edit.text().strip()
            if g and e and len(g) == 4 and len(e) == 4:
                return True
        return False

    def value_matches(self, stored_value, query_value):
        """
        SQL LIKE 스타일 비교
        *1234  → endswith
        1234*  → startswith
        *1234* → contains
        1234   → exact match
        """
        if not query_value:
            return True

        if query_value.startswith("*") and query_value.endswith("*"):
            return query_value.strip("*") in stored_value

        if query_value.startswith("*"):
            return stored_value.endswith(query_value.lstrip("*"))

        if query_value.endswith("*"):
            return stored_value.startswith(query_value.rstrip("*"))

        return stored_value == query_value

    def search_and_display(self):
        conditions = []
        for _, group_edit, elem_edit, value_edit in self.tag_widgets:
            g = group_edit.text().strip().upper()
            e = elem_edit.text().strip().upper()
            v = value_edit.text().strip()
            if g and e and len(g) == 4 and len(e) == 4:
                conditions.append((f"{g},{e}", v))

        if not conditions:
            QMessageBox.warning(self, "경고", "유효한 태그를 입력하세요 (4자리 16진수).")
            return

        is_and = self.and_radio.isChecked()
        if is_and:
            results = set(self.all_dicom_files)
        else:
            results = set()

        for tag, value in conditions:
            matching_files = set()
            for file_path in self.dicom_index.get(tag, []):
                file_tags = self.dicom_tag_values.get(file_path, {})
                stored_value = file_tags.get(tag, "")
                if value:
                    if self.value_matches(stored_value, value):
                        matching_files.add(file_path)
                else:
                    matching_files.add(file_path)

            if is_and:
                results = results.intersection(matching_files)
            else:
                results = results.union(matching_files)
            if not results:
                break

        # 결과 출력
        txt = "=== DICOM 태그 정밀 검색 결과 ===\n"
        txt += f"조건: {', '.join([f'{t}={v}' if v else t for t, v in conditions])}\n"
        txt += f"로직: {'AND' if is_and else 'OR'}\n"
        txt += f"총 {len(results)}개 파일\n\n"
        for f in sorted(results):
            txt += f"{f}\n"

        self.result_text.setText(txt)

        # 자동 저장
        if results:
            save_path = "dicom_search_results.txt"
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(txt)
            QMessageBox.information(self, "저장 완료", f"결과가 '{save_path}'에 저장되었습니다.")
        else:
            QMessageBox.information(self, "결과 없음", "조건에 맞는 파일이 없습니다.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("D:\github\\dicom\\dicom_tag_finder\\searcher.ico"))
    window = DICOMTagSearcher()
    window.show()
    sys.exit(app.exec_())
