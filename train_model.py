from typing import Any

import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

# Config
BASE_MODEL = "Qwen/Qwen1.5-0.5B"  # Small enough for CPU/M1
TEXT_FILE_PATH = "./train.txt"
OUTPUT_DIR = "./fine-tuned-model"
MAX_SEQ_LENGTH = 512
dataset = load_dataset(
    "json", data_files="train_data_chatml_format.jsonl", split="train"
)

# Use MPS (Apple GPU) if available
device_str = "mps" if torch.backends.mps.is_available() else "cpu"

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, trust_remote_code=True)
model = model.to(device_str)  # type: ignore[arg-type]


def tokenize_fn(example_batch: dict[str, Any]) -> dict[str, Any]:
    prompts = []
    for messages in example_batch["messages"]:
        conv = ""
        for turn in messages:
            role = turn["role"]
            content = turn["content"].strip()
            if role == "user":
                conv += f"<|user|>\n{content}\n"
            elif role == "assistant":
                conv += f"<|assistant|>\n{content}\n"
        prompts.append(conv.strip())

    result = tokenizer(
        prompts,
        truncation=True,
        padding="max_length",
        max_length=512,
    )
    return dict(result)


tokenized_dataset = dataset.map(tokenize_fn, batched=True)
data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

# Training config
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=2,
    num_train_epochs=3,
    save_strategy="epoch",
    logging_steps=10,
    fp16=False,  # No CUDA, so disable fp16
    push_to_hub=False,
)

# Trainer setup
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    tokenizer=tokenizer,
    data_collator=data_collator,
)

# Train
trainer.train()

# Save
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
