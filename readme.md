# AI Foto Ideas

**Automatically generate and send daily creative ideas for photography, cooking, and DIY projects using GPT-4!**

This project generates unique daily challenges and ideas, sends them via email, and collects user feedback to continuously improve future suggestions.

---

## ✨ Features

- 📸 **Photo Challenges** - Creative photography ideas
- 🥬 **Vegetarian Cooking** - Delicious vegetarian and vegan recipes
- 🍖 **Meat Cooking** - Recipes with meat or fish
- 🔨 **DIY Projects** - Homemade food and drink projects
- 📧 **Email Delivery** - Send to multiple recipients
- 💬 **Feedback System** - Collect user ratings and comments
- 🤖 **GPT Learning** - AI improves based on feedback
- 🔐 **Secure** - HMAC signatures, rate limiting, HTTPS
- 🆓 **Free Hosting** - Self-hosted with Cloudflare Tunnel

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
nano .env
```

Add your API keys and configuration.

### 3. Generate Ideas

#### Single Category
```bash
# Generate a photo challenge
python main.py photo

# Generate a vegetarian cooking idea
python main.py cooking_veggie

# Generate a cooking idea with meat
python main.py cooking_meat

# Generate a DIY project
python main.py diy
```

#### Send via Email (Multiple Recipients)

**Option 1: Multiple --email flags**
```bash
python main.py email --email friend1@example.com --email friend2@example.com
```

**Option 2: Comma-separated**
```bash
python main.py email --email "friend1@example.com,friend2@example.com"
```

**Option 3: Mix both**
```bash
python main.py email --email friend1@example.com --email "friend2@example.com,friend3@example.com"
```

---

## 💬 Feedback System

The feedback system allows **multiple users** to rate and comment on the same ideas, creating a collective intelligence that helps GPT generate better suggestions over time.

### Key Features
- 👥 **Multiple Feedbacks per Idea** - Everyone can give feedback on the same idea
- 📊 **Average Ratings** - See what the group thinks (e.g., ⭐ 4.3/5 from 3 people)
- 💭 **Individual Comments** - Each person can share their unique perspective
- 🔒 **Same Link for All** - Share one feedback link with multiple people
- 📈 **Real-time Stats** - Shows feedback count and average rating

### Setup Instructions

See **[CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md)** for complete setup instructions including:
- Flask API configuration
- Cloudflare Tunnel setup (free HTTPS)
- Systemd auto-start services
- Security best practices

---

## 📊 How It Works

1. **Generate Ideas** - GPT-4 creates unique daily challenges
2. **Send Emails** - Ideas delivered to multiple recipients with feedback buttons
3. **Collect Feedback** - Each person can rate ideas (1-5 stars) and add comments
4. **Aggregate Insights** - System calculates average ratings and tracks implementations
5. **Learn & Improve** - GPT uses collective feedback to generate better ideas:
   - ✅ More ideas similar to highly-rated ones (avg ≥ 4 stars)
   - ⚠️ Avoids patterns from poorly-rated ideas (avg ≤ 2 stars)
   - 🎯 Prioritizes ideas that people actually implemented

---

## 📁 Project Structure

```
AI_foto_ideas/
├── main.py                          # Main idea generator
├── feedback_api.py                  # Flask feedback API
├── templates/                       # HTML templates for feedback
│   ├── feedback.html
│   ├── feedback_already_submitted.html
│   └── error.html
├── systemd/                         # Auto-start service files
│   ├── ai-foto-feedback.service
│   └── cloudflared-tunnel.service
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment configuration template
├── CLOUDFLARE_TUNNEL_SETUP.md      # Complete setup guide
└── readme.md                        # This file
```

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# Email (Gmail example)
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Feedback System
FEEDBACK_SECRET_KEY=generate_with_python_secrets
FEEDBACK_BASE_URL=https://your-tunnel-url.trycloudflare.com
```

### Generate Secret Key
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🔐 Security Features

- **HMAC Signatures** - Feedback links can't be tampered with
- **Rate Limiting** - Max 10 requests/hour per IP
- **Input Validation** - Prevents XSS and injection attacks
- **HTTPS** - Automatic via Cloudflare Tunnel
- **Localhost Binding** - Flask only accessible via tunnel
- **No Port Forwarding** - No router configuration needed

---

## 📖 Usage Examples

### Generate and Email to Multiple People

```bash
# Send to you and your friend
python main.py email --email you@example.com --email friend@example.com
```

### Automate with Cron

Add to crontab to send daily at 8 AM:
```bash
crontab -e

# Add this line:
0 8 * * * cd /home/user/AI_foto_ideas && /usr/bin/python3 main.py email --email your@email.com
```

---

## 🛠️ Troubleshooting

### Email not sending
- Check SMTP credentials in `.env`
- For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833)
- Verify `SENDER_EMAIL` and `SENDER_PASSWORD` are set

### Feedback links not working
- Make sure Flask API is running: `python3 feedback_api.py`
- Check Cloudflare Tunnel is active
- Verify `FEEDBACK_BASE_URL` matches your tunnel URL
- Generate new secret key if needed

### GPT not learning from feedback
- Ensure JSON files contain feedback data
- Check that `feedback.rating` is not null
- Verify OpenAI API key has access to GPT-4

---

## 📝 License

This project is for personal use.

---

## 🤝 Contributing

Feel free to fork and modify for your own use!

---

## 📞 Support

For detailed setup instructions, see:
- **[CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md)** - Complete hosting guide
- **[systemd/README.md](systemd/README.md)** - Auto-start configuration

---

**Happy creating! 🎨📸🍳**