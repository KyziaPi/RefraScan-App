# RefraScan App - Multi-Computer Network Setup Guide

## Overview
This guide enables multiple computers on the same network to:
- Connect to a shared PostgreSQL database
- Access the same uploads folder (images and heatmaps)
- Run the RefraScan app from different machines

## Prerequisites
- All computers on the same network (same WiFi/LAN)
- Server machine: Has database and shared folders
- Client machines: Can access server's shared resources
- Windows/network sharing enabled on server

---

## Part 1: Database Setup (Server Machine)

### Step 1: Ensure PostgreSQL Listens to Network
1. Find PostgreSQL installation folder (usually `C:\Program Files\PostgreSQL\XX`)
2. Open `data/postgresql.conf` in a text editor
3. Find line: `#listen_addresses = 'localhost'`
4. Change to: `listen_addresses = '*'`
5. Save and restart PostgreSQL

### Step 2: Update pg_hba.conf (Allow Network Connections)
1. In same `data` folder, open `pg_hba.conf`
2. Add this line at the end:
   ```
   host    all             all             0.0.0.0/0               md5
   ```
3. Save and restart PostgreSQL

### Step 3: Get Server's IP Address
1. Open Command Prompt on server
2. Type: `ipconfig`
3. Look for "IPv4 Address" (e.g., `192.168.1.100`)
4. Note this down - you'll use it on client machines

---

## Part 2: Network Shared Folder Setup (Server Machine)

### Step 1: Share the Uploads Folder
1. Navigate to your RefraScan app folder
2. Right-click `static\uploads` folder
3. Select "Properties"
4. Go to "Sharing" tab
5. Click "Share"
6. Add your user and click "Share"
7. Note the network path shown (e.g., `\\SERVER-PC\uploads`)

### Step 2: Set Permissions
1. Right-click `static\uploads` folder
2. Select "Properties" → "Security" tab
3. Click "Edit" → "Add"
4. Type: `Everyone` and click "Check Names"
5. Click "OK"
6. Select "Everyone"
7. Check: **"Modify"** and **"Write"** (required for client uploads!)
8. Click "Apply" and "OK"

**Important:** Without "Modify" and "Write" permissions, clients won't be able to upload images!

---

## Part 3: Configure Server Machine

### Step 1: Create/Update .env File
In your RefraScan app folder, create or update `.env`:

```
# Database Configuration
DB_NAME=refrascan_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=127.0.0.1
DB_PORT=5432

# Network Shared Folder Path (for uploads)
# Use this to store all images, heatmaps on shared network drive
# Format: \\COMPUTER_NAME\ShareName or \\IP_ADDRESS\ShareName
UPLOAD_BASE_PATH=
```

Leave `UPLOAD_BASE_PATH` empty for now (uses local folder by default)

### Step 2: Test Server Setup
1. Double-click `START-APP.bat`
2. Browser opens to `http://localhost:5000`
3. Test that it works normally
4. Close the app (Ctrl+C)

---

## Part 4: Configure Client Machines

### Step 1: Map Network Drive
1. Open File Explorer
2. Right-click "This PC" → "Map network drive"
3. Drive letter: Choose `Z:` (or any available)
4. Folder: `\\SERVER_IP\uploads` (replace SERVER_IP with actual IP, e.g., `\\192.168.1.100\uploads`)
5. Check "Reconnect at sign-in"
6. Click "Finish"
7. Folder should open automatically

### Step 2: Create .env File
1. On client machine, go to RefraScan app folder
2. Create file called `.env` with this content:

```
# Database Configuration (point to server)
DB_NAME=refrascan_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=192.168.1.100
DB_PORT=5432

# Use mapped network drive for uploads
UPLOAD_BASE_PATH=Z:\
```

Replace:
- `192.168.1.100` with server's actual IP address
- `your_postgres_password` with actual password
- `Z:\` with the drive letter you mapped

### Step 3: Copy App Files to Client
Option A: Copy entire RefraScan-App folder to client (easier)
Option B: Just update the `.env` file if app is shared

### Step 4: Run on Client Machine
1. Double-click `SETUP.bat` (if first time)
2. Double-click `START-APP.bat`
3. App opens on `http://localhost:5000`
4. All uploads go to shared network folder
5. Database on server is used

---

## How Client Uploads Work

### Upload Flow
1. **Client #1** accesses app at `http://localhost:5000`
2. User uploads an image through inference engine
3. App saves file to: `Z:\images\` (the mapped drive)
4. File actually writes to: `\\SERVER\uploads\images\`
5. **Database** automatically updated on server
6. **Client #2** can immediately see:
   - New patient in "Patient Records"
   - New image available
   - All metadata and inference results

### Why This Works
- Each client's `Z:\` drive maps to same server folder
- All write to same physical location
- All read from same database
- Changes are instant across network

### Permissions Needed for Uploads
- Share must have "Modify" permission
- "Write" permission for file creation
- "Read" permission for viewing others' uploads
- "Delete" permission to remove images (optional)

### Testing Client Uploads
See "Testing Your Setup" section below for step-by-step instructions

---

### Can't See Server Share?
- Ping server: `ping 192.168.1.100`
- Check Windows Firewall is allowing file sharing
- Check server isn't in sleep mode

### Database Connection Failed?
- Verify PostgreSQL is running on server
- Check `DB_HOST` in .env has correct IP
- Try: `psql -h 192.168.1.100 -U postgres`

### Mapped Drive Not Working?
- Disconnect and re-map the drive
- Use full UNC path: `\\192.168.1.100\uploads`
- Make sure network discovery is enabled on server

### Uploads Not Appearing?
- Check mapped drive has read/write permissions
- Verify UPLOAD_BASE_PATH in .env is correct
- Check network folder has enough space

---

## Architecture Summary

```
┌─────────────────────────────────────────┐
│     SERVER MACHINE (192.168.1.100)      │
│  ┌───────────────────────────────────┐  │
│  │   PostgreSQL Database             │  │
│  │   (listening on 0.0.0.0:5432)     │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │   Shared Folder: uploads/         │  │
│  │   ├── images/                     │  │
│  │   └── heatmaps/                   │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         ↑                    ↑
    Network Access       Network Access
         ↓                    ↓
┌─────────────────┐  ┌─────────────────┐
│  CLIENT PC #1   │  │  CLIENT PC #2   │
│  ┌───────────┐  │  │  ┌───────────┐  │
│  │RefraScan  │  │  │  │RefraScan  │  │
│  │App        │  │  │  │App        │  │
│  │(Z: drive)│  │  │  │(Z: drive)│  │
│  └───────────┘  │  │  └───────────┘  │
└─────────────────┘  └─────────────────┘
```

---

## Quick Checklist

- [ ] PostgreSQL configured to listen on network (postgresql.conf)
- [ ] pg_hba.conf allows network connections
- [ ] Server IP address noted (e.g., 192.168.1.100)
- [ ] `static\uploads` folder shared
- [ ] Folder permissions set to allow Everyone
- [ ] Server .env created with database config
- [ ] Server tested and working
- [ ] Client machines have network drive mapped
- [ ] Client machines have .env with server IP
- [ ] Clients can access database and uploads

---

## Support Tips

- All app data is in the database (shared automatically)
- All patient images are in the shared uploads folder
- Each user can run the app independently
- All changes are visible to everyone on the network
- Backups: Just backup server database and uploads folder
