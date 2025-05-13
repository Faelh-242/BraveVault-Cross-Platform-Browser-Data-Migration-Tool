#!/bin/bash

echo "Installing BraveVault - Brave Browser Data Migration Tool..."
echo "----------------------------------------------"

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Create a virtual environment
echo "Creating a Python virtual environment..."
python3 -m venv "$SCRIPT_DIR/venv"
source "$SCRIPT_DIR/venv/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# Make scripts executable
echo "Making scripts executable..."
chmod +x "$SCRIPT_DIR/brave_extractor.py"
chmod +x "$SCRIPT_DIR/brave_extractor_gui.py"
chmod +x "$SCRIPT_DIR/brave_extractor.sh"
chmod +x "$SCRIPT_DIR/brave_password_import.py"

# Create desktop shortcut
echo "Creating desktop shortcut..."
desktop_file="$HOME/.local/share/applications/brave-vault.desktop"
mkdir -p "$(dirname "$desktop_file")"

cat > "$desktop_file" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=BraveVault
Comment=Securely transfer Brave browser data between operating systems
Exec=$SCRIPT_DIR/brave_extractor.sh gui
Icon=brave-browser
Terminal=false
Categories=Utility;
Keywords=Brave;Browser;Data;Export;Import;Vault;Transfer;
EOF

echo "Installation complete!"
echo
echo "You can now run BraveVault using the desktop shortcut or by running:"
echo "  $SCRIPT_DIR/brave_extractor.sh"
echo
echo "To run the GUI directly:"
echo "  $SCRIPT_DIR/brave_extractor_gui.py"
echo 