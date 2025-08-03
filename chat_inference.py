import os

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_NAME = "instruction-pretrain/InstructLM-500M"
MODEL_PATH = "./fine-tuned-model"

if not os.path.isdir(MODEL_PATH) or not os.listdir(MODEL_PATH):
    AutoModelForCausalLM.from_pretrained(MODEL_NAME).save_pretrained(MODEL_PATH)
    AutoTokenizer.from_pretrained(MODEL_NAME).save_pretrained(MODEL_PATH)

# Load your fine-tuned model
MODEL_PATH = "./fine-tuned-model"

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, trust_remote_code=True)

# Use Apple MPS or fallback to CPU
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model.to(device)
model.eval()


def chat(user_question: str):
    prompt = f"""### Instruction:
Answer the user's question in less than 100 tokens. 

### Input:
{user_question}

### Response:
"""
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=300,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )

    response = tokenizer.decode(output[0], skip_special_tokens=True)
    return response.split("### Response:")[-1].strip()


# Chat loop
if __name__ == "__main__":
    print("🧠 Personal Scheduling Assistant — Chat\n(Type 'exit' to quit)\n")
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in ["exit", "quit"]:
            break
        reply = chat(user_input)
        print(f"Assistant: {reply}\n")
