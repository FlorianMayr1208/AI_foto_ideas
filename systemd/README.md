# Systemd Service Files

These service files allow your feedback system to run automatically at system startup.

## Files

- **ai-foto-feedback.service** - Flask feedback API service
- **cloudflared-tunnel.service** - Quick tunnel (URL changes on restart)
- **cloudflared-tunnel-persistent.service** - Named/persistent tunnel (fixed URL)

## Installation

### 1. Edit the service files

Before installing, you may need to edit the files to match your setup:

```bash
# Edit Flask service
nano systemd/ai-foto-feedback.service

# Change these if needed:
# - User=user (change to your username)
# - WorkingDirectory=/home/user/AI_foto_ideas (change path if different)
# - ExecStart=/usr/bin/python3 ... (verify python3 path with: which python3)
```

### 2. Copy to systemd directory

```bash
# Copy Flask service
sudo cp systemd/ai-foto-feedback.service /etc/systemd/system/

# Copy tunnel service (choose ONE):
# Option A: Quick tunnel (temporary URL)
sudo cp systemd/cloudflared-tunnel.service /etc/systemd/system/

# Option B: Persistent tunnel (fixed URL) - RECOMMENDED
sudo cp systemd/cloudflared-tunnel-persistent.service /etc/systemd/system/cloudflared-tunnel.service
```

### 3. Reload systemd and enable services

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable ai-foto-feedback.service
sudo systemctl enable cloudflared-tunnel.service

# Start services now
sudo systemctl start ai-foto-feedback.service
sudo systemctl start cloudflared-tunnel.service
```

### 4. Check status

```bash
# Check if services are running
sudo systemctl status ai-foto-feedback.service
sudo systemctl status cloudflared-tunnel.service
```

## Common Commands

### View logs
```bash
# Flask API logs
sudo journalctl -u ai-foto-feedback.service -f

# Cloudflare Tunnel logs
sudo journalctl -u cloudflared-tunnel.service -f
```

### Restart services
```bash
sudo systemctl restart ai-foto-feedback.service
sudo systemctl restart cloudflared-tunnel.service
```

### Stop services
```bash
sudo systemctl stop ai-foto-feedback.service
sudo systemctl stop cloudflared-tunnel.service
```

### Disable services (don't start on boot)
```bash
sudo systemctl disable ai-foto-feedback.service
sudo systemctl disable cloudflared-tunnel.service
```

## Troubleshooting

### Service fails to start

1. Check logs:
   ```bash
   sudo journalctl -u ai-foto-feedback.service -n 50
   ```

2. Test manually:
   ```bash
   python3 /home/user/AI_foto_ideas/feedback_api.py
   ```

3. Check file permissions:
   ```bash
   ls -la /home/user/AI_foto_ideas/
   ```

### Tunnel not accessible

1. Check if Flask is running:
   ```bash
   curl http://127.0.0.1:5000/health
   ```

2. Check tunnel logs:
   ```bash
   sudo journalctl -u cloudflared-tunnel.service -f
   ```

3. Verify cloudflared is installed:
   ```bash
   which cloudflared
   cloudflared --version
   ```
