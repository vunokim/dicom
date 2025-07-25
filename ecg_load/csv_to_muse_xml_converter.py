import os
import xml.etree.ElementTree as ET
import pandas as pd

# === 사용자 설정 ===
XML_TEMPLATE_PATH = "D:\\ECG\\ecg\\실제ATTRdata\\S0304_MUSE_20240123_133526_47000.xml"
CSV_FOLDER = "D:\\ECG\\arrhythmia_ECGData_12lead_10000patients\\ECGDataDenoised"
OUTPUT_FOLDER = "D:\\ECG\\arrhythmia_ECGData_12lead_10000patients\\xml"
DIAGNOSTICS_CSV_PATH = "D:\\ECG\\arrhythmia_ECGData_12lead_10000patients\\Diagnostics_test.csv"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 진단 정보 불러오기
diagnostics_df = pd.read_csv(DIAGNOSTICS_CSV_PATH)
diagnostics_df.set_index('FileName', inplace=True)

# 날짜/시간/환자ID 추출 및 변환
def format_date(date_str):
    return f"{date_str[4:6]}-{date_str[6:8]}-{date_str[0:4]}"

def format_time(time_str):
    return f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"

def extract_metadata_from_filename(fname):
    parts = os.path.splitext(fname)[0].split('_')
    if len(parts) >= 4:
        date_part = parts[1]
        time_part = parts[2]
        tail_part = parts[3]
        patient_id = time_part + tail_part[:2]
        return format_date(date_part), format_time(time_part), patient_id
    return "", "", ""

# 네임스페이스 자동 추출
def get_namespace(element):
    if element.tag[0] == "{":
        return element.tag[1:].split("}")[0]
    return ""

# XML 수정 함수
def replace_ecg_data_in_xml(root, signal_df, acquisition_date, acquisition_time, patient_id, diag_info):
    ns_uri = get_namespace(root)
    ns = {'ns': ns_uri} if ns_uri else {}
    ns_prefix = 'ns:' if ns_uri else ''

    def find_tag(path):
        return root.find(path.replace("ns:", ns_prefix), ns)

    def find_in(node, path):
        return node.find(path.replace("ns:", ns_prefix), ns)

    # Waveform 삽입
    signal_node = find_tag(".//ns:Signal")
    if signal_node is not None:
        for lead in signal_node.findall(f"{ns_prefix}LeadData", ns):
            lead_name_node = find_in(lead, f"{ns_prefix}LeadID")
            data_node = find_in(lead, f"{ns_prefix}WaveFormData")
            if lead_name_node is not None and data_node is not None:
                lead_name = lead_name_node.text.strip()
                if lead_name in signal_df.columns:
                    values = signal_df[lead_name].tolist()
                    data_node.text = " ".join([str(int(round(v))) for v in values])

    # 날짜/시간/환자ID
    for tag, value in zip(["AcquisitionDate", "AcquisitionTime", "PatientID"],
                          [acquisition_date, acquisition_time, patient_id]):
        node = find_tag(f".//ns:{tag}")
        if node is not None:
            node.text = value

    # 진단 관련 필드 삽입
    def update_or_create(parent_tag, tag_name, value):
        parent = find_tag(f".//ns:{parent_tag}")
        if parent is not None:
            elem = parent.find(f"{ns_prefix}{tag_name}", ns)
            if elem is not None:
                elem.text = str(value)
            else:
                new_elem = ET.SubElement(parent, tag_name)
                new_elem.text = str(value)

    fields_to_update = [
        ("PatientDemographics", "PatientAge"),
        ("PatientDemographics", "Gender"),
        ("RestingECGMeasurements", "VentricularRate"),
        ("RestingECGMeasurements", "AtrialRate"),
        ("RestingECGMeasurements", "QRSDuration"),
        ("RestingECGMeasurements", "QTInterval"),
        ("RestingECGMeasurements", "QTCorrected"),
        ("RestingECGMeasurements", "RAxis"),
        ("RestingECGMeasurements", "TAxis"),
        ("RestingECGMeasurements", "QRSCount"),
        ("RestingECGMeasurements", "QOnset"),
        ("RestingECGMeasurements", "QOffset"),
        ("RestingECGMeasurements", "TOffset"),
        ("OriginalRestingECGMeasurements", "VentricularRate"),
        ("OriginalRestingECGMeasurements", "AtrialRate"),
        ("OriginalRestingECGMeasurements", "QRSDuration"),
        ("OriginalRestingECGMeasurements", "QTInterval"),
        ("OriginalRestingECGMeasurements", "QTCorrected"),
        ("OriginalRestingECGMeasurements", "RAxis"),
        ("OriginalRestingECGMeasurements", "TAxis"),
        ("OriginalRestingECGMeasurements", "QRSCount"),
        ("OriginalRestingECGMeasurements", "QOnset"),
        ("OriginalRestingECGMeasurements", "QOffset"),
        ("OriginalRestingECGMeasurements", "TOffset"),
    ]
    for section, field in fields_to_update:
        if field in diag_info and pd.notna(diag_info[field]):
            update_or_create(section, field, diag_info[field])

    # Diagnosis 및 OriginalDiagnosis 처리
    for diag_section in ["Diagnosis", "OriginalDiagnosis"]:
        section = find_tag(f".//ns:{diag_section}")
        if section is not None:
            # Modality 백업
            modality = section.find(f"{ns_prefix}Modality", ns)
            # 기존 DiagnosisStatement 삭제
            for stmt in section.findall(f"{ns_prefix}DiagnosisStatement", ns):
                section.remove(stmt)
            # 다시 삽입
            if modality is not None:
                section.append(modality)
            # Beat1~Beat9 삽입
            for i in range(1, 10):
                beat_key = f"Beat{i}"
                if beat_key in diag_info and pd.notna(diag_info[beat_key]):
                    stmt = ET.Element("DiagnosisStatement")
                    flag = ET.SubElement(stmt, "StmtFlag")
                    flag.text = "ENDSLINE"
                    text = ET.SubElement(stmt, "StmtText")
                    text.text = str(diag_info[beat_key])
                    section.append(stmt)
            # OriginalDiagnosis에 추가 문장
            if diag_section == "OriginalDiagnosis":
                final_stmt = ET.Element("DiagnosisStatement")
                final_text = ET.SubElement(final_stmt, "StmtText")
                final_text.text = "When compared with ECG of"
                section.append(final_stmt)

