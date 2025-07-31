import sys
import json
import pandas as pd
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QPushButton, QFileDialog, QVBoxLayout, QWidget, QMessageBox
from PyQt5.QtCore import Qt

class JsonTableViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JSON Table Viewer")
        self.setGeometry(100, 100, 600, 1200)

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Create main widget and layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout()
        self.main_widget.setLayout(self.layout)

        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Object ID", "Value"])
        self.layout.addWidget(self.table)

        # Create buttons
        self.load_button = QPushButton("Load JSON")
        self.load_button.clicked.connect(self.load_json)
        self.layout.addWidget(self.load_button)

        self.export_button = QPushButton("Export to CSV")
        self.export_button.clicked.connect(self.export_to_csv)
        self.layout.addWidget(self.export_button)

        # Initialize data
        self.data = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files and files[0].endswith('.json'):
            self.process_json(files[0])

    def load_json(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open JSON File", "", "JSON Files (*.json)")
        if file_path:
            self.process_json(file_path)

    def process_json(self, file_path):
        try:
            with open(file_path, 'r') as file:
                json_data = json.load(file)

            # Extract data from inferences
            extracted_data = []
            for inference in json_data.get('inferences', []):
                for obj in inference.get('objects', []):
                    extracted_data.append({
                        'objectid': obj['objectid'],
                        'volumediameter': obj['text']['volumediameter'],
                        'value': f"{obj['text']['volumediameter']}/{obj['text']['volumesize']}"
                    })

            # Sort by volumediameter in descending order
            extracted_data.sort(key=lambda x: x['volumediameter'], reverse=True)

            # Create DataFrame with empty rows
            display_data = []
            for i, item in enumerate(extracted_data):
                display_data.append({'Object ID': str(item['objectid']), 'Value': item['value']})
                if i < len(extracted_data) - 1:
                    display_data.append({'Object ID': '', 'Value': ''})

            self.data = pd.DataFrame(display_data)

            # Update table
            self.table.setRowCount(len(display_data))
            for row, item in enumerate(display_data):
                self.table.setItem(row, 0, QTableWidgetItem(item['Object ID']))
                self.table.setItem(row, 1, QTableWidgetItem(item['Value']))

            self.table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load JSON: {str(e)}")

    def export_to_csv(self):
        if self.data is None:
            QMessageBox.warning(self, "Warning", "No data to export")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV File", "", "CSV Files (*.csv)")
        if file_path:
            try:
                self.data.to_csv(file_path, index=False)
                QMessageBox.information(self, "Success", "Data exported successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export CSV: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JsonTableViewer()
    window.show()
    sys.exit(app.exec_())
