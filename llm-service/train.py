"""
DistilBERT fine-tuning for log severity classification.
RUN ON GOOGLE COLAB WITH T4 GPU - not locally.

Steps:
1. colab.research.google.com
2. Runtime > Change runtime type > T4 GPU
3. Upload this file + data/labeled_logs.csv
4. Uncomment Drive lines (marked STEP A and STEP B)
5. Run
6. Download model.zip to Mac
7. Extract into llm-service/models/distilbert-log/
"""

import json
import os

import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset
from transformers import (
    DistilBertForSequenceClassification,
    DistilBertTokenizerFast,
    Trainer,
    TrainingArguments,
)


# STEP A - Uncomment on Colab to save model to Drive (survives session end)
# from google.colab import drive
# drive.mount('/content/drive')

SAVE_DIR = "./models/distilbert-log"
# On Colab, switch to:
# SAVE_DIR = "/content/drive/MyDrive/llm-log-explainer/models/distilbert-log"


def load_data(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Training data not found: {csv_path}")

    df = pd.read_csv(csv_path)
    required_columns = {"text", "label", "label_id"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns in {csv_path}: {sorted(missing_columns)}"
        )

    return df


class LogDataset(Dataset):
    def __init__(self, tokenizer, texts, labels):
        self.encodings = tokenizer(
            list(texts),
            truncation=True,
            padding=True,
            max_length=128,
        )
        self.labels = list(labels)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        item = {k: torch.tensor(v[idx]) for k, v in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx])
        return item


def main():
    df = load_data("data/labeled_logs.csv")
    print(f"Total samples: {len(df)}")
    print(df["label"].value_counts())

    num_labels = df["label_id"].nunique()
    train_df, test_df = train_test_split(
        df,
        test_size=0.2,
        random_state=42,
        stratify=df["label_id"],
    )

    tokenizer = DistilBertTokenizerFast.from_pretrained("distilbert-base-uncased")

    train_dataset = LogDataset(tokenizer, train_df["text"], train_df["label_id"])
    test_dataset = LogDataset(tokenizer, test_df["text"], test_df["label_id"])

    model = DistilBertForSequenceClassification.from_pretrained(
        "distilbert-base-uncased",
        num_labels=num_labels,
    )

    training_args = TrainingArguments(
        output_dir=SAVE_DIR,
        num_train_epochs=4,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        logging_steps=10,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
    )
    trainer.train()

    os.makedirs(SAVE_DIR, exist_ok=True)
    model.save_pretrained(SAVE_DIR)
    tokenizer.save_pretrained(SAVE_DIR)

    label_names = sorted(df["label"].unique())
    label_map = {i: label for i, label in enumerate(label_names)}
    with open(os.path.join(SAVE_DIR, "label_map.json"), "w") as f:
        json.dump(label_map, f, indent=2)

    print(f"Model saved to {SAVE_DIR}")
    print(f"Label map: {label_map}")

    # STEP B - Uncomment on Colab to download model after training:
    # import shutil
    # from google.colab import files
    # shutil.make_archive("distilbert-log", "zip", SAVE_DIR)
    # files.download("distilbert-log.zip")


if __name__ == "__main__":
    main()
