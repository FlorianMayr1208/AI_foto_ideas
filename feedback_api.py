"""
Flask Feedback API for AI Foto Ideas
Secure feedback collection with HMAC verification and rate limiting
"""

from flask import Flask, render_template, request, jsonify, abort
import json
import os
from datetime import datetime
import hmac
import hashlib
from pathlib import Path
from functools import wraps
import time
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Security configuration
SECRET_KEY = os.getenv('FEEDBACK_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("FEEDBACK_SECRET_KEY environment variable must be set!")

# Cookbook API configuration
COOKBOOK_API_URL = os.getenv('COOKBOOK_API_URL', 'https://cookbook-v3.vercel.app/api/remote')
COOKBOOK_OPENAI_KEY = os.getenv('OPENAI_API_KEY')  # Reuse the same OpenAI key

# File paths
BASE_DIR = Path(__file__).parent
FILE_MAP = {
    'photo': BASE_DIR / 'photo_challenges.json',
    'cooking': BASE_DIR / 'cooking_ideas.json',
    'diy': BASE_DIR / 'diy_projects.json'
}

# Simple in-memory rate limiting (resets on restart)
# For production, consider using Redis
RATE_LIMIT_STORE = {}
RATE_LIMIT_MAX = 10  # Max requests per IP per hour
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds


def verify_signature(idea_id, signature):
    """Verify HMAC signature to prevent tampering"""
    expected = hmac.new(
        SECRET_KEY.encode(),
        idea_id.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    return hmac.compare_digest(expected, signature)


def check_rate_limit(ip_address):
    """Simple rate limiting: max 10 requests per hour per IP"""
    now = time.time()

    if ip_address not in RATE_LIMIT_STORE:
        RATE_LIMIT_STORE[ip_address] = []

    # Remove old entries
    RATE_LIMIT_STORE[ip_address] = [
        timestamp for timestamp in RATE_LIMIT_STORE[ip_address]
        if now - timestamp < RATE_LIMIT_WINDOW
    ]

    # Check limit
    if len(RATE_LIMIT_STORE[ip_address]) >= RATE_LIMIT_MAX:
        return False

    # Add current timestamp
    RATE_LIMIT_STORE[ip_address].append(now)
    return True


def rate_limit(f):
    """Decorator for rate limiting"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get real IP (considering proxy headers from Cloudflare)
        ip = request.headers.get('CF-Connecting-IP') or \
             request.headers.get('X-Forwarded-For', '').split(',')[0] or \
             request.remote_addr

        if not check_rate_limit(ip):
            return jsonify({
                'error': 'Zu viele Anfragen. Bitte versuche es später noch einmal.'
            }), 429

        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'AI Foto Ideas Feedback API',
        'version': '1.0.0'
    })


@app.route('/health')
def health():
    """Health check for monitoring"""
    return jsonify({'status': 'healthy'}), 200


@app.route('/feedback/<idea_id>/<signature>')
@rate_limit
def feedback_form(idea_id, signature):
    """Display feedback form"""
    # Verify signature
    if not verify_signature(idea_id, signature):
        abort(403, "Ungültiger Feedback-Link. Bitte verwende den Link aus deiner E-Mail.")

    # Parse category from idea_id
    try:
        category = idea_id.split('_')[0]
        if category not in FILE_MAP:
            abort(400, "Ungültige Kategorie.")
    except (IndexError, ValueError):
        abort(400, "Ungültige Ideen-ID.")

    # Load idea details to show preview and feedback count
    idea_preview = None
    feedback_count = 0
    avg_rating = None

    try:
        with open(FILE_MAP[category], 'r', encoding='utf-8') as f:
            ideas = json.load(f)
            for idea in ideas:
                if idea.get('id') == idea_id:
                    # Get first 150 chars of challenge as preview
                    challenge_text = idea.get('challenge', '')
                    idea_preview = challenge_text[:150] + '...' if len(challenge_text) > 150 else challenge_text

                    # Count existing feedbacks
                    feedbacks = idea.get('feedbacks', [])
                    if isinstance(feedbacks, list):
                        feedback_count = len(feedbacks)
                        # Calculate average rating
                        ratings = [f['rating'] for f in feedbacks if f.get('rating')]
                        if ratings:
                            avg_rating = sum(ratings) / len(ratings)

                    break
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    return render_template('feedback.html',
                          idea_id=idea_id,
                          signature=signature,
                          category=category,
                          idea_preview=idea_preview,
                          feedback_count=feedback_count,
                          avg_rating=avg_rating)


@app.route('/api/feedback', methods=['POST'])
@rate_limit
def submit_feedback():
    """Submit feedback for an idea"""
    try:
        data = request.json

        # Validate required fields
        if not data or 'idea_id' not in data or 'signature' not in data:
            return jsonify({'error': 'Fehlende Pflichtfelder.'}), 400

        idea_id = data['idea_id']
        signature = data['signature']

        # Verify signature
        if not verify_signature(idea_id, signature):
            return jsonify({'error': 'Ungültige Anfrage.'}), 403

        # Parse category
        try:
            category = idea_id.split('_')[0]
        except (IndexError, ValueError):
            return jsonify({'error': 'Ungültige Ideen-ID.'}), 400

        if category not in FILE_MAP:
            return jsonify({'error': 'Ungültige Kategorie.'}), 400

        filepath = FILE_MAP[category]

        # Validate rating
        rating = data.get('rating')
        if not rating or not isinstance(rating, int) or not (1 <= rating <= 5):
            return jsonify({'error': 'Bewertung muss zwischen 1 und 5 liegen.'}), 400

        # Sanitize comment (max 1000 chars)
        comment = data.get('comment', '').strip()[:1000]

        # Get implemented status
        implemented = bool(data.get('implemented', False))

        # Update JSON file
        if not filepath.exists():
            return jsonify({'error': 'Datei nicht gefunden.'}), 404

        # Get user IP for tracking (optional)
        user_ip = request.headers.get('CF-Connecting-IP') or \
                  request.headers.get('X-Forwarded-For', '').split(',')[0] or \
                  request.remote_addr

        # Read, update, and write atomically
        try:
            with open(filepath, 'r+', encoding='utf-8') as f:
                ideas = json.load(f)

                idea_found = False
                for idea in ideas:
                    if idea.get('id') == idea_id:
                        # Ensure feedbacks array exists (for backward compatibility)
                        if 'feedbacks' not in idea:
                            idea['feedbacks'] = []

                        # Append new feedback to array
                        new_feedback = {
                            'rating': rating,
                            'comment': comment,
                            'implemented': implemented,
                            'submitted_at': datetime.now().isoformat(),
                            'ip_hash': hashlib.md5(user_ip.encode()).hexdigest()[:8]  # Anonymized IP
                        }
                        idea['feedbacks'].append(new_feedback)
                        idea_found = True

                        # Calculate new stats for response
                        feedback_count = len(idea['feedbacks'])
                        avg_rating = sum(f['rating'] for f in idea['feedbacks']) / feedback_count

                        break

                if not idea_found:
                    return jsonify({'error': 'Idee nicht gefunden.'}), 404

                # Write back to file
                f.seek(0)
                json.dump(ideas, f, indent=2, ensure_ascii=False)
                f.truncate()

            return jsonify({
                'status': 'success',
                'message': 'Feedback erfolgreich gespeichert!',
                'feedback_count': feedback_count,
                'avg_rating': round(avg_rating, 1)
            })

        except json.JSONDecodeError:
            return jsonify({'error': 'Fehler beim Lesen der Datei.'}), 500
        except PermissionError:
            return jsonify({'error': 'Keine Berechtigung zum Schreiben.'}), 500

    except Exception as e:
        app.logger.error(f"Error submitting feedback: {str(e)}")
        return jsonify({
            'error': 'Ein unerwarteter Fehler ist aufgetreten.'
        }), 500


@app.errorhandler(403)
def forbidden(e):
    """Custom 403 error page"""
    return render_template('error.html',
                          error_code=403,
                          error_message=str(e.description)), 403


@app.errorhandler(404)
def not_found(e):
    """Custom 404 error page"""
    return render_template('error.html',
                          error_code=404,
                          error_message="Seite nicht gefunden."), 404


@app.errorhandler(429)
def rate_limit_exceeded(e):
    """Custom 429 error page"""
    return render_template('error.html',
                          error_code=429,
                          error_message="Zu viele Anfragen. Bitte versuche es in einer Stunde noch einmal."), 429


@app.errorhandler(500)
def internal_error(e):
    """Custom 500 error page"""
    return render_template('error.html',
                          error_code=500,
                          error_message="Ein interner Fehler ist aufgetreten."), 500


@app.route('/api/import-recipe', methods=['POST'])
@rate_limit
def import_recipe():
    """Import a cooking idea into the cookbook app"""
    try:
        data = request.json

        # Validate required fields
        if not data or 'idea_id' not in data or 'signature' not in data:
            return jsonify({'error': 'Fehlende Pflichtfelder.'}), 400

        idea_id = data['idea_id']
        signature = data['signature']

        # Verify signature
        if not verify_signature(idea_id, signature):
            return jsonify({'error': 'Ungültige Anfrage.'}), 403

        # Parse category - only allow cooking
        try:
            category = idea_id.split('_')[0]
        except (IndexError, ValueError):
            return jsonify({'error': 'Ungültige Ideen-ID.'}), 400

        if category != 'cooking':
            return jsonify({'error': 'Import ist nur für Koch-Ideen verfügbar.'}), 400

        filepath = FILE_MAP[category]

        # Find the cooking idea
        if not filepath.exists():
            return jsonify({'error': 'Datei nicht gefunden.'}), 404

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                ideas = json.load(f)

            idea_text = None
            for idea in ideas:
                if idea.get('id') == idea_id:
                    idea_text = idea.get('challenge', '')
                    break

            if not idea_text:
                return jsonify({'error': 'Koch-Idee nicht gefunden.'}), 404

            # Prepare request to cookbook API
            cookbook_payload = {
                'text': idea_text
            }

            # Add API key if available
            if COOKBOOK_OPENAI_KEY:
                cookbook_payload['apiKey'] = COOKBOOK_OPENAI_KEY

            # Call the cookbook API
            app.logger.info(f"Calling cookbook API at {COOKBOOK_API_URL}")
            response = requests.post(
                COOKBOOK_API_URL,
                json=cookbook_payload,
                timeout=30  # 30 second timeout
            )

            # Check if request was successful
            if response.status_code != 200:
                error_msg = 'Fehler beim Importieren in das Kochbuch.'
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg = error_data['error']
                except:
                    pass
                app.logger.error(f"Cookbook API error: {response.status_code} - {response.text}")
                return jsonify({'error': error_msg}), 500

            # Parse response
            cookbook_response = response.json()

            if not cookbook_response.get('success'):
                return jsonify({
                    'error': 'Das Kochbuch konnte das Rezept nicht verarbeiten.'
                }), 500

            # Return the parsed recipe
            return jsonify({
                'status': 'success',
                'message': 'Rezept erfolgreich importiert!',
                'recipe': cookbook_response.get('recipe', {})
            })

        except json.JSONDecodeError:
            return jsonify({'error': 'Fehler beim Lesen der Datei.'}), 500
        except requests.Timeout:
            return jsonify({'error': 'Timeout beim Importieren. Bitte versuche es erneut.'}), 504
        except requests.RequestException as e:
            app.logger.error(f"Request error: {str(e)}")
            return jsonify({'error': 'Verbindungsfehler zum Kochbuch-Server.'}), 503

    except Exception as e:
        app.logger.error(f"Error importing recipe: {str(e)}")
        return jsonify({
            'error': 'Ein unerwarteter Fehler ist aufgetreten.'
        }), 500


if __name__ == '__main__':
    # Production settings
    app.run(
        host='127.0.0.1',  # Only listen on localhost (Cloudflare Tunnel will expose)
        port=5000,
        debug=False  # NEVER use debug=True in production!
    )
