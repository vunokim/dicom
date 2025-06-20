import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pydicom
from pydicom.tag import Tag
from pydicom.dataelem import DataElement

VR_OPTIONS = [
    "Same", "AE", "AS", "AT", "CS", "DA", "DS", "DT", "FL", "FD", "IS", "LO", "LT",
    "OB", "OD", "OF", "OW", "PN", "SH", "SL", "SQ", "SS", "ST", "TM", "UI",
    "UL", "UN", "US", "UT"
]

# VR 전체 이름 매핑 (툴팁용)
VR_LABELS = {
    "AE": "Application Entity",
    "AS": "Age String",
    "AT": "Attribute Tag",
    "CS": "Code String",
    "DA": "Date",
    "DS": "Decimal String",
    "DT": "Date Time",
    "FL": "Floating Point Single",
    "FD": "Floating Point Double",
    "IS": "Integer String",
    "LO": "Long String",
    "LT": "Long Text",
    "OB": "Other Byte",
    "OD": "Other Double",
    "OF": "Other Float",
    "OW": "Other Word",
    "PN": "Person Name",
    "SH": "Short String",
    "SL": "Signed Long",
    "SQ": "Sequence of Items",
    "SS": "Signed Short",
    "ST": "Short Text",
    "TM": "Time",
    "UI": "Unique Identifier",
    "UL": "Unsigned Long",
    "UN": "Unknown",
    "US": "Unsigned Short",
    "UT": "Unlimited Text",
    "Same": "Use existing same VR"
}


def validate_hex_input(P):
    return len(P.strip()) <= 4 and all(c in "0123456789ABCDEFabcdef" for c in P.strip())

def modify_dicom_tags():
    source_folder = source_entry.get()
    source_file = file_entry.get()
    output_folder = output_entry.get()

    if not output_folder:
        messagebox.showerror("Error", "Output folder path is empty.")
        return
    if source_folder and source_file:
        messagebox.showerror("Error", "Please select either a folder or a file, not both.")
        return
    if not source_folder and not source_file:
        messagebox.showerror("Error", "Please select a source folder or file.")
        return
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    tag_values = []
    for idx, (group_entry, element_entry, vr_combobox, new_value_entry, _) in enumerate(tag_entries, start=1):
        group_str = group_entry.get().strip()
        element_str = element_entry.get().strip()
        value = new_value_entry.get().strip()
        vr = vr_combobox.get().strip()

        if not (group_str and element_str and value):
            messagebox.showwarning("입력 누락", f"Row {idx}: Group/Element/Value 중 누락된 항목이 있어 건너뜁니다.")
            continue

        try:
            group = int(group_str, 16)
            element = int(element_str, 16)
        except ValueError:
            messagebox.showerror("Error", f"Row {idx}: Group '{group_str}' 또는 Element '{element_str}'는 유효한 16진수가 아닙니다.")
            continue

        tag_values.append((group, element, vr, value))

    if not tag_values:
        messagebox.showerror("Error", "No valid tag entries found.")
        return

    files_to_process = []
    if source_folder:
        for root, _, files in os.walk(source_folder):
            files_to_process.extend(
                os.path.join(root, file)
                for file in files if file.lower().endswith(".dcm")
            )
    elif source_file:
        files_to_process.append(source_file)

    try:
        for dicom_path in files_to_process:
            filename = os.path.basename(dicom_path)
            try:
                dicom = pydicom.dcmread(dicom_path)
            except Exception as e:
                messagebox.showerror("Error", f"Error reading DICOM file {filename}: {e}")
                continue

            for group, element, vr, new_value in tag_values:
                tag = Tag(group, element)
                if tag in dicom:
                    try:
                        dicom[tag].value = new_value
                    except Exception as e:
                        messagebox.showerror("Error", f"Error modifying tag {tag}: {e}")
                else:
                    if vr == "Same":
                        messagebox.showerror("Error", f"Tag {tag} does not exist and VR is not specified.")
                        continue
                    try:
                        elem = DataElement(tag, vr, new_value)
                        dicom.add(elem)
                    except Exception as e:
                        messagebox.showerror("Error", f"Error adding tag {tag}: {e}")

            output_path = os.path.join(output_folder, filename)
            try:
                dicom.save_as(output_path)
            except Exception as e:
                messagebox.showerror("Error", f"Error saving {filename}: {e}")

        messagebox.showinfo("Success", "Operation Complete!")
    except Exception as e:
        messagebox.showerror("Error", f"Something went wrong: {e}")

def browse_folder(entry):
    folder_path = filedialog.askdirectory()
    if folder_path:
        entry.delete(0, tk.END)
        entry.insert(0, folder_path)

def browse_file(entry):
    file_path = filedialog.askopenfilename(
        filetypes=[("DICOM Files", "*.dcm"), ("All Files", "*.*")]
    )
    if file_path:
        entry.delete(0, tk.END)
        entry.insert(0, file_path)

