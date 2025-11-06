# Cloudflare Tunnel Setup Guide

This guide will help you set up the feedback system using **Cloudflare Tunnel** for secure self-hosting.

## 🎯 What You'll Achieve

- ✅ Flask feedback API running on your local machine
- ✅ Publicly accessible via HTTPS (automatic SSL)
- ✅ No router configuration needed (no port forwarding)
- ✅ Free forever
- ✅ Secure with HMAC verification and rate limiting

---

## 📋 Prerequisites

- A computer running Linux (or Mac/Windows with minor adaptations)
- Python 3.8 or higher installed
- Internet connection
- Cloudflare account (free)

---

## 🚀 Step 1: Install Dependencies

```bash
# Navigate to your project directory
cd /home/user/AI_foto_ideas

# Install Python dependencies
pip3 install -r requirements.txt
```

---

## 🔐 Step 2: Configure Environment Variables

### Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output (it will be a 64-character hex string).

### Update your `.env` file:

```bash
cp .env.example .env
nano .env
```

Add/update these values:

```bash
# Your existing values
OPENAI_API_KEY=your_openai_api_key
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password

# NEW: Feedback configuration
FEEDBACK_SECRET_KEY=paste_the_64_char_hex_you_generated_above
FEEDBACK_BASE_URL=https://your-tunnel-url.trycloudflare.com  # We'll update this later
```

**Important:** Keep your `FEEDBACK_SECRET_KEY` secret! Don't commit it to Git.

---

## 🧪 Step 3: Test the Flask API Locally

Before setting up the tunnel, make sure the API works:

```bash
# Run the Flask app
python3 feedback_api.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
```

**Test it:** Open a new terminal and run:
```bash
curl http://127.0.0.1:5000/health
```

Expected response:
```json
{"status":"healthy"}
```

Press `Ctrl+C` to stop the Flask app.

---

## ☁️ Step 4: Install Cloudflare Tunnel

### Download cloudflared:

```bash
# Download the latest version
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64

# Make it executable
chmod +x cloudflared-linux-amd64

# Move to a system directory (optional but recommended)
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

# Verify installation
cloudflared --version
```

You should see something like: `cloudflared version 2024.x.x`

---

## 🌐 Step 5: Create a Quick Tunnel (Testing)

First, let's test with a **temporary tunnel** (no Cloudflare account needed):

```bash
# In one terminal, start Flask:
python3 feedback_api.py
```

**In another terminal, start the tunnel:**

```bash
cloudflared tunnel --url http://127.0.0.1:5000
```

You'll see output like:
```
2025-11-06T10:23:45Z INF +--------------------------------------------------------------------------------------------+
2025-11-06T10:23:45Z INF |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable): |
2025-11-06T10:23:45Z INF |  https://randomly-generated-name.trycloudflare.com                                        |
2025-11-06T10:23:45Z INF +--------------------------------------------------------------------------------------------+
```

**Copy that URL!** That's your public URL.

### Test it:

Open the URL in your browser (or curl):
```bash
curl https://randomly-generated-name.trycloudflare.com/health
```

You should see: `{"status":"healthy"}`

🎉 **Congratulations!** Your Flask API is now publicly accessible!

**⚠️ Important:** This URL changes every time you restart the tunnel. For production, see Step 6.

---

## 🔒 Step 6: Create a Persistent Tunnel (Recommended)

For a permanent tunnel with a fixed URL, you need a Cloudflare account:

### 1. Login to Cloudflare:

```bash
cloudflared tunnel login
```

This will open a browser window. Log in to your Cloudflare account and select a website (or create a free one).

### 2. Create a named tunnel:

```bash
cloudflared tunnel create ai-foto-feedback
```

You'll see output like:
```
Tunnel credentials written to: /home/user/.cloudflared/UUID.json
Created tunnel ai-foto-feedback with id UUID
```

### 3. Create a configuration file:

```bash
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

Paste this configuration:

```yaml
tunnel: ai-foto-feedback
credentials-file: /home/user/.cloudflared/UUID.json

ingress:
  - hostname: feedback.yourdomain.com
    service: http://127.0.0.1:5000
  - service: http_status:404
```

**Replace:**
- `UUID` with the actual UUID from step 2
- `feedback.yourdomain.com` with your desired subdomain

### 4. Create DNS record:

```bash
cloudflared tunnel route dns ai-foto-feedback feedback.yourdomain.com
```

### 5. Run the tunnel:

```bash
cloudflared tunnel run ai-foto-feedback
```

Your tunnel is now accessible at `https://feedback.yourdomain.com`!

---

## ⚙️ Step 7: Update Environment Variables

Now that you have your public URL, update `.env`:

```bash
nano .env
```

Update this line:

```bash
FEEDBACK_BASE_URL=https://your-actual-tunnel-url.trycloudflare.com
# OR if using persistent tunnel:
FEEDBACK_BASE_URL=https://feedback.yourdomain.com
```

**Restart Flask** for changes to take effect.

---

## 🤖 Step 8: Set Up Auto-Start with Systemd

To keep everything running automatically, even after reboot:

### 1. Create Flask service:

```bash
sudo nano /etc/systemd/system/ai-foto-feedback.service
```

Paste this:

```ini
[Unit]
Description=AI Foto Ideas Feedback API
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/user/AI_foto_ideas
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /home/user/AI_foto_ideas/feedback_api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Replace `YOUR_USERNAME`** with your actual Linux username.

### 2. Create Cloudflare Tunnel service:

```bash
sudo nano /etc/systemd/system/cloudflared-tunnel.service
```

**For quick tunnel (temporary URL):**

```ini
[Unit]
Description=Cloudflare Tunnel
After=network.target ai-foto-feedback.service

