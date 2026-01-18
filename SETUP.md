# Installation and Configuration

## Quick Method (Recommended)

Use the automatic setup script:

```bash
chmod +x setup.sh
./setup.sh
```

This will create a virtual environment and install all dependencies automatically.

## Manual Method

### Step 1: Install System Dependencies

The program needs some system libraries to capture keys globally:

```bash
sudo apt-get update
sudo apt-get install python3-pip python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-venv
```

### Step 2: Create Virtual Environment

Ubuntu 24.04 uses an "externally managed" Python environment. We'll use a virtual environment with access to system libraries (necessary for PyGObject):

```bash
python3 -m venv --system-site-packages venv
source venv/bin/activate
```

**Note:** We use `--system-site-packages` so the virtual environment has access to the `gi` (PyGObject) module installed on the system.

### Step 3: Install Python Dependencies

With the virtual environment activated:

```bash
pip install -r requirements.txt
```

### Step 4: Run

With the virtual environment activated:

```bash
python shortcut_helper.py
```

Or use the wrapper script:

```bash
./run.sh
```

## Note on Virtual Environment

Whenever you want to run the program, you need to activate the virtual environment first:

```bash
source venv/bin/activate
python shortcut_helper.py
```

Or use the `run.sh` script which does this automatically.

## Run in Background

To run the program in the background:

```bash
source venv/bin/activate
nohup python shortcut_helper.py &
```

Or using the script:

```bash
nohup ./run.sh &
```

## Stop the Program

If running in background, you can stop it with:

```bash
pkill -f shortcut_helper.py
```

## Install as System Service (Auto-start on Login)

To have ShortcutHelper start automatically when you log in to Ubuntu, you can install it as a systemd user service:

### Installation

```bash
chmod +x install-service.sh
./install-service.sh
```

This script will:
1. Detect your current X11 display automatically
2. Create a systemd service file
3. Install it to `~/.config/systemd/user/shortcut-helper.service`
4. Enable the service to start automatically on login
5. Start the service immediately

The service will automatically restart if it crashes, and will start automatically every time you log in.

### Service Management

Once installed, you can manage the service with systemctl:

```bash
# Check service status
systemctl --user status shortcut-helper.service

# View logs in real-time
journalctl --user -u shortcut-helper.service -f

# View last 50 log entries
journalctl --user -u shortcut-helper.service -n 50

# Restart the service
systemctl --user restart shortcut-helper.service

# Stop the service
systemctl --user stop shortcut-helper.service

# Start the service
systemctl --user start shortcut-helper.service

# Disable auto-start (but keep service installed)
systemctl --user disable shortcut-helper.service

# Re-enable auto-start
systemctl --user enable shortcut-helper.service
```

### Uninstallation

To remove the systemd service:

```bash
chmod +x uninstall-service.sh
./uninstall-service.sh
```

This will:
1. Stop the service if it's running
2. Disable auto-start
3. Remove the service file
4. Reload systemd daemon

**Note:** After uninstalling, you can still run ShortcutHelper manually using `./run.sh`.

## Troubleshooting

### Error: "externally-managed-environment"

If you encounter this error when trying to install with `pip3`, use the virtual environment as described above. Ubuntu 24.04 does not allow installing Python packages directly on the system.

### Error: "No module named 'pynput'"

Make sure that:
1. The virtual environment is created (`./setup.sh`)
2. The virtual environment is activated (`source venv/bin/activate`)
3. Dependencies are installed (`pip install -r requirements.txt`)

## Customization

Edit `config.json` to add, remove, or modify the displayed shortcuts.