def add_edit_row():
    validate_hex = root.register(validate_hex_input)

    # Group + Element 묶음 Frame
    group_element_frame = tk.Frame(root)
    group_entry = tk.Entry(group_element_frame, width=6, validate="key", validatecommand=(validate_hex, "%P"))
    element_entry = tk.Entry(group_element_frame, width=6, validate="key", validatecommand=(validate_hex, "%P"))
    group_entry.pack(side="left", padx=(0, 3))
    element_entry.pack(side="left")

    vr_combobox = ttk.Combobox(root, values=VR_OPTIONS, width=7)
    vr_combobox.set("Same")
    # 기본 툴팁 연결
    vr_tooltip = ToolTip(vr_combobox, VR_LABELS.get("Same", "Unknown VR"))

    # 선택 변경 시 툴팁 텍스트 갱신
    def update_vr_tooltip(event, combobox=vr_combobox, tooltip=vr_tooltip):
        vr = combobox.get()
        tooltip.text = VR_LABELS.get(vr, "Unknown VR")

    vr_combobox.bind("<<ComboboxSelected>>", update_vr_tooltip)

    new_value_entry = tk.Entry(root, width=60)

    delete_button = tk.Button(
        root,
        text="-",
        command=lambda: delete_row(group_element_frame, vr_combobox, new_value_entry, delete_button),
        width=2,
    )

    row_index = len(tag_entries) + 6
    group_element_frame.grid(row=row_index, column=0, padx=(10, 2), pady=2, sticky="w")
    vr_combobox.grid(row=row_index, column=1, padx=3, pady=2, sticky="w")
    new_value_entry.grid(row=row_index, column=2, columnspan=2, padx=(3, 3), pady=2, sticky="we")
    delete_button.grid(row=row_index, column=4, padx=(2, 0), pady=2)

    tag_entries.append((group_entry, element_entry, vr_combobox, new_value_entry, delete_button))
    add_edit_button.grid(row=row_index + 1, column=0, columnspan=2, pady=5, sticky="w")
    run_button.grid(row=row_index + 1, column=3, columnspan=2, pady=5, sticky="e")

def delete_row(group_element_frame, vr_combobox, new_value_entry, delete_button):
    group_element_frame.grid_forget()
    vr_combobox.grid_forget()
    new_value_entry.grid_forget()
    delete_button.grid_forget()
    tag_entries[:] = [t for t in tag_entries if t[0].master != group_element_frame]

# Tooltip 헬퍼 클래스 정의 (GUI 상단에 추가)
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "9"))
        label.pack(ipadx=5, ipady=2)

    def hide_tip(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
        self.tipwindow = None

# ---------------------- GUI ----------------------
root = tk.Tk()
root.title("DICOM Tag Editor")
root.geometry("620x450")

for col in range(5):
    root.grid_columnconfigure(col, weight=1 if col in (2, 3) else 0)

validate_hex = root.register(validate_hex_input)

def create_path_row(label_text, row, entry_var, browse_cmd):
    tk.Label(root, text=label_text).grid(row=row, column=0, padx=(10, 2), pady=5, sticky="e")
    entry_var.grid(row=row, column=1, columnspan=3, padx=(0, 2), pady=5, sticky="we")
    tk.Button(root, text="Browse", command=browse_cmd).grid(row=row, column=4, padx=(2, 10), pady=5, sticky="w")

source_entry = tk.Entry(root, width=60)
file_entry = tk.Entry(root, width=60)
output_entry = tk.Entry(root, width=60)

create_path_row("Source Folder:", 0, source_entry, lambda: browse_folder(source_entry))
create_path_row("Source File:", 1, file_entry, lambda: browse_file(file_entry))
create_path_row("Output Folder:", 2, output_entry, lambda: browse_folder(output_entry))

tk.Label(root, text="Tag Edit", font=("Helvetica", 16)).grid(row=3, column=0, columnspan=6, pady=(10, 0))
tk.Frame(root, height=2, bd=1, relief=tk.SUNKEN).grid(row=4, column=0, columnspan=6, sticky="we", padx=10, pady=5)

# 라벨
tk.Label(root, text="Group / Element").grid(row=5, column=0, padx=3, sticky="w")
tk.Label(root, text="VR").grid(row=5, column=1, padx=3, sticky="w")
tk.Label(root, text="New Value").grid(row=5, column=2, columnspan=2, padx=3, sticky="w")

# 초기 한 줄
tag_entries = []

group_element_frame = tk.Frame(root)
initial_group_entry = tk.Entry(group_element_frame, width=6, validate="key", validatecommand=(validate_hex, "%P"))
initial_element_entry = tk.Entry(group_element_frame, width=6, validate="key", validatecommand=(validate_hex, "%P"))
initial_group_entry.pack(side="left", padx=(0, 3))
initial_element_entry.pack(side="left")

initial_vr_combobox = ttk.Combobox(root, values=VR_OPTIONS, width=7)
initial_vr_combobox.set("Same")
initial_vr_combobox.grid(row=1, column=1, padx=10, pady=5)

# 툴팁 연결
tooltip = ToolTip(initial_vr_combobox, VR_LABELS.get("Same"))

def update_tooltip(event):
    vr = initial_vr_combobox.get()
    tooltip.text = VR_LABELS.get(vr, "Unknown VR")

initial_vr_combobox.bind("<<ComboboxSelected>>", update_tooltip)


initial_new_value_entry = tk.Entry(root, width=60)

group_element_frame.grid(row=6, column=0, padx=(10, 2), pady=2, sticky="w")
initial_vr_combobox.grid(row=6, column=1, padx=3, pady=2, sticky="w")
initial_new_value_entry.grid(row=6, column=2, columnspan=2, padx=(3, 3), pady=2, sticky="we")

tag_entries.append((initial_group_entry, initial_element_entry, initial_vr_combobox, initial_new_value_entry, None))

add_edit_button = tk.Button(root, text="Add Edit", command=add_edit_row)
run_button = tk.Button(root, text="Run", command=modify_dicom_tags)

add_edit_button.grid(row=7, column=0, columnspan=2, pady=5, sticky="w", padx=(10, 0))
run_button.grid(row=7, column=3, columnspan=2, pady=5, sticky="e", padx=(0, 10))

root.mainloop()
