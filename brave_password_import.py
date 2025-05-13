#!/usr/bin/env python3
"""
Brave Browser Password Import Module
-----------------------------------
Utilities for importing decrypted passwords back into Brave browser.
"""

import os
import json
import sqlite3
import logging
import platform
import base64
import shutil
import tempfile
from datetime import datetime

# Import crypto module for key functions
try:
    import brave_crypto as crypto
except ImportError:
    # If module is not found, it might be in the same directory
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import brave_crypto as crypto

logger = logging.getLogger('brave_extractor.password_import')

def get_encryption_key():
    """Get the Brave encryption key for the current platform."""
    return crypto.get_encryption_key()

def encrypt_password_windows(password, key):
    """Encrypt a password for Windows Brave browser."""
    if not crypto.PYCRYPTO_AVAILABLE:
        logger.error("pycryptodome is required for Windows encryption but not installed")
        return None
    
    try:
        from Crypto.Cipher import AES
        from os import urandom
        
        # Generate a random 12-byte nonce
        nonce = urandom(12)
        
        # Create AES-GCM cipher with the key and nonce
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        
        # Encrypt the password
        password_bytes = password.encode('utf-8')
        ciphertext, tag = cipher.encrypt_and_digest(password_bytes)
        
        # Combine nonce, ciphertext, and tag
        encrypted = b'v10' + nonce + ciphertext + tag
        return encrypted
    except Exception as e:
        logger.error(f"Error encrypting password on Windows: {e}")
        return None

def encrypt_password_linux(password, key):
    """Encrypt a password for Linux Brave browser."""
    try:
        # Try using cryptography library first for AES-GCM
        if crypto.CRYPTOGRAPHY_AVAILABLE:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            from os import urandom
            
            # Generate a random 12-byte nonce
            nonce = urandom(12)
            
            # Create AESGCM cipher with the key
            aesgcm = AESGCM(key)
            
            # Encrypt the password
            password_bytes = password.encode('utf-8')
            ciphertext = aesgcm.encrypt(nonce, password_bytes, None)
            
            # Return the prefixed, encrypted password
            return b'v10' + nonce + ciphertext
        
        # Fall back to pycryptodome if available
        elif crypto.PYCRYPTO_AVAILABLE:
            return encrypt_password_windows(password, key)
        else:
            logger.error("No suitable encryption library available")
            return None
    except Exception as e:
        logger.error(f"Error encrypting password on Linux: {e}")
        return None

def encrypt_password(password, key=None):
    """
    Encrypt a password for Brave browser using the appropriate method 
    for the current platform.
    """
    if not password:
        return None
    
    if key is None:
        key = get_encryption_key()
        if not key:
            logger.error("Unable to get encryption key")
            return None
    
    system = platform.system()
    
    if system == 'Windows':
        return encrypt_password_windows(password, key)
    elif system == 'Linux':
        return encrypt_password_linux(password, key)
    else:
        logger.error(f"Unsupported OS: {system}")
        return None

def import_passwords_from_json(json_file, login_data_file):
    """
    Import passwords from a JSON file (exported by the tool) back into 
    Brave browser's Login Data SQLite database.
    
    Parameters:
    - json_file: Path to the JSON file containing exported passwords
    - login_data_file: Path to the Brave browser's Login Data file
    
    Returns True if successful, False otherwise.
    """
    if not os.path.exists(json_file):
        logger.error(f"Password JSON file not found: {json_file}")
        return False
    
    # Get the encryption key
    key = get_encryption_key()
    if not key:
        logger.error("Unable to retrieve encryption key")
        return False
    
    # Read the passwords from JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            passwords = json.load(f)
        
        if not passwords:
            logger.warning("No passwords found in the JSON file")
            return False
            
        logger.info(f"Found {len(passwords)} passwords to import")
        
        # Create a temporary copy of the database to avoid lock issues
        temp_db = os.path.join(tempfile.gettempdir(), "temp_login_data_import")
        
        # Check if target database exists and copy it, otherwise create new
        if os.path.exists(login_data_file):
            shutil.copy2(login_data_file, temp_db)
        else:
            # Create a new empty database with the required schema
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Create the logins table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logins (
                    id INTEGER PRIMARY KEY,
                    origin_url TEXT NOT NULL,
                    action_url TEXT,
                    username_element TEXT,
                    username_value TEXT,
                    password_element TEXT,
                    password_value BLOB,
                    submit_element TEXT,
                    signon_realm TEXT NOT NULL,
                    date_created INTEGER NOT NULL,
                    blacklisted_by_user INTEGER NOT NULL,
                    scheme INTEGER NOT NULL,
                    password_type INTEGER,
                    times_used INTEGER,
                    form_data BLOB,
                    display_name TEXT,
                    icon_url TEXT,
                    federation_url TEXT,
                    skip_zero_click INTEGER,
                    generation_upload_status INTEGER,
                    possible_username_pairs BLOB,
                    date_last_used INTEGER,
                    moving_blocked_for BLOB,
                    date_password_modified INTEGER
                )
            ''')
            conn.commit()
            conn.close()
        
        # Connect to the database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Import each password
        import_count = 0
        current_time = int(datetime.now().timestamp() * 1000000)
        
        for password_data in passwords:
            url = password_data.get('url', '')
            username = password_data.get('username', '')
            password = password_data.get('password', '')
            
            if not url or not password:
                continue
            
            # Generate signon_realm (usually same as origin_url)
            signon_realm = url
            
            # Check if this entry already exists
            cursor.execute(
                'SELECT id FROM logins WHERE origin_url = ? AND username_value = ?',
                (url, username)
            )
            existing_entry = cursor.fetchone()
            
            # Encrypt the password
            encrypted_password = encrypt_password(password, key)
            if not encrypted_password:
                logger.warning(f"Could not encrypt password for {url}")
                continue
            
            if existing_entry:
                # Update existing entry
                cursor.execute('''
                    UPDATE logins 
                    SET password_value = ?, date_password_modified = ?
                    WHERE id = ?
                ''', (encrypted_password, current_time, existing_entry[0]))
            else:
                # Insert new entry
                cursor.execute('''
                    INSERT INTO logins (
                        origin_url, action_url, username_element, username_value,
                        password_element, password_value, submit_element, signon_realm,
                        date_created, blacklisted_by_user, scheme, date_password_modified
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    url, url, '', username,
                    '', encrypted_password, '', signon_realm,
                    current_time, 0, 0, current_time
                ))
            
            import_count += 1
        
        conn.commit()
        conn.close()
        
        # Backup the current login data file
        if os.path.exists(login_data_file):
            backup_file = f"{login_data_file}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            shutil.copy2(login_data_file, backup_file)
            logger.info(f"Backed up Login Data to {backup_file}")
        
        # Copy the temporary database to the Login Data file
        shutil.copy2(temp_db, login_data_file)
        logger.info(f"Successfully imported {import_count} passwords")
        
        # Clean up
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except Exception:
                pass
                
        return True
        
    except Exception as e:
        logger.error(f"Error importing passwords: {e}")
        return False

if __name__ == "__main__":
    # Simple test if run directly
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 3:
        print("Usage: python brave_password_import.py passwords.json login_data_path")
        sys.exit(1)
    
    json_file = sys.argv[1]
    login_data_file = sys.argv[2]
    
    if import_passwords_from_json(json_file, login_data_file):
        print("Passwords imported successfully.")
    else:
        print("Failed to import passwords.") 