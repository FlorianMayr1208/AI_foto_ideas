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
        "system_prompt": "Du bist ein kreativer DIY-Experte für hausgemachte Lebensmittel und Getränke. Antworte immer auf Deutsch.",
        "user_prompt": """Generiere eine kreative DIY-Idee für selbstgemachte Lebensmittel oder Getränke für den {date}.

Die Idee sollte beinhalten:
1. Einen inspirierenden Titel
2. Was hergestellt wird (z.B. Marmelade, Sirup, eingelegtes Gemüse, Limonade, Gewürzmischung, Aufstrich, Pesto, etc.)
3. Benötigte Zutaten
4. Kurze Anleitung oder wichtige Schritte
5. Tipps zur Haltbarkeit und mögliche Variationen

Halte es kreativ, machbar und saisonal passend. Fokus ausschließlich auf essbare/trinkbare Produkte: Marmeladen, Konfitüren, eingelegtes Gemüse/Obst, Sirups, Limonaden, Gewürzmischungen, Aufstriche, Pesto, fermentierte Produkte, Kräuteröle, etc.{context}

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

def convert_markdown_to_html(text):
    """Convert basic markdown formatting to HTML"""
    import re
    import html

    # Escape HTML characters first
    text = html.escape(text)

    # Convert markdown headers (### Header -> <h4>)
    text = re.sub(r'###\s+(.+?)(?=\n|$)', r'<h4 style="margin: 10px 0; color: #2c5aa0;">\1</h4>', text)

    # Convert bold text (**text** -> <strong>)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    # Convert numbered lists (1. Item -> <ol><li>)
    lines = text.split('\n')
    in_ordered_list = False
    in_unordered_list = False
    result_lines = []

    for line in lines:
        # Check for numbered list
        if re.match(r'^\d+\.\s+', line):
            if not in_ordered_list:
                result_lines.append('<ol style="margin: 10px 0; padding-left: 20px;">')
                in_ordered_list = True
            if in_unordered_list:
                result_lines.append('</ul>')
                in_unordered_list = False
            # Remove the number and add as list item
            item = re.sub(r'^\d+\.\s+', '', line)
            result_lines.append(f'<li style="margin: 5px 0;">{item}</li>')
        # Check for unordered list (- Item)
        elif re.match(r'^-\s+', line):
            if not in_unordered_list:
                result_lines.append('<ul style="margin: 10px 0; padding-left: 20px;">')
                in_unordered_list = True
            if in_ordered_list:
                result_lines.append('</ol>')
                in_ordered_list = False
            # Remove the dash and add as list item
            item = re.sub(r'^-\s+', '', line)
            result_lines.append(f'<li style="margin: 5px 0;">{item}</li>')
        else:
            # Close any open lists
            if in_ordered_list:
                result_lines.append('</ol>')
                in_ordered_list = False
            if in_unordered_list:
                result_lines.append('</ul>')
                in_unordered_list = False
            # Add line with br if not empty
            if line.strip():
                result_lines.append(line + '<br>')
            else:
                result_lines.append('<br>')

    # Close any remaining open lists
    if in_ordered_list:
        result_lines.append('</ol>')
    if in_unordered_list:
        result_lines.append('</ul>')

    text = '\n'.join(result_lines)

    # Clean up multiple <br> tags
    text = re.sub(r'(<br>\s*){3,}', '<br><br>', text)

    return text

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

    # Convert markdown content to HTML
    photo_html = convert_markdown_to_html(ideas_dict['photo'])
    cooking_html = convert_markdown_to_html(ideas_dict['cooking'])
    diy_html = convert_markdown_to_html(ideas_dict['diy'])

    html_content = f"""
<html>
  <head>
    <meta charset="UTF-8">
  </head>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #2c5aa0; border-bottom: 2px solid #2c5aa0; padding-bottom: 10px;">
      Deine täglichen Ideen für {datetime.now().strftime('%d.%m.%Y')}
    </h2>

    <div style="margin: 30px 0;">
      <h3 style="color: #2c5aa0; background-color: #e8f0ff; padding: 10px; border-left: 4px solid #2c5aa0;">
        📸 FOTO-CHALLENGE
      </h3>
      <div style="background-color: #f9f9f9; padding: 20px; border-radius: 5px; margin: 10px 0;">
        {photo_html}
      </div>
    </div>

    <div style="margin: 30px 0;">
      <h3 style="color: #d9534f; background-color: #ffe8e8; padding: 10px; border-left: 4px solid #d9534f;">
        🍳 KOCH-IDEE
      </h3>
      <div style="background-color: #f9f9f9; padding: 20px; border-radius: 5px; margin: 10px 0;">
        {cooking_html}
      </div>
    </div>

    <div style="margin: 30px 0;">
      <h3 style="color: #5cb85c; background-color: #e8ffe8; padding: 10px; border-left: 4px solid #5cb85c;">
        🔨 DIY-PROJEKT
      </h3>
      <div style="background-color: #f9f9f9; padding: 20px; border-radius: 5px; margin: 10px 0;">
        {diy_html}
      </div>
    </div>

    <hr style="border: none; border-top: 1px solid #ccc; margin: 30px 0;">
    <p style="color: #666; font-style: italic; text-align: center;">
      Viel Spaß beim Ausprobieren!
    </p>
  </body>
</html>
"""

    # Attach both plain text and HTML versions
    part1 = MIMEText(text_content, "plain", "utf-8")
    part2 = MIMEText(html_content, "html", "utf-8")
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
