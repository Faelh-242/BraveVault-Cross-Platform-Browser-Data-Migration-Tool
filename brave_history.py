#!/usr/bin/env python3
"""
Brave Browser History Module
---------------------------
Utilities for handling browser history in Brave browser.
"""

import os
import json
import sqlite3
import logging
import shutil
import tempfile
from datetime import datetime, timedelta

logger = logging.getLogger('brave_extractor.history')

def read_history(history_file, limit=None, since_days=None):
    """
    Read browsing history from a Brave History file.
    Returns a list of history entries.
    
    Parameters:
    - history_file: Path to the History SQLite database
    - limit: Maximum number of entries to return (None for all)
    - since_days: Only return entries from the last N days (None for all)
    """
    if not os.path.exists(history_file):
        logger.error(f"History file not found: {history_file}")
        return []
    
    # Create a copy of the database to avoid lock issues
    temp_db = os.path.join(tempfile.gettempdir(), "temp_history")
    try:
        shutil.copy2(history_file, temp_db)
        
        results = []
        
        try:
            conn = sqlite3.connect(temp_db)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT url, title, visit_count, last_visit_time FROM urls"
            params = []
            
            if since_days:
                # Convert days to microseconds (Chromium time format)
                # Chromium time is microseconds since Jan 1, 1601 UTC
                # First convert to microseconds since epoch (1970)
                time_threshold = datetime.now() - timedelta(days=since_days)
                epoch_start = datetime(1970, 1, 1)
                time_since_epoch = (time_threshold - epoch_start).total_seconds() * 1000000
                # Then add the difference between 1601 and 1970
                # (369 years, 89 leap days)
                chrome_time = time_since_epoch + (11644473600 * 1000000)
                
                query += " WHERE last_visit_time > ?"
                params.append(chrome_time)
            
            query += " ORDER BY last_visit_time DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            
            for row in cursor.fetchall():
                # Convert Chrome time to datetime
                # Chrome time is in microseconds since Jan 1, 1601 UTC
                chrome_time = row['last_visit_time']
                if chrome_time:
                    # Convert to seconds since epoch
                    seconds_since_epoch = chrome_time / 1000000 - 11644473600
                    # Convert to datetime
                    visit_time = datetime.fromtimestamp(seconds_since_epoch)
                else:
                    visit_time = None
                
                results.append({
                    'url': row['url'],
                    'title': row['title'],
                    'visit_count': row['visit_count'],
                    'last_visit': visit_time.isoformat() if visit_time else None
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error reading history database: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()
                
    except Exception as e:
        logger.error(f"Error copying history database: {e}")
        return []
    finally:
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except Exception:
                pass

def export_history(history_file, output_path, limit=None, since_days=None):
    """
    Export browsing history from a Brave History file to JSON.
    
    Parameters:
    - history_file: Path to the History SQLite database
    - output_path: Path to save the JSON output
    - limit: Maximum number of entries to export (None for all)
    - since_days: Only export entries from the last N days (None for all)
    
    Returns True if successful, False otherwise.
    """
    history_data = read_history(history_file, limit, since_days)
    
    if not history_data:
        logger.warning("No history data found or error occurred")
        return False
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2)
        
        logger.info(f"Exported {len(history_data)} history entries to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error exporting history: {e}")
        return False

def import_history(input_file, history_file):
    """
    Import browsing history from a JSON file to Brave's History database.
    
    Parameters:
    - input_file: Path to the JSON file containing history data
    - history_file: Path to the Brave History SQLite database
    
    Returns True if successful, False otherwise.
    """
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return False
    
    try:
        # Read the input file
        with open(input_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        
        if not history_data:
            logger.warning("No history data found in input file")
            return False
        
        # Create a temporary copy of the history database
        temp_db = os.path.join(tempfile.gettempdir(), "temp_import_history")
        
        if os.path.exists(history_file):
            shutil.copy2(history_file, temp_db)
        else:
            logger.warning(f"History file not found: {history_file}")
            # Create a new empty database
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS urls (
                    id INTEGER PRIMARY KEY,
                    url TEXT NOT NULL,
                    title TEXT,
                    visit_count INTEGER DEFAULT 0 NOT NULL,
                    typed_count INTEGER DEFAULT 0 NOT NULL,
                    last_visit_time INTEGER NOT NULL,
                    hidden INTEGER DEFAULT 0 NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS visits (
                    id INTEGER PRIMARY KEY,
                    url INTEGER NOT NULL,
                    visit_time INTEGER NOT NULL,
                    from_visit INTEGER,
                    transition INTEGER DEFAULT 0 NOT NULL,
                    segment_id INTEGER,
                    visit_duration INTEGER DEFAULT 0 NOT NULL,
                    FOREIGN KEY(url) REFERENCES urls(id)
                )
            ''')
            conn.commit()
            conn.close()
        
        try:
            # Connect to the database
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Import history data
            for entry in history_data:
                url = entry.get('url')
                title = entry.get('title')
                visit_count = entry.get('visit_count', 1)
                
                # Convert last_visit from ISO format to Chrome time
                last_visit_iso = entry.get('last_visit')
                if last_visit_iso:
                    try:
                        last_visit_dt = datetime.fromisoformat(last_visit_iso)
                        epoch_start = datetime(1970, 1, 1)
                        seconds_since_epoch = (last_visit_dt - epoch_start).total_seconds()
                        # Convert to Chrome time (microseconds since Jan 1, 1601)
                        last_visit_time = int((seconds_since_epoch + 11644473600) * 1000000)
                    except Exception:
                        last_visit_time = int(datetime.now().timestamp() * 1000000)
                else:
                    last_visit_time = int(datetime.now().timestamp() * 1000000)
                
                # Check if URL already exists
                cursor.execute('SELECT id, visit_count FROM urls WHERE url = ?', (url,))
                result = cursor.fetchone()
                
                if result:
                    # Update existing entry
                    url_id, existing_count = result
                    cursor.execute(
                        'UPDATE urls SET visit_count = ?, title = ?, last_visit_time = ? WHERE id = ?',
                        (existing_count + visit_count, title, last_visit_time, url_id)
                    )
                else:
                    # Insert new entry
                    cursor.execute(
                        'INSERT INTO urls (url, title, visit_count, last_visit_time) VALUES (?, ?, ?, ?)',
                        (url, title, visit_count, last_visit_time)
                    )
                    
                    # Get the ID of the inserted URL
                    cursor.execute('SELECT last_insert_rowid()')
                    url_id = cursor.fetchone()[0]
                
                # Add a visit entry
                cursor.execute(
                    'INSERT INTO visits (url, visit_time, transition) VALUES (?, ?, 805306368)',
                    (url_id, last_visit_time)
                )
            
            conn.commit()
            
            # Back up the current history file
            if os.path.exists(history_file):
                backup_file = f"{history_file}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                shutil.copy2(history_file, backup_file)
                logger.info(f"Backed up current history to {backup_file}")
            
            # Copy the temporary database to the history file
            shutil.copy2(temp_db, history_file)
            
            logger.info(f"Imported {len(history_data)} history entries to {history_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing history: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
            if os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except Exception:
                    pass
                    
    except Exception as e:
        logger.error(f"Error processing history import: {e}")
        return False

if __name__ == "__main__":
    # Simple test if run directly
    import platform
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    system = platform.system()
    if system == 'Windows':
        history_file = os.path.expandvars(r'%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\History')
    else:
        history_file = os.path.expanduser('~/.config/BraveSoftware/Brave-Browser/Default/History')
    
    if os.path.exists(history_file):
        # Test read with last 7 days and limit of 100
        history = read_history(history_file, limit=100, since_days=7)
        print(f"Found {len(history)} recent history entries")
        
        # Test export
        if len(sys.argv) > 1:
            output_file = sys.argv[1]
            export_history(history_file, output_file, limit=100, since_days=7)
            print(f"Exported history to {output_file}") 