[Service]
Type=simple
User=YOUR_USERNAME
ExecStart=/usr/local/bin/cloudflared tunnel --url http://127.0.0.1:5000 --no-autoupdate
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**OR for persistent tunnel:**

```ini
[Unit]
Description=Cloudflare Tunnel
After=network.target ai-foto-feedback.service

[Service]
Type=simple
User=YOUR_USERNAME
ExecStart=/usr/local/bin/cloudflared tunnel --no-autoupdate run ai-foto-feedback
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. Enable and start services:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable ai-foto-feedback.service
sudo systemctl enable cloudflared-tunnel.service

# Start services now
sudo systemctl start ai-foto-feedback.service
sudo systemctl start cloudflared-tunnel.service

# Check status
sudo systemctl status ai-foto-feedback.service
sudo systemctl status cloudflared-tunnel.service
```

### 4. View logs:

```bash
# Flask API logs
sudo journalctl -u ai-foto-feedback.service -f

# Cloudflare Tunnel logs
sudo journalctl -u cloudflared-tunnel.service -f
```

---

## 🧪 Step 9: Test End-to-End

### 1. Generate a test idea:

```bash
python3 main.py photo
```

You should see a feedback URL at the end!

### 2. Open the URL:

Copy the feedback URL and open it in your browser. You should see the beautiful feedback form!

### 3. Submit feedback:

Fill out the form and submit. Check your JSON file:

```bash
cat photo_challenges.json | jq '.[].feedback'
```

You should see your feedback stored!

### 4. Send a test email:

```bash
python3 main.py email --email your@email.com
```

Open the email and click the feedback buttons!

---

## 🔒 Security Best Practices

### ✅ What's already secured:

1. **HMAC signatures** - Feedback links can't be tampered with
2. **Rate limiting** - Max 10 requests/hour per IP
3. **Input validation** - Prevents malicious input
4. **HTTPS** - Automatic with Cloudflare Tunnel
5. **Localhost binding** - Flask only listens on 127.0.0.1

### 🛡️ Additional recommendations:

1. **Firewall:**
   ```bash
   # Ensure port 5000 is NOT exposed externally
   sudo ufw status
   # If 5000 is open, close it:
   sudo ufw deny 5000
   ```

2. **Keep secrets safe:**
   - Never commit `.env` to Git (already in `.gitignore`)
   - Use strong passwords for email
   - Rotate `FEEDBACK_SECRET_KEY` if compromised

3. **Monitor logs:**
   ```bash
   # Watch for suspicious activity
   sudo journalctl -u ai-foto-feedback.service | grep -i error
   ```

4. **Update regularly:**
   ```bash
   pip3 install --upgrade flask openai python-dotenv
   cloudflared update
   ```

---

## 📊 Useful Commands

### Check service status:
```bash
sudo systemctl status ai-foto-feedback.service
sudo systemctl status cloudflared-tunnel.service
```

### Restart services:
```bash
sudo systemctl restart ai-foto-feedback.service
sudo systemctl restart cloudflared-tunnel.service
```

### Stop services:
```bash
sudo systemctl stop ai-foto-feedback.service
sudo systemctl stop cloudflared-tunnel.service
```

### View real-time logs:
```bash
sudo journalctl -u ai-foto-feedback.service -f
sudo journalctl -u cloudflared-tunnel.service -f
```

### Test API manually:
```bash
# Health check
curl https://your-tunnel-url.trycloudflare.com/health

# Check if Flask is running locally
curl http://127.0.0.1:5000/health
```

---

## 🐛 Troubleshooting

### Problem: "FEEDBACK_SECRET_KEY not found"

**Solution:** Make sure `.env` file exists and contains `FEEDBACK_SECRET_KEY`:
```bash
cat .env | grep FEEDBACK_SECRET_KEY
```

---

### Problem: Cloudflare Tunnel URL changes every restart

**Solution:** Use a persistent tunnel (Step 6) instead of quick tunnel.

---

### Problem: "Connection refused" when accessing tunnel URL

**Solution:**
1. Check if Flask is running: `curl http://127.0.0.1:5000/health`
2. Check Flask logs: `sudo journalctl -u ai-foto-feedback.service -f`
3. Restart services: `sudo systemctl restart ai-foto-feedback.service cloudflared-tunnel.service`

---

### Problem: Feedback not saving

**Solution:**
1. Check file permissions:
   ```bash
   ls -la /home/user/AI_foto_ideas/*.json
   chmod 644 /home/user/AI_foto_ideas/*.json
   ```
2. Check Flask logs for errors

---

### Problem: Email feedback buttons don't work

**Solution:**
1. Verify `FEEDBACK_BASE_URL` in `.env` matches your tunnel URL
2. Regenerate ideas to get new URLs: `python3 main.py email --email test@example.com`

---

## 🎉 You're Done!

Your feedback system is now:
- ✅ Running 24/7
- ✅ Publicly accessible via HTTPS
- ✅ Secure and rate-limited
- ✅ Integrated with your email system
- ✅ Learning from user feedback

**Next steps:**
1. Test with real ideas and emails
2. Monitor logs for the first few days
3. Collect feedback and iterate!

---

## 📞 Need Help?

If something isn't working:
1. Check the logs: `sudo journalctl -u ai-foto-feedback.service -n 100`
2. Test each component individually
3. Verify environment variables are set correctly
4. Make sure ports aren't blocked

Happy hosting! 🚀
