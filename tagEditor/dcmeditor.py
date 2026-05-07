import os
import sys
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pydicom
from pydicom.tag import Tag
from pydicom.dataelem import DataElement
from pydicom.valuerep import DA, DT, TM

VR_OPTIONS = [
    "Same", "AE", "AS", "AT", "CS", "DA", "DS", "DT", "FL", "FD", "IS", "LO", "LT",
    "OB", "OD", "OF", "OW", "PN", "SH", "SL", "SQ", "SS", "ST", "TM", "UI",
    "UL", "UN", "US", "UT"
]

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


def get_resource_path(relative_path):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)

def validate_hex_input(P):
    p = P.strip()
    return len(p) <= 4 and all(c in "0123456789ABCDEFabcdef" for c in p)

def get_missing_required_paths(source_folder, source_file, output_folder):
    missing = []
    if not output_folder:
        missing.append("Output Folder")
    if not source_folder and not source_file:
        missing.append("Source Folder")
        missing.append("Source File")
    return missing

def is_output_overlapping(source_folder, source_file, output_folder):
    """Return 'same', 'nested', or False."""
    if not output_folder:
        return False
    output_abs = os.path.abspath(output_folder)

    if source_folder:
        source_abs = os.path.abspath(source_folder)
        if output_abs == source_abs:
            return "same"
        try:
            if os.path.commonpath([output_abs, source_abs]) == source_abs:
                return "nested"
        except ValueError:
            pass

    if source_file:
        source_dir = os.path.abspath(os.path.dirname(source_file))
        if output_abs == source_dir:
            return "same"

    return False

def convert_value_for_vr(vr, value):
    def convert_single(single_value):
        single_value = single_value.strip()
        if vr in ("DS", "FL", "FD"):
            return float(single_value)
        if vr in ("IS", "SL", "SS", "UL", "US"):
            return int(single_value)
        if vr == "DA":
            return DA(single_value)
        if vr == "DT":
            return DT(single_value)
        if vr == "TM":
            return TM(single_value)
        if vr == "AT":
            tag_str = single_value.replace(",", "").replace(" ", "")
            if len(tag_str) != 8 or not all(c in "0123456789ABCDEFabcdef" for c in tag_str):
                raise ValueError("AT VR requires tag format GGGGEEEE or GGGG,EEEE")
            return Tag(int(tag_str[:4], 16), int(tag_str[4:], 16))
        if vr == "SQ":
            raise ValueError("SQ VR requires sequence input")
        return single_value

    if "\\" in value:
        return [convert_single(v) for v in value.split("\\")]
    return convert_single(value)

def modify_dicom_tags_worker(files_to_process, tag_values, output_folder, progress_queue):
    total_files = len(files_to_process)
    processed_files = 0
    failed_files = 0

    for dicom_path in files_to_process:
        filename = os.path.basename(dicom_path)
        file_failed = False

        try:
            dicom = pydicom.dcmread(dicom_path)
        except Exception as e:
            progress_queue.put(("error", f"Error reading DICOM file {filename}: {e}"))
            file_failed = True
            processed_files += 1
            failed_files += 1
            progress_queue.put(("progress", processed_files, total_files))
            continue

        for group, element, vr, new_value in tag_values:
            tag = Tag(group, element)

            try:
                if tag == Tag(0x0010, 0x0010):  # Patient's Name
                    dicom.SpecificCharacterSet = ['ISO 2022 IR 100', 'ISO 2022 IR 13', 'ISO 2022 IR 87']

                if tag in dicom:
                    actual_vr = dicom[tag].VR
                    dicom[tag].value = convert_value_for_vr(actual_vr, new_value)
                else:
                    if vr == "Same":
                        progress_queue.put(("error", f"Tag {tag} does not exist and VR is not specified."))
                        file_failed = True
                        continue
                    converted_value = convert_value_for_vr(vr, new_value)
                    elem = DataElement(tag, vr, converted_value)
                    dicom.add(elem)
            except Exception as e:
                progress_queue.put(("error", f"Error processing tag {tag}: {e}"))
                file_failed = True

        output_path = os.path.join(output_folder, filename)
        try:
            dicom.save_as(output_path)
        except Exception as e:
            progress_queue.put(("error", f"Error saving {filename}: {e}"))
            file_failed = True

        processed_files += 1
        if file_failed:
            failed_files += 1
        progress_queue.put(("progress", processed_files, total_files))

    progress_queue.put(("done", failed_files, total_files))


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


