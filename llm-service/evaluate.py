"""
Run locally after downloading model from Colab.
Generates eval_report.txt with accuracy, F1, and confusion matrix.
"""

import json
import os

import pandas as pd
import torch
from sklearn.metrics import classification_report, confusion_matrix
from transformers import DistilBertForSequenceClassification, DistilBertTokenizerFast


MODEL_DIR = "./models/distilbert-log"


def load_label_map(model_dir: str) -> dict[str, str]:
    label_map_path = os.path.join(model_dir, "label_map.json")
    if not os.path.exists(label_map_path):
        raise FileNotFoundError(
            f"Missing label map: {label_map_path}. "
            "Run train.py and copy the trained model directory first."
        )

    with open(label_map_path) as f:
        raw_map = json.load(f)

    return {str(k): v for k, v in raw_map.items()}


def main():
    if not os.path.exists(MODEL_DIR):
        raise FileNotFoundError(
            f"Missing model directory: {MODEL_DIR}. "
            "Download the trained DistilBERT model into this path first."
        )

    tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_DIR)
    model = DistilBertForSequenceClassification.from_pretrained(MODEL_DIR)
    model.eval()

    label_map = load_label_map(MODEL_DIR)

    # label_id is already in the CSV from prepare_data.py
    df = pd.read_csv("data/labeled_logs.csv")
    if "label_id" not in df.columns or "text" not in df.columns:
        raise ValueError("data/labeled_logs.csv must contain text and label_id columns")

    test_df = df.sample(min(200, len(df)), random_state=99).reset_index(drop=True)

    inputs = tokenizer(
        list(test_df["text"]),
        truncation=True,
        padding=True,
        max_length=128,
        return_tensors="pt",
    )

    with torch.no_grad():
        outputs = model(**inputs)
        preds = torch.argmax(outputs.logits, dim=1).numpy()

    true_labels = [label_map[str(lid)] for lid in test_df["label_id"]]
    pred_labels = [label_map[str(p)] for p in preds]

    ordered = sorted(label_map.values())
    report = classification_report(
        true_labels,
        pred_labels,
        labels=ordered,
        zero_division=0,
    )
    matrix = confusion_matrix(true_labels, pred_labels, labels=ordered)

    print(report)
    print(f"Confusion Matrix {ordered}:\n{matrix}")

    os.makedirs("models", exist_ok=True)
    with open("models/eval_report.txt", "w") as f:
        f.write("LLM Log Explainer - DistilBERT Evaluation\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Test samples: {len(test_df)}\n")
        f.write(f"Labels: {ordered}\n\n")
        f.write("Classification Report\n" + "-" * 50 + "\n")
        f.write(report)
        f.write(f"\nConfusion Matrix {ordered}\n" + "-" * 50 + "\n")
        f.write(str(matrix))

    print("Saved to models/eval_report.txt")


if __name__ == "__main__":
    main()
