#!/usr/bin/env python3
"""
Daily Ideas Generator
Generates creative daily challenges and ideas using OpenAI's GPT API
Supports: Photography, Cooking, DIY/Homemade projects
"""

import os
import json
import argparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Categories configuration
CATEGORIES = {
    "photo": {
        "name": "Foto-Challenge",
        "file": "photo_challenges.json",
        "system_prompt": "Du bist ein kreativer Fotografie-Lehrer, der inspirierende tägliche Foto-Herausforderungen erstellt. Antworte immer auf Deutsch.",
        "user_prompt": """Generiere eine kreative und inspirierende tägliche Fotografie-Herausforderung für den {date}.

Die Herausforderung sollte beinhalten:
1. Einen einprägsamen Titel
2. Eine kurze Beschreibung, was fotografiert werden soll
3. Technische Tipps oder Vorschläge
4. Kreative Inspiration oder Kontext

Halte es unterhaltsam, erreichbar und geeignet für Fotografen aller Erfahrungsstufen.{context}

WICHTIG: Erstelle eine NEUE und EINZIGARTIGE Herausforderung, die sich von den bisherigen unterscheidet."""
    },
    "cooking": {
        "name": "Koch-Idee",
        "file": "cooking_ideas.json",
        "system_prompt": "Du bist ein kreativer Koch und Ernährungsberater, der inspirierende tägliche Kochideen erstellt. Antworte immer auf Deutsch.",
        "user_prompt": """Generiere eine kreative und leckere tägliche Kochidee für den {date}.

Die Idee sollte beinhalten:
1. Einen appetitlichen Titel
2. Eine kurze Beschreibung des Gerichts
3. Hauptzutaten (ca. 5-7)
4. Besondere Tipps oder Variationen
5. Schwierigkeitsgrad und ungefähre Zeit

Halte es abwechslungsreich, saisonal wenn möglich, und für Hobbyköche machbar.{context}

WICHTIG: Erstelle eine NEUE und EINZIGARTIGE Idee, die sich von den bisherigen unterscheidet."""
    },
    "diy": {
        "name": "DIY-Projekt",
        "file": "diy_projects.json",
        "system_prompt": "Du bist ein kreativer DIY-Experte, der inspirierende Ideen zum Selbermachen erstellt. Antworte immer auf Deutsch.",
        "user_prompt": """Generiere eine kreative DIY-Idee zum Selbermachen für den {date}.

Die Idee sollte beinhalten:
1. Einen inspirierenden Titel
2. Was hergestellt wird (z.B. Marmelade, Seife, Deko, etc.)
3. Benötigte Materialien/Zutaten
4. Kurze Anleitung oder wichtige Schritte
5. Tipps und mögliche Variationen

Halte es kreativ, machbar und saisonal passend. Fokus auf hausgemachte Produkte wie Marmelade, eingelegtes Gemüse, Naturkosmetik, etc.{context}

WICHTIG: Erstelle eine NEUE und EINZIGARTIGE Idee, die sich von den bisherigen unterscheidet."""
    }
}

def load_challenges(filename):
    """Load previous challenges from file"""
    if not os.path.exists(filename):
        return []

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load history: {e}")
        return []

def save_challenge(filename, challenge_text):
    """Save a new challenge to the history file"""
    challenges = load_challenges(filename)

    new_challenge = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "challenge": challenge_text
    }

    challenges.append(new_challenge)

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(challenges, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warning: Could not save: {e}")

def generate_idea(category_key, previous_challenges):
    """Generate a daily idea/challenge using GPT API"""

    category = CATEGORIES[category_key]

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
        context = "\n\nBisher generierte Ideen (bitte NICHT wiederholen):\n"
        for ch in recent_challenges:
            context += f"- {ch['date']}: {ch['challenge'][:100]}...\n"

    # Create prompt using category template
    prompt = category["user_prompt"].format(date=today, context=context)

    try:
        # Call GPT API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": category["system_prompt"]},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=1000,
            temperature=1
        )

        # Extract and return the idea
        idea = response.choices[0].message.content
        return idea

    except Exception as e:
        raise Exception(f"Error generating idea: {str(e)}")

