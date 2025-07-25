import sys
import os
import csv
import json
import re
import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import pydicom
from pydicom.tag import Tag
from pydicom.datadict import add_private_dict_entries

# DICOM 사전 확장 함수
def extend_dicom_dictionary():
    private_dict = {
        'VUNO Private Tags': {
            (0x1001, 0x1002): ('CS', 'Private Version', '1', '', 'VUNO Private Tags'),
            (0x1001, 0x1004): ('CS', 'Private Flag 0/1', '1', '', 'VUNO Private Tags'),
            (0x1001, 0x1005): ('CS', 'Private Flag 1', '1', '', 'VUNO Private Tags'),
            (0x1001, 0x1008): ('UT', 'Private Report', '1', '', 'VUNO Private Tags'),
            (0x1001, 0x1009): ('CS', 'Private Type', '1', '', 'VUNO Private Tags'),
            (0x1001, 0x1011): ('UT', 'Private Report/RADS', '1', '', 'VUNO Private Tags'),
            (0x1001, 0x1015): ('UT', 'Private JSON', '1', '', 'VUNO Private Tags'),
        }
    }
    for block_name, tags in private_dict.items():
        tag_dict = {}
        for tag_tuple, (vr, name, vm, is_retired, owner) in tags.items():
            tag_int = (tag_tuple[0] << 16) | tag_tuple[1]
            tag_dict[tag_int] = (vr, name, vm, is_retired, owner)
        add_private_dict_entries(block_name, tag_dict)

def is_valid_date(value):
    if not value or not isinstance(value, str):
        return False
    try:
        datetime.datetime.strptime(value, "%Y%m%d")
        return True
    except ValueError:
        return False

def is_valid_time(value):
    if not value or not isinstance(value, str):
        return False
    return bool(re.match(r"^[0-2][0-9][0-5][0-9][0-5][0-9]$", value))

def status_color(ok):
    return QColor("#a8f28a") if ok else QColor("#f28a8c")

def alternate_row_color(row):
    return QColor("#FBFAFB") if row % 2 == 0 else QColor("#FFFFFF")

class TagStatusEvaluator:
    SERIES_MAP = {
        "900010": "SC", "900090": "GSPS", "900070": "SC Report",
        "900071": "T1+T2 or BA환자용", "900072": "T1 or BA의사용",
        "900073": "T2", "900080": "Encap. PDF Report"
    }

    MODEL_MAP = {
        "VN-M-01": "BA", "VN-M-02": "CXR", "VN-M-03": "FAI", "VN-M-04": "LCT",
        "VN-M-06": "DB", "VN-M-07": "DB AD", "VN-M-30": "CXR Triage", "VN-M-31": "CXR Assist"
    }

    @classmethod
    def evaluate_series_uid(cls, value):
        if not value or not isinstance(value, str):
            return False, "Fail, study, Encap. PDF Report"
        parts = value.split(".")
        if len(parts) < 6 or parts[:4] != ["1", "2", "410", "200123"]:
            return False, "Fail, study, Encap. PDF Report"
        version, level, snum, unixtime, randno = parts[4:9] if len(parts) >= 9 else parts[4:6] + [""] * (9 - len(parts[4:]))
        level_valid = level in ["1", "2", "3"]
        snum_valid = snum in cls.SERIES_MAP
        randno_valid = randno.isdigit() and 1 <= int(randno) <= 32767
        if level_valid and snum_valid and randno_valid:
            level_txt = {"1": "study", "2": "series", "3": "instance SOP"}[level]
            series_txt = cls.SERIES_MAP[snum]
            return True, f"OK, {level_txt}, {series_txt}"
        else:
            level_txt = {"1": "study", "2": "series", "3": "instance SOP"}.get(level, "study")
            series_txt = cls.SERIES_MAP.get(snum, "Encap. PDF Report")
            return False, f"Fail, {level_txt}, {series_txt}"

    @classmethod
    def evaluate_sop_instance_uid(cls, value):
        if not value or not isinstance(value, str):
            return False, "Fail, study, Encap. PDF Report"
        parts = value.split(".")
        if len(parts) >= 10 and parts[:5] == ["1", "2", "410", "200123", "100"]:
            level, snum, unixtime, randno, instance_num = parts[5:10] if len(parts) >= 10 else parts[5:6] + [""] * 5
            level_valid = level in ["1", "2", "3"]
            snum_valid = snum in cls.SERIES_MAP
            randno_valid = randno.isdigit() and 1 <= int(randno) <= 32767
            instance_valid = instance_num.isdigit()
            if level_valid and snum_valid and randno_valid and instance_valid:
                level_txt = {"1": "study", "2": "series", "3": "instance SOP"}[level]
                series_txt = cls.SERIES_MAP[snum]
                return True, f"OK, {level_txt}, {series_txt}"
            else:
                level_txt = {"1": "study", "2": "series", "3": "instance SOP"}.get(level, "study")
                series_txt = cls.SERIES_MAP.get(snum, "Encap. PDF Report")
                return False, f"Fail, {level_txt}, {series_txt}"
        return False, "Fail, study, Encap. PDF Report"

    @classmethod
    def evaluate_date(cls, value):
        return is_valid_date(value), "OK" if is_valid_date(value) else "Fail"

    @classmethod
    def evaluate_time(cls, value):
        return is_valid_time(value), "OK" if is_valid_time(value) else "Fail"

    @classmethod
    def evaluate_series_number(cls, value):
        if not value:
            return False, "Fail"
        return value in cls.SERIES_MAP, cls.SERIES_MAP.get(value, "Fail")

    @classmethod
    def evaluate_fixed_value(cls, value, expected):
        return value == expected, "OK" if value == expected else "Fail"

    @classmethod
    def evaluate_model_name(cls, value):
        if not value:
            return False, value or "Fail"
        return value in cls.MODEL_MAP, cls.MODEL_MAP.get(value, value)

    @classmethod
    def evaluate_version(cls, value):
        if not value or not isinstance(value, str):
            return False, "Fail"
        return bool(re.search(r"\d+\.\d+\.\d+", value)), "OK" if re.search(r"\d+\.\d+\.\d+", value) else "Fail"

    @classmethod
    def evaluate_instance_number(cls, value):
        if not value or not isinstance(value, str):
            return False, "Fail"
        suffix = str(value)
        if suffix.endswith("00001"):
            return True, "GSPS"
        elif suffix.endswith("0001"):
            return True, "Encap.PDF Report"
        elif suffix.endswith("001"):
            return True, "SC Report"
        elif suffix.endswith("01"):
            return True, "SC"
        return False, "Fail"

    @classmethod
    def evaluate_private_1009(cls, model, value):
        if not value or not model:
            return False, "Fail"
        model = str(model).strip().encode().decode(errors="ignore") if isinstance(model, bytes) else model.strip()
        value = str(value).strip()
        valid_models = {"VN-M-01", "VN-M-03", "VN-M-04", "VN-M-06", "VN-M-07", "VN-M-30", "VN-M-31"}
        if model == "VN-M-02" and value == "3":
            return True, "OK"
        elif model in valid_models and value == "2":
            return True, "OK"
        return False, "Fail"

    @classmethod
    def evaluate_private_json_prefix(cls, value, prefix_list):
        if not value or not isinstance(value, str):
            return False, "Fail"
        return any(value.startswith(p) for p in prefix_list), "OK" if any(value.startswith(p) for p in prefix_list) else "Fail"

    @classmethod
    def evaluate_json(cls, value, model):
        if model == "VN-M-31" and not value:
            return True, "OK"
        if not value or not isinstance(value, str):
            return False, "Fail"
        try:
            json.loads(value)
            return True, "OK"
        except json.JSONDecodeError:
            return False, "Fail"

class TagCheckerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1520, 1000)
        self.setAcceptDrops(True)

        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.layout = QVBoxLayout(self.central)

        self.file_label = QLabel("No file loaded")
        self.load_button = QPushButton("Open DICOM")
        self.export_button = QPushButton("Export CSV")

        hbox = QHBoxLayout()
        hbox.addWidget(self.file_label)
        hbox.addStretch()
        hbox.addWidget(self.load_button)
        hbox.addWidget(self.export_button)

        self.layout.addLayout(hbox)

        self.table = QTableWidget()
        self.layout.addWidget(self.table)

        self.load_button.clicked.connect(self.load_dicom)
        self.export_button.clicked.connect(self.export_csv)
        self.tags = []
        self.setWindowTitle("Tag Checker - No file loaded")  # 초기 제목 설정

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            file_url = event.mimeData().urls()[0]
            filepath = file_url.toLocalFile()
            self.load_dicom_from_path(filepath)

    def load_dicom(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open DICOM", "", "DICOM files (*.dcm)")
        if path:
            self.load_dicom_from_path(path)

    def load_dicom_from_path(self, path):
        filename = os.path.basename(path)
        self.file_label.setText(filename)
        self.setWindowTitle(f"Tag Checker - {filename}")
        try:
            ds = pydicom.dcmread(path, force=True)
            self.tags = self.extract_tags(ds)
            self.populate_table()
        except Exception as e:
            self.file_label.setText(f"Error loading DICOM: {str(e)}")
            self.tags = []
            self.populate_table()

    def extract_tags(self, ds):
        tags = []
        def add(tag, desc, value, ok, status):
            tags.append({
                "group": f"{tag.group:04X}", "element": f"{tag.element:04X}",
                "desc": desc, "value": value, "ok": ok, "status": status
            })

        model = str(ds.get(Tag(0x0008, 0x1090), "").value).strip() if (0x0008, 0x1090) in ds and ds[0x0008, 0x1090].value else ""

        tag_map = [
            (Tag(0x0020, 0x000E), "Series Instance UID", TagStatusEvaluator.evaluate_series_uid),
            (Tag(0x0008, 0x0021), "Series Date", TagStatusEvaluator.evaluate_date),
            (Tag(0x0020, 0x0011), "Series Number", TagStatusEvaluator.evaluate_series_number),
            (Tag(0x0008, 0x0064), "Conversion Type", lambda v: TagStatusEvaluator.evaluate_fixed_value(v, "WSD")),
            (Tag(0x0008, 0x0070), "Manufacturer", lambda v: TagStatusEvaluator.evaluate_fixed_value(v, "VUNO")),
            (Tag(0x0008, 0x1090), "Manufacturer's Model Name", TagStatusEvaluator.evaluate_model_name),
            (Tag(0x0018, 0x1020), "Software Versions", TagStatusEvaluator.evaluate_version),
            (Tag(0x0008, 0x0012), "Instance Creation Date", TagStatusEvaluator.evaluate_date),
            (Tag(0x0008, 0x0013), "Instance Creation Time", TagStatusEvaluator.evaluate_time),
            (Tag(0x0008, 0x0018), "SOP Instance UID", TagStatusEvaluator.evaluate_sop_instance_uid),
            (Tag(0x0020, 0x0013), "Instance Number", TagStatusEvaluator.evaluate_instance_number),
            (Tag(0x0020, 0x4000), "Image Comments", lambda v: (bool(v), "OK" if v else "Fail"))
        ]

        private_tag_map = [
            (Tag(0x1001, 0x1002), "Private Version", TagStatusEvaluator.evaluate_version),
            (Tag(0x1001, 0x1004), "Private Flag 0/1", lambda v: (v in ["0", "1"], "OK" if v in ["0", "1"] else "Fail")),
            (Tag(0x1001, 0x1005), "Private Flag 1", lambda v: (v == "1", "OK" if v == "1" else "Fail")),
            (Tag(0x1001, 0x1008), "Private Report", lambda v: TagStatusEvaluator.evaluate_private_json_prefix(v, ['{"report":"'])),
            (Tag(0x1001, 0x1009), "Private Type", lambda v: TagStatusEvaluator.evaluate_private_1009(model, v)),
            (Tag(0x1001, 0x1011), "Private Report/RADS", lambda v: TagStatusEvaluator.evaluate_private_json_prefix(v, ['{"result":"', '{"case_lung_RADS":"'])),
            (Tag(0x1001, 0x1015), "Private JSON", lambda v: TagStatusEvaluator.evaluate_json(v, model)),
        ]

        for tag, desc, fn in tag_map:
            try:
                if tag in ds:
                    value = ds[tag].value
                    val = str(value) if not isinstance(value, bytes) else value.decode(errors="ignore")
                    ok, status = fn(val)
                    add(tag, desc, val, ok, status)
                else:
                    add(tag, desc, "", False, "Fail")
            except Exception:
                add(tag, desc, "ERROR", False, "Fail")

        for tag, desc, fn in private_tag_map:
            try:
                if tag in ds:
                    element = ds[tag]
                    if isinstance(element.value, pydicom.multival.MultiValue) or isinstance(element.value, pydicom.sequence.Sequence):
                        for val in element.value:
                            str_val = str(val) if not isinstance(val, bytes) else val.decode(errors="ignore")
                            ok, status = fn(str_val)
                            add(tag, desc, str_val, ok, status)
                    else:
                        value = element.value
                        val = str(value) if not isinstance(value, bytes) else value.decode(errors="ignore")
                        ok, status = fn(val)
                        add(tag, desc, val, ok, status)
                else:
                    add(tag, desc, "", False, "Fail")
            except Exception:
                add(tag, desc, "ERROR", False, "Fail")

        return tags

    def populate_table(self):
        self.table.clear()
        self.table.setRowCount(len(self.tags))
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["GroupID", "ElementID", "Description", "Value", "Status"])
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 60)
        self.table.setColumnWidth(2, 300)
        self.table.setColumnWidth(3, 800)
        self.table.setColumnWidth(4, 300)

        for row, tag in enumerate(sorted(self.tags, key=lambda x: (int(x["group"], 16), int(x["element"], 16)))):
            for col, key in enumerate(["group", "element", "desc", "value", "status"]):
                item = QTableWidgetItem(tag[key])
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                if key == "status":
                    item.setBackground(status_color(tag["ok"]))
                else:
                    item.setBackground(alternate_row_color(row))
                self.table.setItem(row, col, item)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

    def export_csv(self):
        if not self.tags:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV files (*.csv)")
        if not path:
            return
        with open(path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["GroupID", "ElementID", "Description", "Value", "Status"])
            for tag in sorted(self.tags, key=lambda x: (int(x["group"], 16), int(x["element"], 16))):
                writer.writerow([tag["group"], tag["element"], tag["desc"], tag["value"], tag["status"]])

if __name__ == "__main__":
    extend_dicom_dictionary()
    app = QApplication(sys.argv)
    window = TagCheckerApp()
    app.setWindowIcon(QIcon("D:\\github\\dicom\\tag_checker\\checker.ico"))
    window.show()
    sys.exit(app.exec_())