class DicomEditorApp:
    # Fixed rows inside scrollable_frame:
    # Tag Edit label(0), separator(1), column headers(2)
    FIXED_ROWS = 3

    def __init__(self, root):
        self.root = root
        self.root.title("DICOM Tag Editor")
        self.root.geometry("620x450")
        self.tag_entries = []

        # Allow row 3 (canvas row) to expand with the window
        for col in range(5):
            self.root.grid_columnconfigure(col, weight=1 if col in (2, 3) else 0)
        self.root.grid_rowconfigure(3, weight=1)

        self.validate_hex = self.root.register(validate_hex_input)

        self._build_path_rows()
        self._build_scroll_area()
        self._build_tag_section_header()
        self._add_tag_row(deletable=False)
        self._build_action_row()

    # ── Layout ────────────────────────────────────────────────────

    def _build_path_rows(self):
        self.source_entry = tk.Entry(self.root, width=60)
        self.file_entry = tk.Entry(self.root, width=60)
        self.output_entry = tk.Entry(self.root, width=60)

        self._create_path_row("Source Folder:", 0, self.source_entry,
                              lambda: self.browse_folder(self.source_entry))
        self._create_path_row("Source File:", 1, self.file_entry,
                              lambda: self.browse_file(self.file_entry))
        self._create_path_row("Output Folder:", 2, self.output_entry,
                              lambda: self.browse_folder(self.output_entry))

    def _build_scroll_area(self):
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.configure(yscrollcommand=self._on_scrollbar_set)
        self.canvas.grid(row=3, column=0, columnspan=5, sticky="nswe")

        # Fixed-width container always occupies column 5 — canvas width never shifts
        self.scrollbar_container = tk.Frame(self.root, width=17)
        self.scrollbar_container.grid(row=3, column=5, sticky="ns")
        self.scrollbar_container.grid_propagate(False)

        self.scrollbar = ttk.Scrollbar(self.scrollbar_container, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        for col in range(5):
            self.scrollable_frame.grid_columnconfigure(col, weight=1 if col in (2, 3) else 0)
        # Reserve delete button column width so New Value entry never shifts
        self.scrollable_frame.grid_columnconfigure(4, minsize=30)

        self.scrollable_frame.bind("<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_scrollbar_set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.scrollbar.pack_forget()
        else:
            self.scrollbar.pack(fill="both", expand=True)
        self.scrollbar.set(lo, hi)

    def _on_mousewheel(self, event):
        if self.scrollbar.winfo_ismapped():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_tag_section_header(self):
        tk.Label(self.scrollable_frame, text="Tag Edit", font=("Helvetica", 16)).grid(
            row=0, column=0, columnspan=6, pady=(10, 0))
        tk.Frame(self.scrollable_frame, height=2, bd=1, relief=tk.SUNKEN).grid(
            row=1, column=0, columnspan=6, sticky="we", padx=10, pady=5)
        tk.Label(self.scrollable_frame, text="Group / Element").grid(row=2, column=0, padx=3, sticky="w")
        tk.Label(self.scrollable_frame, text="VR").grid(row=2, column=1, padx=3, sticky="w")
        tk.Label(self.scrollable_frame, text="New Value").grid(row=2, column=2, columnspan=2, padx=3, sticky="w")

    def _build_action_row(self):
        self.add_edit_button = tk.Button(self.scrollable_frame, text="Add Edit", command=self.add_edit_row)
        self.run_button = tk.Button(self.scrollable_frame, text="Run", command=self.modify_dicom_tags)
        self.progress_label = tk.Label(self.scrollable_frame, text="")
        self._reposition_action_row()

    def _reposition_action_row(self):
        action_row = self.FIXED_ROWS + len(self.tag_entries)
        self.add_edit_button.grid(row=action_row, column=0, columnspan=2, pady=5, sticky="w", padx=(10, 0))
        self.run_button.grid(row=action_row, column=3, columnspan=2, pady=5, sticky="e", padx=(0, 10))
        self.progress_label.grid(row=action_row + 1, column=0, columnspan=5, pady=(2, 5), sticky="w", padx=(10, 0))

    def _create_path_row(self, label_text, row, entry_var, browse_cmd):
        tk.Label(self.root, text=label_text).grid(row=row, column=0, padx=(10, 2), pady=5, sticky="e")
        entry_var.grid(row=row, column=1, columnspan=3, padx=(0, 2), pady=5, sticky="we")
        tk.Button(self.root, text="Browse", command=browse_cmd).grid(
            row=row, column=4, padx=(2, 10), pady=5, sticky="w")

    def _add_tag_row(self, deletable=True):
        row_index = self.FIXED_ROWS + len(self.tag_entries)

        group_element_frame = tk.Frame(self.scrollable_frame)
        group_entry = tk.Entry(group_element_frame, width=6, validate="key",
                               validatecommand=(self.validate_hex, "%P"))
        element_entry = tk.Entry(group_element_frame, width=6, validate="key",
                                 validatecommand=(self.validate_hex, "%P"))
        group_entry.pack(side="left", padx=(0, 3))
        element_entry.pack(side="left")

        vr_combobox = ttk.Combobox(self.scrollable_frame, values=VR_OPTIONS, width=7)
        vr_combobox.set("Same")
        vr_tooltip = ToolTip(vr_combobox, VR_LABELS.get("Same", "Unknown VR"))

        def update_vr_tooltip(event, cb=vr_combobox, tt=vr_tooltip):
            tt.text = VR_LABELS.get(cb.get(), "Unknown VR")

        vr_combobox.bind("<<ComboboxSelected>>", update_vr_tooltip)

        new_value_entry = tk.Entry(self.scrollable_frame, width=60)

        if deletable:
            delete_button = tk.Button(
                self.scrollable_frame, text="-", width=2,
                command=lambda: self.delete_row(group_element_frame, vr_combobox,
                                                new_value_entry, delete_button),
            )
            delete_button.grid(row=row_index, column=4, padx=(2, 0), pady=2)
        else:
            delete_button = None

        group_element_frame.grid(row=row_index, column=0, padx=(10, 2), pady=2, sticky="w")
        vr_combobox.grid(row=row_index, column=1, padx=3, pady=2, sticky="w")
        new_value_entry.grid(row=row_index, column=2, columnspan=2, padx=(3, 3), pady=2, sticky="we")

        self.tag_entries.append((group_entry, element_entry, vr_combobox, new_value_entry, delete_button))

    def _regrid_tag_rows(self):
        """Re-assign grid rows for remaining entries after a deletion."""
        for idx, (group_entry, _, vr_combobox, new_value_entry, delete_button) in enumerate(self.tag_entries):
            row_index = self.FIXED_ROWS + idx
            group_entry.master.grid(row=row_index, column=0, padx=(10, 2), pady=2, sticky="w")
            vr_combobox.grid(row=row_index, column=1, padx=3, pady=2, sticky="w")
            new_value_entry.grid(row=row_index, column=2, columnspan=2, padx=(3, 3), pady=2, sticky="we")
            if delete_button:
                delete_button.grid(row=row_index, column=4, padx=(2, 0), pady=2)
        self._reposition_action_row()

    # ── Event handlers ────────────────────────────────────────────

    def browse_folder(self, entry):
        folder_path = filedialog.askdirectory()
        if folder_path:
            entry.delete(0, tk.END)
            entry.insert(0, folder_path)

    def browse_file(self, entry):
        file_path = filedialog.askopenfilename(
            filetypes=[("DICOM Files", "*.dcm"), ("All Files", "*.*")]
        )
        if file_path:
            entry.delete(0, tk.END)
            entry.insert(0, file_path)

    def add_edit_row(self):
        self._add_tag_row(deletable=True)
        action_row = self.FIXED_ROWS + len(self.tag_entries)
        self.add_edit_button.grid(row=action_row, column=0, columnspan=2, pady=5, sticky="w", padx=(10, 0))
        self.run_button.grid(row=action_row, column=3, columnspan=2, pady=5, sticky="e", padx=(0, 10))
        self.progress_label.grid(row=action_row + 1, column=0, columnspan=5, pady=(2, 5), sticky="w", padx=(10, 0))

    def delete_row(self, group_element_frame, vr_combobox, new_value_entry, delete_button):
        group_element_frame.grid_forget()
        vr_combobox.grid_forget()
        new_value_entry.grid_forget()
        delete_button.grid_forget()
        self.tag_entries[:] = [t for t in self.tag_entries if t[0].master != group_element_frame]
        self._regrid_tag_rows()

    def modify_dicom_tags(self):
        source_folder = self.source_entry.get()
        source_file = self.file_entry.get()
        output_folder = self.output_entry.get()

        missing = get_missing_required_paths(source_folder, source_file, output_folder)
        if missing:
            messagebox.showerror("Error", f"Unfilled input box: {', '.join(missing)}")
            return
        if source_folder and source_file:
            messagebox.showerror("Error", "Please select either a folder or a file, not both.")
            return
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        tag_values = []
        for idx, (group_entry, element_entry, vr_combobox, new_value_entry, _) in enumerate(self.tag_entries, start=1):
            group_str = group_entry.get().strip()
            element_str = element_entry.get().strip()
            value = new_value_entry.get().strip()
            vr = vr_combobox.get().strip()

            if not (group_str and element_str and value):
                messagebox.showwarning("Missing Input", f"Row {idx}: Group, Element, or Value is empty. Skipping.")
                continue

            try:
                group = int(group_str, 16)
                element = int(element_str, 16)
            except ValueError:
                messagebox.showerror("Error", f"Row {idx}: Group '{group_str}' or Element '{element_str}' is not a valid hex value.")
                continue

            tag_values.append((group, element, vr, value))

        if not tag_values:
            messagebox.showerror("Error", "No valid tag entries found.")
            return

        files_to_process = []
        if source_folder:
            for dir_root, _, files in os.walk(source_folder):
                files_to_process.extend(
                    os.path.join(dir_root, file)
                    for file in files if file.lower().endswith(".dcm")
                )
        elif source_file:
            files_to_process.append(source_file)

        if not files_to_process:
            messagebox.showerror("Error", "There are no DICOM files.")
            return

        overlap = is_output_overlapping(source_folder, source_file, output_folder)
        if overlap == "same":
            proceed = messagebox.askyesno(
                "Confirm",
                "The output folder is the same as the source folder.\n"
                "Original files will be overwritten. Continue?"
            )
            if not proceed:
                return
        elif overlap == "nested":
            proceed = messagebox.askyesno(
                "Confirm",
                "The output folder is inside the source folder.\n"
                "Files already saved to the output folder may be re-processed. Continue?"
            )
            if not proceed:
                return

        self.run_button.config(state=tk.DISABLED)
        self.add_edit_button.config(state=tk.DISABLED)
        self.progress_label.config(text=f"0/{len(files_to_process)} processing...")

        progress_queue = queue.Queue()
        worker_thread = threading.Thread(
            target=modify_dicom_tags_worker,
            args=(files_to_process, tag_values, output_folder, progress_queue),
            daemon=True
        )
        worker_thread.start()

        error_log = []

        def process_queue():
            try:
                while True:
                    message = progress_queue.get_nowait()
                    msg_type = message[0]

                    if msg_type == "progress":
                        current, total = message[1], message[2]
                        self.progress_label.config(text=f"{current}/{total} processing...")
                    elif msg_type == "error":
                        error_log.append(message[1])
                    elif msg_type == "done":
                        failed_files, total = message[1], message[2]
                        if not error_log:
                            messagebox.showinfo("Success", "Operation Complete!")
                        else:
                            summary = "\n".join(error_log[:20])
                            if len(error_log) > 20:
                                summary += f"\n... and {len(error_log) - 20} more error(s)."
                            messagebox.showerror(
                                f"Completed with errors ({failed_files}/{total} failed)",
                                summary
                            )
                        self.run_button.config(state=tk.NORMAL)
                        self.add_edit_button.config(state=tk.NORMAL)
                        self.progress_label.config(text="")
                        return
            except queue.Empty:
                self.root.after(100, process_queue)

        self.root.after(100, process_queue)


if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconbitmap(get_resource_path("editor.ico"))
    except Exception:
        pass
    app = DicomEditorApp(root)
    root.mainloop()