# 전체 CSV 처리 함수
def convert_all_csv_to_xml(csv_dir, output_dir):
    for fname in os.listdir(csv_dir):
        if fname.lower().endswith(".csv"):
            csv_path = os.path.join(csv_dir, fname)
            try:
                # df = pd.read_csv(csv_path) # csv 첫행에 타이틀이 있을 경우 사용
                #아래 3줄은 csv 첫행에 타이틀 없이 바로 데이터로 시작할 떄 사용
                lead_names = ['I', 'II', 'III', 'AVR', 'AVL', 'AVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']
                df = pd.read_csv(csv_path, header=None)
                df.columns = lead_names[:df.shape[1]]

                acq_date, acq_time, patient_id = extract_metadata_from_filename(fname)

                # 확장자 제거 및 소문자로 비교
                file_key = os.path.splitext(fname)[0].lower()
                matched = diagnostics_df.reset_index()
                matched["FileNameLower"] = matched["FileName"].str.lower()
                row = matched[matched["FileNameLower"] == file_key]

                if not row.empty:
                    diag_info = row.iloc[0].to_dict()
                    print(f"✅ 진단 정보 매칭됨: {fname}")
                else:
                    diag_info = {}
                    print(f"⚠️ 진단 정보 없음: {fname}")

                tree = ET.parse(XML_TEMPLATE_PATH)
                root = tree.getroot()

                replace_ecg_data_in_xml(root, df, acq_date, acq_time, patient_id, diag_info)

                out_path = os.path.join(output_dir, os.path.splitext(fname)[0] + ".xml")
                tree.write(out_path, encoding="utf-8", xml_declaration=True)
                print(f"✅ 변환 완료: {fname} → {os.path.basename(out_path)}")
            except Exception as e:
                print(f"❌ 변환 실패: {fname} ({e})")

# 실행
if __name__ == "__main__":
    convert_all_csv_to_xml(CSV_FOLDER, OUTPUT_FOLDER)
