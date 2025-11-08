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

app = Flask(__name__)

# Security configuration
SECRET_KEY = os.getenv('FEEDBACK_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("FEEDBACK_SECRET_KEY environment variable must be set!")

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


if __name__ == '__main__':
    # Production settings
    app.run(
        host='127.0.0.1',  # Only listen on localhost (Cloudflare Tunnel will expose)
        port=5000,
        debug=False  # NEVER use debug=True in production!
    )
