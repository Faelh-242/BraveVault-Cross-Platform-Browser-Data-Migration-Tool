# BraveVault: Cross-Platform Browser Data Migration Tool

<p align="center">
  <img src="https://brave.com/static-assets/images/brave-logo-sans-text.svg" alt="Brave Logo" width="100">
</p>

BraveVault is a powerful tool for securely transferring your Brave browser data (history, passwords, bookmarks) between different operating systems. Perfect for when you're switching computers or setting up a new system.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## ✨ Features

- **Comprehensive Data Export**: Extract all essential browser data
  - Passwords (fully encrypted)
  - Browsing history
  - Bookmarks
  - Site preferences
- **Secure Password Handling**: Proprietary encryption handling for safe password transfer
- **Dual Interface**: Use command-line or graphical interface
- **Cross-Platform**: Works seamlessly between Windows and Ubuntu/Linux
- **Backup Protection**: Automatically creates backups before importing

## 📋 Requirements

- Python 3.6+
- Brave Browser installed on both systems
- Required Python packages (installed automatically)

## 🚀 Installation

### Quick Install (Recommended)

```bash
# On Linux
git clone https://github.com/brighteyekid/BraveVault-Cross-Platform-Browser-Data-Migration-Tool.git
cd brave-vault
./install.sh

# On Windows
git clone https://github.com/brighteyekid/BraveVault-Cross-Platform-Browser-Data-Migration-Tool.git
cd brave-vault
install.bat
```

### Manual Installation

```bash
git clone https://github.com/brighteyekid/BraveVault-Cross-Platform-Browser-Data-Migration-Tool.git
cd brave-vault
pip install -r requirements.txt
```

## 💻 Usage

### Graphical Interface

The easiest way to use BraveVault is through its graphical interface:

**On Linux:**
```bash
./brave_extractor.sh gui
```

**On Windows:**
```batch
brave_extractor.bat gui
```

### Command Line Interface

For advanced users or automation:

**Export your browser data:**
```bash
python brave_extractor.py export --output brave_data.zip
```

**Import on a new system:**
```bash
python brave_extractor.py import --input brave_data.zip
```

#### Advanced Options

```bash
# Export only specific data
python brave_extractor.py export --output brave_data.zip --no-passwords --no-history

# Export only recent history
python brave_extractor.py export --output brave_data.zip --history-days 30
```

## 🔍 Data Locations

BraveVault automatically finds your Brave browser data in:

- **Windows**: `%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default`
- **Ubuntu/Linux**: `~/.config/BraveSoftware/Brave-Browser/Default`

## 🔒 Security Notice

This tool handles sensitive information including passwords. To maintain security:

- Keep exported data files secure
- Transfer data files using encrypted channels
- Delete exported files after completing the transfer
- Close Brave browser before importing data

## 🤝 Contributing

Contributions are welcome! Feel free to submit pull requests or open issues to improve BraveVault.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details. 
