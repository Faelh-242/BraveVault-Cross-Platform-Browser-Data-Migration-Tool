#!/usr/bin/env python3
"""
Brave Browser Data Extractor and Importer
-----------------------------------------
Extract and import Brave browser data (history, passwords, bookmarks) between
different operating systems (Ubuntu and Windows 10).
"""

import os
import sys
import shutil
import zipfile
import argparse
import platform
import json
import sqlite3
import tempfile
import logging
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

# Import our modules
try:
    import brave_crypto as crypto
    import brave_bookmarks as bookmarks
    import brave_history as history
    import brave_password_import as password_import
except ImportError:
    # If modules are not found, they might be in the same directory
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import brave_crypto as crypto
    import brave_bookmarks as bookmarks
    import brave_history as history
    import brave_password_import as password_import

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('brave_extractor')

# Brave data locations
BRAVE_PATHS = {
    'Windows': os.path.expandvars(r'%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default'),
    'Linux': os.path.expanduser('~/.config/BraveSoftware/Brave-Browser/Default')
}

# Files to be extracted and imported
BRAVE_DATA_FILES = {
    'History': 'History',
    'Bookmarks': 'Bookmarks',
    'Login Data': 'Login Data',
    'Preferences': 'Preferences',
    'Favicons': 'Favicons',
    'Cookies': 'Cookies',
    'Web Data': 'Web Data'
}

def get_brave_path():
    """Get the path to the Brave browser data based on the OS."""
    system = platform.system()
    if system == 'Windows':
        return BRAVE_PATHS['Windows']
    elif system == 'Linux':
        return BRAVE_PATHS['Linux']
    else:
        logger.error(f"Unsupported OS: {system}. This tool supports Windows and Ubuntu only.")
        sys.exit(1)

def check_brave_installed():
    """Check if Brave browser is installed on the system."""
    brave_path = get_brave_path()
    if not os.path.exists(brave_path):
        logger.error("Brave browser data not found. Make sure Brave is installed.")
        return False
    return True