def send_email(to_email, ideas_dict):
    """Send an email with all three daily ideas"""

    # Get email configuration from environment variables
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')

    if not sender_email or not sender_password:
        raise ValueError("SENDER_EMAIL and SENDER_PASSWORD must be set in environment variables")

    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = f"Deine täglichen Ideen - {datetime.now().strftime('%d.%m.%Y')}"
    message["From"] = sender_email
    message["To"] = to_email

    # Create email body
    text_content = f"""
Hallo!

Hier sind deine täglichen Ideen für {datetime.now().strftime('%d.%m.%Y')}:

{'='*60}
FOTO-CHALLENGE
{'='*60}

{ideas_dict['photo']}

{'='*60}
KOCH-IDEE
{'='*60}

{ideas_dict['cooking']}

{'='*60}
DIY-PROJEKT
{'='*60}

{ideas_dict['diy']}

{'='*60}

Viel Spaß beim Ausprobieren!
"""

    html_content = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2>Deine täglichen Ideen für {datetime.now().strftime('%d.%m.%Y')}</h2>

    <hr>
    <h3 style="color: #2c5aa0;">📸 FOTO-CHALLENGE</h3>
    <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 10px 0;">
      {ideas_dict['photo'].replace(chr(10), '<br>')}
    </div>

    <hr>
    <h3 style="color: #d9534f;">🍳 KOCH-IDEE</h3>
    <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 10px 0;">
      {ideas_dict['cooking'].replace(chr(10), '<br>')}
    </div>

    <hr>
    <h3 style="color: #5cb85c;">🔨 DIY-PROJEKT</h3>
    <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 10px 0;">
      {ideas_dict['diy'].replace(chr(10), '<br>')}
    </div>

    <hr>
    <p style="color: #666; font-style: italic;">Viel Spaß beim Ausprobieren!</p>
  </body>
</html>
"""

    # Attach both plain text and HTML versions
    part1 = MIMEText(text_content, "plain")
    part2 = MIMEText(html_content, "html")
    message.attach(part1)
    message.attach(part2)

    # Send email
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, message.as_string())
        print(f"✓ Email erfolgreich an {to_email} gesendet!")
    except Exception as e:
        raise Exception(f"Fehler beim Senden der Email: {str(e)}")

def main():
    """Main function to run the daily ideas generator"""

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Täglicher Ideen-Generator für Foto-Challenges, Koch-Ideen und DIY-Projekte"
    )
    parser.add_argument(
        "category",
        nargs="?",
        choices=["photo", "cooking", "diy", "email"],
        help="Kategorie: photo (Fotografie), cooking (Kochen), diy (Selbermachen), email (alle per Email senden)"
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Email-Adresse für den Versand (nur mit 'email' Kategorie)"
    )

    args = parser.parse_args()

    # Email mode: generate all three ideas and send via email
    if args.category == "email":
        if not args.email:
            print("Fehler: Bitte gib eine Email-Adresse mit --email an")
            print("Beispiel: python main.py email --email deine@email.com")
            return 1

        print("=" * 60)
        print("TÄGLICHE IDEEN - EMAIL VERSAND")
        print("=" * 60)
        print()

        try:
            ideas_dict = {}

            # Generate ideas for all three categories
            for category_key in ["photo", "cooking", "diy"]:
                category = CATEGORIES[category_key]
                print(f"Generiere {category['name']}...")

                # Load previous ideas
                previous_ideas = load_challenges(category["file"])

                # Generate new idea
                idea = generate_idea(category_key, previous_ideas)
                ideas_dict[category_key] = idea

                # Save the idea
                save_challenge(category["file"], idea)
                print(f"✓ {category['name']} generiert und gespeichert!")

            print()
            print("Sende Email...")

            # Send email with all ideas
            send_email(args.email, ideas_dict)

            print()
            print("=" * 60)

        except Exception as e:
            print(f"Fehler: {e}")
            return 1

        return 0

    # Single category mode (original functionality)
    if not args.category:
        parser.print_help()
        return 1

    category_key = args.category
    category = CATEGORIES[category_key]

    # Print header
    print("=" * 60)
    print(f"TÄGLICHE {category['name'].upper()}")
    print("=" * 60)
    print()

    try:
        # Load previous ideas
        previous_ideas = load_challenges(category["file"])
        print(f"Geladen: {len(previous_ideas)} bisherige Ideen...")
        print()

        # Generate new idea
        idea = generate_idea(category_key, previous_ideas)
        print(idea)
        print()

        # Save the idea
        save_challenge(category["file"], idea)
        print(f"✓ {category['name']} gespeichert!")
        print()
        print("=" * 60)

    except Exception as e:
        print(f"Fehler: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
