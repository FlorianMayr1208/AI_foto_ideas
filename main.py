#!/usr/bin/env python3
"""
Daily Photo Challenge Generator
Generates creative photography challenges using OpenAI's GPT API
"""

import os
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# File to store challenges
CHALLENGES_FILE = "challenges_history.json"

def load_challenges():
    """Load previous challenges from file"""
    if not os.path.exists(CHALLENGES_FILE):
        return []

    try:
        with open(CHALLENGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load challenges history: {e}")
        return []

def save_challenge(challenge_text):
    """Save a new challenge to the history file"""
    challenges = load_challenges()

    new_challenge = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "challenge": challenge_text
    }

    challenges.append(new_challenge)

    try:
        with open(CHALLENGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(challenges, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warning: Could not save challenge: {e}")

def generate_photo_challenge(previous_challenges):
    """Generate a daily photo challenge using GPT API"""

    # Initialize OpenAI client
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    client = OpenAI(api_key=api_key)

    # Get current date for context
    today = datetime.now().strftime("%B %d, %Y")

    # Prepare context from previous challenges (last 10)
    context = ""
    if previous_challenges:
        recent_challenges = previous_challenges[-10:]  # Get last 10 challenges
        context = "\n\nBisher generierte Herausforderungen (bitte NICHT wiederholen):\n"
        for ch in recent_challenges:
            context += f"- {ch['date']}: {ch['challenge'][:100]}...\n"

    # Create prompt for photo challenge
    prompt = f"""Generiere eine kreative und inspirierende tägliche Fotografie-Herausforderung für den {today}. Halte dich kurz.

Die Herausforderung sollte beinhalten:
1. Einen einprägsamen Titel
2. Eine kurze Beschreibung, was fotografiert werden soll
3. Technische Tipps oder Vorschläge
4. Kreative Inspiration oder Kontext

Halte es unterhaltsam, erreichbar und geeignet für Fotografen aller Erfahrungsstufen.{context}

WICHTIG: Erstelle eine NEUE und EINZIGARTIGE Herausforderung, die sich von den bisherigen unterscheidet."""

    try:
        # Call GPT API
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "Du bist ein kreativer Fotografie-Lehrer, der inspirierende tägliche Foto-Herausforderungen erstellt. Antworte immer auf Deutsch."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=1000,
            temperature=1
        )

        # Extract and return the challenge
        challenge = response.choices[0].message.content
        return challenge

    except Exception as e:
        raise Exception(f"Error generating challenge: {str(e)}")

def main():
    """Main function to run the photo challenge generator"""
    print("=" * 60)
    print("DAILY PHOTO CHALLENGE")
    print("=" * 60)
    print()

    try:
        # Load previous challenges
        previous_challenges = load_challenges()
        print(f"Loaded {len(previous_challenges)} previous challenges...")
        print()

        # Generate new challenge
        challenge = generate_photo_challenge(previous_challenges)
        print(challenge)
        print()

        # Save the challenge
        save_challenge(challenge)
        print("Challenge saved to history!")
        print()
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
