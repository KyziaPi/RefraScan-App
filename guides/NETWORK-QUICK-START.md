# RefraScan App - Multi-Computer Network Setup (Quick Start)

## What This Does
Allows multiple computers on your network to:
- Use the same database (all patient data is shared)
- Access the same uploads folder (all images available to everyone)
- Run the app independently on different machines

## Quick Setup (5 Steps)

### Step 1: On Server Machine - Share Uploads Folder
1. Open File Explorer
2. Navigate to RefraScan-App folder
3. Right-click `static` → `uploads` folder
4. Select "Properties" → "Sharing" tab
5. Click "Share" → Add your user → "Share"
6. Note the network path (e.g., `\\COMPUTER-NAME\uploads`)

### Step 2: On Server Machine - Configure PostgreSQL
1. Open PostgreSQL data folder (usually `C:\Program Files\PostgreSQL\15\data`)
2. Edit `postgresql.conf`:
   - Find: `#listen_addresses = 'localhost'`
   - Change to: `listen_addresses = '*'`
   - Save
3. Restart PostgreSQL (Services app)
4. Test: Run `TEST-NETWORK.bat`

### Step 3: On Server Machine - Create .env File
1. In RefraScan-App folder, copy `.env.example` and rename to `.env`
2. Update with your PostgreSQL password:
   ```
   DB_NAME=refrascan_db
   DB_USER=postgres
   DB_PASSWORD=your_actual_password
   DB_HOST=127.0.0.1
   DB_PORT=5432
   UPLOAD_BASE_PATH=
   ```
3. Leave `UPLOAD_BASE_PATH` empty (uses local folder)
4. Save and test: Run `START-APP.bat`

### Step 4: On Client Machines - Map Network Drive
1. Open File Explorer
2. Right-click "This PC" → "Map network drive"
3. Drive: `Z:`
4. Folder: `\\SERVER-IP\uploads` (replace SERVER-IP with server's actual IP)
   - Find server IP: On server, open Command Prompt, type `ipconfig`, look for IPv4 Address
5. Check "Reconnect at sign-in"
6. Click "Finish"

### Step 5: On Client Machines - Create .env File
1. Copy RefraScan-App folder to client machine (or share from server)
2. Create `.env` file:
   ```
   DB_NAME=refrascan_db
   DB_USER=postgres
   DB_PASSWORD=your_actual_password
   DB_HOST=192.168.1.100
   DB_PORT=5432
   UPLOAD_BASE_PATH=Z:\
   ```
   Replace `192.168.1.100` with server's actual IP and `Z:\` with your mapped drive
3. Run `START-APP.bat` - all set!

---

## Example Network Setup

```
Server PC (192.168.1.100)
├── PostgreSQL Database
├── RefraScan App
└── Shared Folder: uploads/
    ├── images/
    ├── heatmaps/
    └── temp/

Client PC #1 (192.168.1.101)
├── RefraScan App
└── Mapped Drive Z: → \\192.168.1.100\uploads
    (can read & write uploads)

Client PC #2 (192.168.1.102)
├── RefraScan App
└── Mapped Drive Z: → \\192.168.1.100\uploads
    (can read & write uploads)
```

## ✅ Client Uploads Work Automatically

Yes, clients can upload images! Here's what happens:

1. **Client uploads image** via web interface
2. App saves to: `Z:\images\` (the mapped network drive)
3. File actually goes to: `\\SERVER\uploads\images\`
4. **All other clients** can see it immediately
5. **Database** updated on server (all users see it)

**Important:** Make sure network share has **Write** permissions for users!
- [Go back to Step 2](#step-2-set-permissions) to verify permissions

---

## Troubleshooting

### "Network path not found"
- Server IP wrong? Get it from `ipconfig` on server
- Server offline? Check if it's on and connected
- Firewall blocking? Open Windows Firewall exceptions

### "Database connection failed"
- PostgreSQL running on server? Check Services
- Password correct? Update .env on client
- IP address correct? Use `ping SERVER-IP` to test

### "Can't access shared folder"
- Folder shared? Right-click folder → Properties → Sharing
- Permissions set? Everyone needs Read/Write access
- Reconnect mapped drive? Disconnect and re-map

### "Still using local folder instead of network"
- Network path set in .env? Check `UPLOAD_BASE_PATH=`
- Mapped drive working? Test access in File Explorer
- Path format wrong? Use `Z:\` or `\\192.168.1.100\uploads\`

---

## Files Reference

| File | Purpose |
|------|---------|
| `NETWORK-SETUP.md` | Detailed network setup guide |
| `.env.example` | Template for .env configuration |
| `TEST-NETWORK.bat` | Verify network setup is working |
| `START-APP.bat` | Launch app (works on both server and clients) |

---

## Important Notes

✅ **All patient data** is stored in the database (shared automatically)
✅ **All images** go to the shared uploads folder
✅ **Database must be created first** (run app on server once)
✅ **Each user runs app independently** on their machine
✅ **All changes are visible** to everyone immediately
✅ **Backup strategy**: Backup server database and uploads folder

---

## Testing Your Setup

1. **On Server:**
   - Run `START-APP.bat`
   - Go to inference engine
   - Upload an image, fill form, submit
   - Check that `static/uploads/images` has the file
   - Note the patient ID created
   - Stop app (Ctrl+C)

2. **On Client #1:**
   - Run `TEST-NETWORK.bat` to verify connection
   - Run `START-APP.bat`
   - Go to inference engine
   - Upload a DIFFERENT image (different patient)
   - Check that the server's patient appears in "Patient Records"
   - Stop app (Ctrl+C)

3. **On Server Again:**
   - Run `START-APP.bat`
   - Go to "Patient Records"
   - Should see BOTH patients (from server and client #1)
   - Check `static/uploads/images` folder
   - Should see images from both uploads
   - This proves uploads from clients work! ✅

4. **On Client #2 (if available):**
   - Repeat steps from Client #1
   - Should see all previous uploads from server and other clients
   - Upload new image
   - This demonstrates true multi-user capability ✅

---

## Troubleshooting Client Uploads

### "Upload fails" or "File not saved"
- Network drive not mapped? Check `Z:\` in File Explorer
- Network drive offline? Reconnect it
- Permission denied? Share needs Write access (Step 2 above)
- Disk full on server? Check free space on shared folder

### "Upload appears on client but not visible on server"
- File delay? Network transfers may take a moment, refresh
- Different machine uploaded? Check that client's .env is correct
- Share not updated? Right-click Z: → Disconnect → Reconnect

### "See server uploads but can't modify"
- Read-only access? Need Write permissions on share
- Admin needed? Contact IT to update permissions
