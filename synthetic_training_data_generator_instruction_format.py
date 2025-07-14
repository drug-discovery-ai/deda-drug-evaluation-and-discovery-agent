import json
import random
from datetime import datetime, timedelta
from pathlib import Path


# Generate synthetic calendar events
def generate_calendar_events(start_date, days=60):
    events = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        events.append({
            "date": date.strftime("%Y-%m-%d"),
            "events": [
                f"{date.strftime('%Y-%m-%d')} 09:00 AM - Daily checkin with the team",
                f"{date.strftime('%Y-%m-%d')} 02:00 PM - Project Update",
                f"{date.strftime('%Y-%m-%d')} 05:00 PM - Review messages and Plan Next Day"
            ]
        })
    return events


# Synthetic message pool
def generate_messages():
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
        "Car service booked for Monday at 10AM."
    ]


# Format into Instruction-Input-Output style
def make_instruction_format(instruction: str, input_text: str, output: str) -> dict:
    return {
        "instruction": instruction.strip(),
        "input": input_text.strip(),
        "output": output.strip()
    }


# Create dataset entries
def generate_jsonl_dataset(calendar_events, messages, output_file):
    examples = []

    # Calendar-based examples
    for entry in calendar_events:
        cal = entry["events"]

        # Next event query - needs calendar input
        examples.append(make_instruction_format(
            "You are a scheduling assistant. Given a list of calendar events, identify the next upcoming event.",
            "\n".join(cal),
            f"Your next event is '{cal[0].split(' - ')[-1]}' at {cal[0].split(' ')[1]}."
        ))

        # Schedule summary - needs calendar input
        examples.append(make_instruction_format(
            "You are a scheduling assistant. Given a list of calendar events, provide a summary of today's schedule.",
            "\n".join(cal),
            f"You have {len(cal)} events today: " + "; ".join([e.split(' - ')[-1] for e in cal]) + "."
        ))

        # Last event query - needs calendar input
        examples.append(make_instruction_format(
            "You are a scheduling assistant. Given a list of calendar events, identify the last event of the day.",
            "\n".join(cal),
            f"Your last event is '{cal[-1].split(' - ')[-1]}' at {cal[-1].split(' ')[1]}."
        ))

    # Message-based examples
    for i in range(0, len(messages), 3):
        group = messages[i:i + 3]

        # Message summarization - needs message input
        examples.append(make_instruction_format(
            "You are a scheduling assistant. Given a list of messages, summarize the key points.",
            "\n".join(group),
            "Here are the important points:\n" + "\n".join(f"- {msg}" for msg in group)
        ))

    # Priority identification examples
    urgent_keywords = ["urgent", "ASAP", "immediate", "deadline", "due"]
    for i in range(0, len(messages), 2):
        group = messages[i:i + 2]
        # Add some urgent markers randomly
        modified_group = []
        for msg in group:
            if random.random() < 0.3:  # 30% chance to make urgent
                msg = f"URGENT: {msg}"
            modified_group.append(msg)

        examples.append(make_instruction_format(
            "You are a scheduling assistant. Given a list of messages, identify which ones are high priority or urgent.",
            "\n".join(modified_group),
            "Priority analysis:\n" + "\n".join([
                f"- {'HIGH PRIORITY' if any(keyword in msg.upper() for keyword in urgent_keywords) else 'Normal priority'}: {msg}"
                for msg in modified_group
            ])
        ))

    # Time-based queries
    time_queries = [
        ("What meetings do I have in the morning?", "morning meetings"),
        ("What's scheduled for this afternoon?", "afternoon events"),
        ("Do I have any evening commitments?", "evening commitments")
    ]

    for entry in calendar_events[:10]:  # Just use first 10 for variety
        cal = entry["events"]
        for query, context in time_queries:
            examples.append(make_instruction_format(
                f"You are a scheduling assistant. Answer the user's question about their schedule: {query}",
                "\n".join(cal),
                f"Based on your schedule, here are your {context}: " +
                "; ".join([e.split(' - ')[-1] for e in cal if context.split()[0] in e.lower()])
            ))

    # Task completion examples
    completion_tasks = [
        "Mark the first event as completed",
        "Reschedule the afternoon meeting to tomorrow",
        "Add a reminder for the last event",
        "Cancel the middle event"
    ]

    for entry in calendar_events[:5]:
        cal = entry["events"]
        for task in completion_tasks:
            examples.append(make_instruction_format(
                f"You are a scheduling assistant. Perform the following task on the user's calendar: {task}",
                "\n".join(cal),
                f"I've processed your request to '{task}'. Your calendar has been updated accordingly."
            ))

    # Out-of-scope questions - instruction includes the question, no input needed
    unrelated_questions = [
        ("Who is the president of the USA?",
         "Sorry, I'm your scheduling assistant. I can only help with calendar events and messages."),
        ("What's the capital of France?",
         "Sorry, I'm your scheduling assistant. I can only help with calendar events and messages."),
        ("Can you write me a poem?",
         "Sorry, I'm your scheduling assistant. I can only help with calendar events and messages."),
        ("Explain quantum mechanics.",
         "Sorry, I'm your scheduling assistant. I can only help with calendar events and messages."),
        ("Tell me a joke.", "Sorry, I'm your scheduling assistant. I can only help with calendar events and messages."),
        ("What time is it?", "Sorry, I'm your scheduling assistant. I can only help with calendar events and messages.")
    ]

    for question, response in unrelated_questions:
        examples.append(make_instruction_format(
            f"You are a scheduling assistant. A user asked: '{question}'. Respond appropriately.",
            "",  # Empty input since instruction contains all necessary info
            response
        ))

    # Greeting and general assistant interactions
    greetings = [
        ("Hello",
         "Hello! I'm your scheduling assistant. I can help you with calendar events, messages, and schedule management."),
        ("Good morning", "Good morning! How can I help you with your schedule today?"),
        ("Hi there", "Hi! I'm here to help you manage your calendar and messages. What would you like to do?"),
        ("What can you do?",
         "I can help you with calendar events, summarize messages, identify priorities, and manage your schedule."),
        ("Help me",
         "I'm your scheduling assistant. I can help you view your calendar, summarize messages, find upcoming events, and manage your schedule.")
    ]

    for greeting, response in greetings:
        examples.append(make_instruction_format(
            f"You are a scheduling assistant. A user said: '{greeting}'. Respond appropriately.",
            "",  # Empty input since instruction contains all necessary info
            response
        ))

    # Shuffle to improve generalization
    random.shuffle(examples)

    # Save to JSONL
    with open(output_file, "w", encoding="utf-8") as f:
        for item in examples:
            f.write(json.dumps(item) + "\n")

    print(f"Generated {len(examples)} training examples in {output_file}")


# Generate dataset
if __name__ == "__main__":
    output_path = Path("train_data_instruction_format.jsonl")
    calendar_data = generate_calendar_events(datetime(2025, 6, 22), days=60)
    message_data = generate_messages() * 5

    generate_jsonl_dataset(calendar_data, message_data, output_path)

    # Print a few examples to verify format
    print("\nSample outputs:")
    with open(output_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i < 3:  # Show first 3 examples
                example = json.loads(line)
                print(f"\nExample {i + 1}:")
                print(f"Instruction: {example['instruction']}")
                print(f"Input: {example['input']}")
                print(f"Output: {example['output']}")
            else:
                break
