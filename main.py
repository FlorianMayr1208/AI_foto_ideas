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
import hmac
import hashlib
import secrets

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
4. Eine kurze Anleitung für die Zubereitung
4. Besondere Tipps oder Variationen
5. Schwierigkeitsgrad und ungefähre Zeit

Halte es abwechslungsreich, saisonal wenn möglich, und für Hobbyköche machbar.{context}

WICHTIG: Erstelle eine NEUE und EINZIGARTIGE Idee, die sich von den bisherigen unterscheidet. An geraden Tagen generiere eine fleischlose Variante, an ungeraden eine mit Fleisch."""
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

Halte es kreativ, machbar und saisonal passend. Fokus ausschließlich auf essbare/trinkbare Produkte: Marmeladen, Konfitueren, eingelegtes Gemüese/Obst, Sirups, Limonaden, Gewuerzmischungen, Aufstriche, Pesto, fermentierte Produkte, Kräuteröle, etc.{context}

WICHTIG: Erstelle eine NEUE und EINZIGARTIGE Idee, die sich von den bisherigen unterscheidet. Schreib die Ideen in Oesterreichischem Deutsch."""
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

def generate_idea_id(category_key):
    """Generate a unique ID for an idea"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    random_suffix = secrets.token_hex(4)  # 8 character random hex
    return f"{category_key}_{date_str}_{random_suffix}"

def save_challenge(filename, challenge_text, category_key):
    """Save a new challenge to the history file with feedback structure"""
    challenges = load_challenges(filename)

    new_challenge = {
        "id": generate_idea_id(category_key),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "challenge": challenge_text,
        "feedbacks": []  # Array to store multiple feedbacks
    }

    challenges.append(new_challenge)

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(challenges, f, ensure_ascii=False, indent=2)
        return new_challenge["id"]
    except Exception as e:
        print(f"Warning: Could not save: {e}")
        return None

def generate_feedback_url(idea_id):
    """Generate a signed feedback URL for an idea"""
    secret_key = os.getenv('FEEDBACK_SECRET_KEY')
    if not secret_key:
        print("Warning: FEEDBACK_SECRET_KEY not set. Feedback links will not work!")
        return None

    # Generate HMAC signature
    signature = hmac.new(
        secret_key.encode(),
        idea_id.encode(),
        hashlib.sha256
    ).hexdigest()[:16]

    # Get base URL from environment or use default
    base_url = os.getenv('FEEDBACK_BASE_URL', 'http://localhost:5000')

    return f"{base_url}/feedback/{idea_id}/{signature}"

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

    # Prepare context from previous challenges (last 10) AND their feedback
    context = ""
    feedback_context = ""

    if previous_challenges:
        recent_challenges = previous_challenges[-10:]  # Get last 10 challenges
        context = "\n\nBisher generierte Ideen (bitte NICHT wiederholen):\n"

        # Collect feedback insights
        highly_rated = []
        poorly_rated = []
        implemented = []

        for ch in recent_challenges:
            context += f"- {ch['date']}: {ch['challenge'][:100]}...\n"

            # Analyze feedbacks if available (support both old 'feedback' and new 'feedbacks')
            feedbacks_list = []

            # Support new format (feedbacks array)
            if ch.get('feedbacks') and isinstance(ch['feedbacks'], list):
                feedbacks_list = ch['feedbacks']
            # Support old format (single feedback object) for backward compatibility
            elif ch.get('feedback') and ch['feedback'].get('rating'):
                feedbacks_list = [ch['feedback']]

            if feedbacks_list:
                # Calculate average rating
                ratings = [f['rating'] for f in feedbacks_list if f.get('rating')]
                if ratings:
                    avg_rating = sum(ratings) / len(ratings)
                    feedback_count = len(ratings)

                    challenge_preview = ch['challenge'][:80]

                    if avg_rating >= 4:
                        highly_rated.append(
                            f"{challenge_preview}... (⭐ {avg_rating:.1f}/5 von {feedback_count} Personen)"
                        )
                    elif avg_rating <= 2:
                        poorly_rated.append(
                            f"{challenge_preview}... (⭐ {avg_rating:.1f}/5 von {feedback_count} Personen)"
                        )

                # Check if anyone implemented it
                implemented_count = sum(1 for f in feedbacks_list if f.get('implemented'))
                if implemented_count > 0:
                    implemented.append(
                        f"{ch['challenge'][:80]}... ({implemented_count} Person(en) haben es umgesetzt)"
                    )

        # Add feedback insights to prompt
        if highly_rated or poorly_rated or implemented:
            feedback_context = "\n\n📊 FEEDBACK-INSIGHTS (bitte beachten):\n"

            if highly_rated:
                feedback_context += "\n✅ Sehr gut bewertet (mehr davon!):\n"
                for item in highly_rated:
                    feedback_context += f"- {item}\n"

            if implemented:
                feedback_context += "\n🎯 Wurden umgesetzt (funktionierten gut!):\n"
                for item in implemented[:3]:  # Top 3
                    feedback_context += f"- {item}...\n"

            if poorly_rated:
                feedback_context += "\n⚠️ Schlecht bewertet (solche vermeiden!):\n"
                for item in poorly_rated:
                    feedback_context += f"- {item}\n"

    # Create prompt using category template
    prompt = category["user_prompt"].format(date=today, context=context + feedback_context)

    try:
        # Call GPT API
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": category["system_prompt"]},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=3000,
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

def send_email(to_emails, ideas_dict, idea_ids_dict):
    """Send an email with all three daily ideas and feedback links

    Args:
        to_emails: List of email addresses or single email address string
        ideas_dict: Dictionary of generated ideas
        idea_ids_dict: Dictionary of idea IDs
    """

    # Ensure to_emails is a list
    if isinstance(to_emails, str):
        to_emails = [to_emails]

    # Get email configuration from environment variables
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')

    if not sender_email or not sender_password:
        raise ValueError("SENDER_EMAIL and SENDER_PASSWORD must be set in environment variables")

    # Generate feedback URLs
    feedback_urls = {}
    for category_key, idea_id in idea_ids_dict.items():
        if idea_id:
            url = generate_feedback_url(idea_id)
            feedback_urls[category_key] = url if url else ""
        else:
            feedback_urls[category_key] = ""

    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = f"Deine täglichen Ideen - {datetime.now().strftime('%d.%m.%Y')}"
    message["From"] = sender_email
    message["To"] = ", ".join(to_emails)  # Multiple recipients separated by comma

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

--- Feedback Links ---
Foto: {feedback_urls.get('photo', 'N/A')}
Kochen: {feedback_urls.get('cooking', 'N/A')}
DIY: {feedback_urls.get('diy', 'N/A')}
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
      {f'''<div style="text-align: center; margin: 15px 0;">
        <a href="{feedback_urls.get('photo', '')}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 12px 30px; border-radius: 25px; font-weight: 600; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
          💬 Feedback geben
        </a>
      </div>''' if feedback_urls.get('photo') else ''}
    </div>

    <div style="margin: 30px 0;">
      <h3 style="color: #d9534f; background-color: #ffe8e8; padding: 10px; border-left: 4px solid #d9534f;">
        🍳 KOCH-IDEE
      </h3>
      <div style="background-color: #f9f9f9; padding: 20px; border-radius: 5px; margin: 10px 0;">
        {cooking_html}
      </div>
      {f'''<div style="text-align: center; margin: 15px 0;">
        <a href="{feedback_urls.get('cooking', '')}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 12px 30px; border-radius: 25px; font-weight: 600; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
          💬 Feedback geben
        </a>
      </div>''' if feedback_urls.get('cooking') else ''}
    </div>

    <div style="margin: 30px 0;">
      <h3 style="color: #5cb85c; background-color: #e8ffe8; padding: 10px; border-left: 4px solid #5cb85c;">
        🔨 DIY-PROJEKT
      </h3>
      <div style="background-color: #f9f9f9; padding: 20px; border-radius: 5px; margin: 10px 0;">
        {diy_html}
      </div>
      {f'''<div style="text-align: center; margin: 15px 0;">
        <a href="{feedback_urls.get('diy', '')}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 12px 30px; border-radius: 25px; font-weight: 600; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
          💬 Feedback geben
        </a>
      </div>''' if feedback_urls.get('diy') else ''}
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
            server.sendmail(sender_email, to_emails, message.as_string())

        if len(to_emails) == 1:
            print(f"✓ Email erfolgreich an {to_emails[0]} gesendet!")
        else:
            print(f"✓ Email erfolgreich an {len(to_emails)} Empfänger gesendet!")
            for email in to_emails:
                print(f"  - {email}")
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
        action='append',
        help="Email-Adresse(n) für den Versand (kann mehrmals verwendet werden oder komma-separiert)"
    )

    args = parser.parse_args()

    # Email mode: generate all three ideas and send via email
    if args.category == "email":
        if not args.email:
            print("Fehler: Bitte gib mindestens eine Email-Adresse mit --email an")
            print("Beispiele:")
            print("  python main.py email --email deine@email.com")
            print("  python main.py email --email email1@example.com --email email2@example.com")
            print("  python main.py email --email 'email1@example.com,email2@example.com'")
            return 1

        # Parse email addresses (support both multiple --email flags and comma-separated)
        email_list = []
        for email_arg in args.email:
            # Split by comma in case user provided comma-separated emails
            emails = [e.strip() for e in email_arg.split(',')]
            email_list.extend(emails)

        # Remove duplicates and empty strings
        email_list = list(set(filter(None, email_list)))

        if not email_list:
            print("Fehler: Keine gültige Email-Adresse angegeben")
            return 1

        print(f"Sende an {len(email_list)} Empfänger: {', '.join(email_list)}")
        print()

        print("=" * 60)
        print("TÄGLICHE IDEEN - EMAIL VERSAND")
        print("=" * 60)
        print()

        try:
            ideas_dict = {}
            idea_ids_dict = {}

            # Generate ideas for all three categories
            for category_key in ["photo", "cooking", "diy"]:
                category = CATEGORIES[category_key]
                print(f"Generiere {category['name']}...")

                # Load previous ideas
                previous_ideas = load_challenges(category["file"])

                # Generate new idea
                idea = generate_idea(category_key, previous_ideas)
                ideas_dict[category_key] = idea

                # Save the idea and get its ID
                idea_id = save_challenge(category["file"], idea, category_key)
                idea_ids_dict[category_key] = idea_id
                print(f"✓ {category['name']} generiert und gespeichert!")

            print()
            print("Sende Emails...")

            # Send email with all ideas and their IDs
            send_email(email_list, ideas_dict, idea_ids_dict)

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
        idea_id = save_challenge(category["file"], idea, category_key)
        print(f"✓ {category['name']} gespeichert!")

        # Show feedback URL if available
        if idea_id:
            feedback_url = generate_feedback_url(idea_id)
            if feedback_url:
                print(f"📝 Feedback-URL: {feedback_url}")

        print()
        print("=" * 60)

    except Exception as e:
        print(f"Fehler: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
