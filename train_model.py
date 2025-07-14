import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer, \
    DataCollatorForLanguageModeling

# Configo
BASE_MODEL = "Qwen/Qwen1.5-0.5B"  # Small enough for CPU/M1
OUTPUT_DIR = "./fine-tuned-model"
MAX_SEQ_LENGTH = 512

# Format selection - set this to choose your data format
DATA_FORMAT = "instruction"  # Options: "chatml" or "instruction"

# Data files based on format
DATA_FILES = {
    "chatml": "train_data_chatml_format.jsonl",
    "instruction": "train_data_instruction_format.jsonl"
}

# Load dataset based on format
dataset = load_dataset("json", data_files=DATA_FILES[DATA_FORMAT], split="train")

# Use MPS (Apple GPU) if available
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, trust_remote_code=True)
model.to(device)


def tokenize_chatml_format(example_batch):
    """Tokenize ChatML format data"""
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

    return tokenizer(
        prompts,
        truncation=True,
        padding="max_length",
        max_length=MAX_SEQ_LENGTH,
    )


def tokenize_instruction_format(example_batch):
    """Tokenize Instruction-Input-Output format data"""
    prompts = []
    for i in range(len(example_batch["instruction"])):
        instruction = example_batch["instruction"][i].strip()
        input_text = example_batch["input"][i].strip()
        output = example_batch["output"][i].strip()

        # Format the prompt based on whether input is provided
        if input_text:
            # When input is provided, include it in the prompt
            prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
        else:
            # When input is empty, skip the input section
            prompt = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"

        prompts.append(prompt)

    return tokenizer(
        prompts,
        truncation=True,
        padding="max_length",
        max_length=MAX_SEQ_LENGTH,
    )


# Select tokenization function based on format
if DATA_FORMAT == "chatml":
    tokenize_fn = tokenize_chatml_format
    print("Using ChatML format tokenization")
elif DATA_FORMAT == "instruction":
    tokenize_fn = tokenize_instruction_format
    print("Using Instruction format tokenization")
else:
    raise ValueError(f"Unsupported data format: {DATA_FORMAT}")

# Tokenize dataset
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
    push_to_hub=False
)

# Trainer setup
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    tokenizer=tokenizer,
    data_collator=data_collator,
)

# Print some examples to verify formatting
print(f"\nDataset size: {len(dataset)}")
print("\nSample tokenized examples:")
for i in range(min(2, len(dataset))):
    if DATA_FORMAT == "chatml":
        print(f"\nExample {i + 1} (ChatML):")
        messages = dataset[i]["messages"]
        conv = ""
        for turn in messages:
            role = turn["role"]
            content = turn["content"].strip()
            if role == "user":
                conv += f"<|user|>\n{content}\n"
            elif role == "assistant":
                conv += f"<|assistant|>\n{content}\n"
        print(conv.strip())
    else:  # instruction format
        print(f"\nExample {i + 1} (Instruction):")
        instruction = dataset[i]["instruction"]
        input_text = dataset[i]["input"]
        output = dataset[i]["output"]

        if input_text:
            prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
        else:
            prompt = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
        print(prompt)

# Train
print(f"\nStarting training with {DATA_FORMAT} format...")
trainer.train()

# Save
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"Model saved to {OUTPUT_DIR}")
