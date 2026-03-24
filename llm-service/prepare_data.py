"""
Run once locally to prepare training data from raw Loghub files.
Download HDFS_2k.log from: https://github.com/logpai/loghub
Place in llm-service/raw_logs/HDFS_2k.log
"""
import pandas as pd
from sklearn.preprocessing import LabelEncoder
import os

SEVERITY_MAP = {
    'error': 'HIGH', 'fail': 'HIGH', 'exception': 'HIGH',
    'critical': 'HIGH', 'timeout': 'HIGH', 'refused': 'HIGH',
    'crash': 'HIGH', 'fatal': 'HIGH',
    'warn': 'MEDIUM', 'warning': 'MEDIUM', 'retry': 'MEDIUM',
    'slow': 'MEDIUM', 'degraded': 'MEDIUM',
    'info': 'LOW', 'success': 'LOW', 'start': 'LOW',
    'connect': 'LOW', 'completed': 'LOW', 'initialized': 'LOW',
}

def label_log(message: str) -> str:
    msg = message.lower()
    for keyword, severity in SEVERITY_MAP.items():
        if keyword in msg:
            return severity
    return 'LOW'

def prepare_dataset(log_file_path: str, output_csv: str):
    if not os.path.exists(log_file_path):
        raise FileNotFoundError(f"Log file not found: {log_file_path}")

    logs = []
    with open(log_file_path, 'r', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line:
                logs.append({'text': line, 'label': label_log(line)})

    df = pd.DataFrame(logs)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    le = LabelEncoder()
    df['label_id'] = le.fit_transform(df['label'])

    os.makedirs(os.path.dirname(output_csv) or '.', exist_ok=True)
    df.to_csv(output_csv, index=False)

    label_map = {i: label for i, label in enumerate(le.classes_)}
    print(f"Dataset prepared: {len(df)} samples")
    print(f"Label distribution:\n{df['label'].value_counts()}")
    print(f"Label encoding: {label_map}")

if __name__ == "__main__":
    prepare_dataset("raw_logs/HDFS_2k.log", "data/labeled_logs.csv")