def export_brave_data(output_file, include_passwords=True, include_history=True, include_bookmarks=True, history_days=None):
    """Export Brave browser data to a ZIP file."""
    if not check_brave_installed():
        sys.exit(1)
        
    brave_path = get_brave_path()
    system = platform.system()
    
    logger.info(f"Exporting Brave data from {brave_path}")
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy each file to the temporary directory
        for file_desc, file_name in BRAVE_DATA_FILES.items():
            src_file = os.path.join(brave_path, file_name)
            dst_file = os.path.join(temp_dir, file_name)
            
            if os.path.exists(src_file):
                try:
                    # Create a copy to avoid database locked issues
                    shutil.copy2(src_file, dst_file)
                    logger.info(f"Copied {file_desc} ({file_name})")
                except Exception as e:
                    logger.warning(f"Could not copy {file_desc} ({file_name}): {e}")
            else:
                logger.warning(f"File not found: {src_file}")
        
        # Export passwords if requested
        if include_passwords:
            passwords_file = os.path.join(brave_path, "Login Data")
            if os.path.exists(passwords_file):
                try:
                    passwords_json = os.path.join(temp_dir, "passwords.json")
                    passwords = crypto.decrypt_passwords_db(passwords_file, passwords_json)
                    logger.info(f"Exported {len(passwords)} passwords to {passwords_json}")
                except Exception as e:
                    logger.warning(f"Could not export passwords: {e}")
        
        # Export history if requested
        if include_history:
            history_file = os.path.join(brave_path, "History")
            if os.path.exists(history_file):
                try:
                    history_json = os.path.join(temp_dir, "history.json")
                    history.export_history(history_file, history_json, since_days=history_days)
                    logger.info(f"Exported history to {history_json}")
                except Exception as e:
                    logger.warning(f"Could not export history: {e}")
        
        # Export bookmarks if requested
        if include_bookmarks:
            bookmarks_file = os.path.join(brave_path, "Bookmarks")
            if os.path.exists(bookmarks_file):
                try:
                    bookmarks_json = os.path.join(temp_dir, "bookmarks.json")
                    bookmarks_html = os.path.join(temp_dir, "bookmarks.html")
                    bookmarks.export_bookmarks(bookmarks_file, bookmarks_json)
                    bookmarks.export_bookmarks_html(bookmarks_file, bookmarks_html)
                    logger.info(f"Exported bookmarks to {bookmarks_json} and {bookmarks_html}")
                except Exception as e:
                    logger.warning(f"Could not export bookmarks: {e}")
        
        # Create a metadata file
        metadata = {
            'export_date': datetime.now().isoformat(),
            'system': system,
            'brave_path': brave_path,
            'files': list(BRAVE_DATA_FILES.values()),
            'exported_passwords': include_passwords,
            'exported_history': include_history,
            'exported_bookmarks': include_bookmarks,
            'history_days': history_days
        }
        
        with open(os.path.join(temp_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create the ZIP file
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
    
    logger.info(f"Brave data exported successfully to {output_file}")
    logger.info(f"IMPORTANT: This file contains sensitive data. Keep it secure and delete after transferring.")

def import_brave_data(input_file, import_passwords=True, import_history=True, import_bookmarks=True):
    """Import Brave browser data from a ZIP file."""
    if not check_brave_installed():
        sys.exit(1)
        
    brave_path = get_brave_path()
    
    logger.info(f"Importing Brave data to {brave_path}")
    
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the ZIP file
        with zipfile.ZipFile(input_file, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        # Check metadata
        metadata_file = os.path.join(temp_dir, 'metadata.json')
        if not os.path.exists(metadata_file):
            logger.warning("Metadata file not found in the ZIP. Proceeding anyway.")
        else:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                logger.info(f"Importing data exported on {metadata.get('export_date')} from {metadata.get('system')}")
        
        # Backup current Brave data
        backup_dir = os.path.join(os.path.dirname(brave_path), f"Default_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(backup_dir, exist_ok=True)
        
        for file_desc, file_name in BRAVE_DATA_FILES.items():
            src_file = os.path.join(brave_path, file_name)
            bak_file = os.path.join(backup_dir, file_name)
            
            if os.path.exists(src_file):
                try:
                    shutil.copy2(src_file, bak_file)
                    logger.info(f"Backed up {file_desc} ({file_name})")
                except Exception as e:
                    logger.warning(f"Could not backup {file_desc} ({file_name}): {e}")
        
        # Import files from the temporary directory
        for file_desc, file_name in BRAVE_DATA_FILES.items():
            src_file = os.path.join(temp_dir, file_name)
            dst_file = os.path.join(brave_path, file_name)
            
            if os.path.exists(src_file):
                try:
                    # Make sure Brave is closed before copying
                    shutil.copy2(src_file, dst_file)
                    logger.info(f"Imported {file_desc} ({file_name})")
                except Exception as e:
                    logger.warning(f"Could not import {file_desc} ({file_name}): {e}")
            else:
                logger.warning(f"File not found in backup: {file_name}")
        
        # Import passwords if requested
        if import_passwords:
            passwords_json = os.path.join(temp_dir, "passwords.json")
            login_data_file = os.path.join(brave_path, "Login Data")
            if os.path.exists(passwords_json):
                try:
                    if password_import.import_passwords_from_json(passwords_json, login_data_file):
                        logger.info(f"Successfully imported passwords from {passwords_json}")
                    else:
                        logger.error(f"Failed to import passwords from {passwords_json}")
                except Exception as e:
                    logger.error(f"Error during password import: {e}")
        
        # Import history if requested
        if import_history:
            history_json = os.path.join(temp_dir, "history.json")
            history_file = os.path.join(brave_path, "History")
            if os.path.exists(history_json):
                try:
                    history.import_history(history_json, history_file)
                    logger.info(f"Imported history from {history_json}")
                except Exception as e:
                    logger.warning(f"Could not import history: {e}")
        
        # Import bookmarks if requested
        if import_bookmarks:
            bookmarks_json = os.path.join(temp_dir, "bookmarks.json")
            bookmarks_file = os.path.join(brave_path, "Bookmarks")
            if os.path.exists(bookmarks_json):
                try:
                    bookmarks.import_bookmarks(bookmarks_json, bookmarks_file)
                    logger.info(f"Imported bookmarks from {bookmarks_json}")
                except Exception as e:
                    logger.warning(f"Could not import bookmarks: {e}")
    
    logger.info(f"Brave data imported successfully")
    logger.info(f"A backup of your previous data is available at {backup_dir}")
    logger.info(f"IMPORTANT: Restart Brave browser to see the imported data")

def main():
    """Main function to parse arguments and call the appropriate functions."""
    parser = argparse.ArgumentParser(description='Brave Browser Data Extractor and Importer')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export Brave browser data')
    export_parser.add_argument('--output', required=True, help='Output ZIP file')
    export_parser.add_argument('--no-passwords', action='store_true', help='Skip exporting passwords')
    export_parser.add_argument('--no-history', action='store_true', help='Skip exporting history')
    export_parser.add_argument('--no-bookmarks', action='store_true', help='Skip exporting bookmarks')
    export_parser.add_argument('--history-days', type=int, help='Only export history from the last N days')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import Brave browser data')
    import_parser.add_argument('--input', required=True, help='Input ZIP file')
    import_parser.add_argument('--no-passwords', action='store_true', help='Skip importing passwords')
    import_parser.add_argument('--no-history', action='store_true', help='Skip importing history')
    import_parser.add_argument('--no-bookmarks', action='store_true', help='Skip importing bookmarks')
    
    args = parser.parse_args()
    
    if args.command == 'export':
        export_brave_data(
            args.output,
            include_passwords=not args.no_passwords,
            include_history=not args.no_history,
            include_bookmarks=not args.no_bookmarks,
            history_days=args.history_days
        )
    elif args.command == 'import':
        import_brave_data(
            args.input,
            import_passwords=not args.no_passwords,
            import_history=not args.no_history,
            import_bookmarks=not args.no_bookmarks
        )
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 