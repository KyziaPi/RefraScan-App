# RefraScan App - Complete Deployment Guide

Welcome! Your RefraScan app is ready to deploy. Choose the setup that matches your needs.

---

## 🎯 Quick Navigation

**Just starting out?** → [Single Computer Setup](#single-computer-setup)
**Need network access?** → [Multi-Computer Network Setup](#multi-computer-network-setup)
**Technical details?** → [Architecture & Troubleshooting](#architecture--troubleshooting)

---

## 📋 What's Included

| File | Purpose |
|------|---------|
| `SETUP.bat` | ⭐ Run this ONCE to install dependencies |
| `START-APP.bat` | ⭐ Run this to start the app (every time) |
| `README-STARTUP.md` | Instructions for non-technical users |
| `run-app.py` | Python launcher script |
| `.env.example` | Template for configuration |
| `TEST-NETWORK.bat` | Verify network setup (optional) |
| `NETWORK-QUICK-START.md` | Network setup guide (optional) |
| `NETWORK-SETUP.md` | Detailed network guide (optional) |

---

## Single Computer Setup

### First Time Only
1. Double-click **SETUP.bat**
2. Wait for dependencies to install (5-10 minutes)
3. Press any key when done

### Every Time You Use It
1. Double-click **START-APP.bat**
2. Browser opens automatically to `http://localhost:5000`
3. To stop: Press Ctrl+C in the command window

✅ That's it! No technical knowledge needed.

---

## Multi-Computer Network Setup

**Goal:** Multiple computers share the same database and upload folders

### Architecture
```
Server PC (Database + Shared Uploads)
    ↓ (Network Share)
Multiple Client PCs (Read & Write same data)
```

**Key:** Clients can both upload and download images - everything is shared!

### Prerequisites
- All computers on same network (same WiFi/LAN)
- Server machine: Runs database and shares upload folders
- Client machines: Access server's data

### Setup Overview (Detailed in NETWORK-QUICK-START.md)

#### On Server Machine:
1. Share `static/uploads` folder
2. Configure PostgreSQL for network access
3. Create `.env` file with database settings
4. Test with `START-APP.bat`

#### On Each Client Machine:
1. Map shared folder as network drive (e.g., Z:)
2. Create `.env` file pointing to server
3. Run `START-APP.bat` - done!

**For detailed steps:** Read [NETWORK-QUICK-START.md](NETWORK-QUICK-START.md)

### Multi-User Workflow Example
```
Timeline: All computers see changes instantly

10:00 AM - Server uploads patient X image
10:01 AM - Client #1 sees patient X in records
10:02 AM - Client #1 uploads patient Y image  
10:03 AM - Server sees patient Y (refreshes page)
10:04 AM - Client #2 sees both patients X and Y
10:05 AM - Client #2 uploads patient Z image
         ✓ All machines see patients X, Y, Z
         ✓ All images in shared uploads folder
         ✓ Database synchronized across network
```

---

## Configuration Files

### .env File (Required for Network Setup)

Copy `.env.example` to `.env` and update:

```
# Local Only
DB_HOST=127.0.0.1
UPLOAD_BASE_PATH=

# Network Setup
DB_HOST=192.168.1.100        (server IP)
UPLOAD_BASE_PATH=Z:\         (mapped drive)
```

### .env.example (Template)
Shows all available options with documentation

---

## Verification & Testing

### Single Computer
- App opens automatically in browser
- Can upload images
- Data persists between sessions

### Network Setup
- Run `TEST-NETWORK.bat` to verify configuration
- Should show ✓ for database and uploads
- If ✗ appears, check NETWORK-QUICK-START.md troubleshooting

---

## Architecture & Troubleshooting

### Single Computer Architecture
```
Local Machine
├── Python 3.10
├── Virtual Environment (.venv)
├── Flask App (localhost:5000)
├── PostgreSQL Database (local)
└── Uploads Folder (local)
```

### Network Architecture
```
Server Machine
├── PostgreSQL Database (listening to network)
└── Shared Uploads Folder (\\SERVER\uploads)
        ↑
        └─→ Network Connection
            ↓
Client Machine #1
├── Flask App
├── .env → points to server
└── Mapped Drive (Z:)

Client Machine #2
├── Flask App
├── .env → points to server
└── Mapped Drive (Z:)
```

---

## Troubleshooting

### App Won't Start
- Check Python is installed: `python --version`
- Check virtual environment: `.venv` folder should exist
- Delete `.venv` and run `SETUP.bat` again

### Browser Doesn't Open Automatically
- App is still running on http://localhost:5000
- Open browser manually and go to that URL

### Database Connection Error
- PostgreSQL service running? Check Windows Services
- Port 5432 open? Test with: `netstat -an | findstr 5432`
- .env has correct password? Update and restart

### Network Issues (After Sharing)
- Can't see network path? Run `TEST-NETWORK.bat`
- Mapped drive offline? Disconnect and re-map
- Database won't connect? Check server IP address

### "Port 5000 already in use"
- Another app using port 5000
- Kill it: `netstat -ano | findstr :5000`
- Then: `taskkill /PID <PID> /F`

---

## User Documentation

### For Non-Technical Users
→ Give them: [README-STARTUP.md](README-STARTUP.md)

Just needs to know:
1. Run `SETUP.bat` once
2. Run `START-APP.bat` every time
3. Done!

### For Technical Managers
→ Give them: This file + [NETWORK-QUICK-START.md](NETWORK-QUICK-START.md)

Key points:
- Database is PostgreSQL
- Runs on Flask framework
- Supports network deployment
- All configuration via .env

---

## System Requirements

### Minimum (Single Computer)
- Windows 10+
- Python 3.8+
- 4GB RAM
- 3GB disk space (mostly for TensorFlow)
- PostgreSQL installed and running

### Network Setup
- Same as above, plus:
- Network connectivity (WiFi/LAN)
- Static server IP (recommended)
- File sharing enabled on server

---

## Features

✅ Web-based interface (no installation per-user)
✅ Multiple users simultaneously on same machine or network
✅ **Client machines can upload AND download images** (everything shared!)
✅ Patient record management
✅ Medical imaging with AI inference
✅ Heatmap/explainability visualization
✅ Data export (Excel)
✅ Data import (Excel templates)
✅ Multi-computer network support
✅ Automatic synchronization across network

---

## Support & Maintenance

### Backing Up Data
- Database: Back up PostgreSQL (contact database admin)
- Files: Back up `static/uploads` folder
- Configuration: Back up `.env` file (keep password safe!)

### Updating the App
- Download new version
- Copy files over existing (except .env, static/uploads)
- Run `SETUP.bat` if requirements.txt changed
- Run `START-APP.bat` as normal

### Monitoring
- Check `static/uploads` folder for disk space
- Monitor PostgreSQL database size
- Check network connectivity if multi-computer

---

## Quick Reference

| Action | Command |
|--------|---------|
| First time setup | `SETUP.bat` |
| Start app | `START-APP.bat` |
| Stop app | Ctrl+C in console |
| Check network | `TEST-NETWORK.bat` |
| View configuration | Open `.env` file |

---

## Next Steps

1. **Single Computer?**
   - Run `SETUP.bat` → `START-APP.bat` → Done!

2. **Network Setup?**
   - Read [NETWORK-QUICK-START.md](NETWORK-QUICK-START.md)
   - Follow 5 steps
   - Run `TEST-NETWORK.bat` to verify

3. **Share with Users?**
   - Give them [README-STARTUP.md](README-STARTUP.md)
   - They only need to know: `SETUP.bat` (once) → `START-APP.bat` (always)

---

**Version:** 1.0  
**Updated:** August 2026  
**Contact:** guecoyerikaelaine@gmail.com
