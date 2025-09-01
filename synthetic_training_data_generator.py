import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

USE_CHATML_FORMAT = True  # Set to False for plain instruction-input-output format


# Generate synthetic calendar events
def generate_calendar_events(
    start_date: datetime, days: int = 60
) -> list[dict[str, Any]]:
    events = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        events.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "events": [
                    f"{date.strftime('%Y-%m-%d')} 09:00 AM - Daily checkin with the team",
                    f"{date.strftime('%Y-%m-%d')} 02:00 PM - Project Update",
                    f"{date.strftime('%Y-%m-%d')} 05:00 PM - Review messages and Plan Next Day",
                ],
            }
        )
    return events


# Synthetic message pool
def generate_messages() -> list[str]:
    return [
        "Reminder: Submit AI proposal by Friday.",
        "Client rescheduled meeting to Tuesday.",
        "Dinner with John confirmed for 7PM.",
        "Don't forget: Book the conference room for Thursday.",
        "Hey, your package will arrive tomorrow.",
        "Update: Interview moved to 11 AM.",
        "New sprint starts on Monday.",
        "Resend last week's notes to the team.",
        "Prepare demo slides for the investor call.",
        "Vaccination appointment confirmed at 3PM.",
        "The design team needs final specs by Thursday.",
        "Call with supplier pushed to next week.",
        "Grocery delivery window: 6PM–8PM today.",
        "Lawn mowing service confirmed for Saturday.",
        "Electrician visit scheduled for Friday morning.",
        "Anniversary dinner reservation at 8PM.",
        "Water bill due tomorrow.",
        "Submit timesheet before 6PM.",
        "Library books due in 2 days.",
        "Car service booked for Monday at 10AM.",
    ]


# Format into ChatML-style prompt
def make_chatml(user_msg: str, assistant_msg: str) -> dict:
    return {
        "messages": [
            {"role": "user", "content": user_msg.strip()},
            {"role": "assistant", "content": assistant_msg.strip()},
        ]
    }


# Create dataset entries
def generate_jsonl_dataset(
    calendar_events: list[dict[str, Any]], messages: list[str], output_file: Path
) -> None:
    examples = []

    for entry in calendar_events:
        cal = entry["events"]
        examples.append(
            make_chatml(
                "What is my next event?\n" + "\n".join(cal),
                f"Your next event is '{cal[0].split(' - ')[-1]}' at {cal[0].split(' ')[1]}.",
            )
        )
        examples.append(
            make_chatml(
                "Summarize today's schedule.\n" + "\n".join(cal),
                f"You have {len(cal)} events today: "
                + "; ".join([e.split(" - ")[-1] for e in cal])
                + ".",
            )
        )
        examples.append(
            make_chatml(
                "When is my last event?\n" + "\n".join(cal),
                f"Your last event is '{cal[-1].split(' - ')[-1]}' at {cal[-1].split(' ')[1]}.",
            )
        )

    for i in range(0, len(messages), 3):
        group = messages[i : i + 3]
        examples.append(
            make_chatml(
                "Summarize key messages:\n" + "\n".join(group),
                "Here are the important points:\n"
                + "\n".join(f"- {msg}" for msg in group),
            )
        )

    unrelated_questions = [
        "Who is the president of the USA?",
        "What's the capital of France?",
        "Can you write me a poem?",
        "Explain quantum mechanics.",
        "Tell me a joke.",
        "What time is it?",
    ]
    for q in unrelated_questions:
        examples.append(
            make_chatml(
                q,
                "Sorry, I’m your scheduling assistant. I can only help with calendar events and messages.",
            )
        )

    # Shuffle to improve generalization
    random.shuffle(examples)

    # Save to JSONL
    with open(output_file, "w", encoding="utf-8") as f:
        for item in examples:
            f.write(json.dumps(item) + "\n")


# Generate dataset
output_path = Path("train_data_chatml_format.jsonl")
calendar_data = generate_calendar_events(datetime(2025, 6, 22), days=60)
message_data = generate_messages() * 5

generate_jsonl_dataset(calendar_data, message_data, output_path)
