#!/usr/bin/env python3
"""
Brave Browser Bookmarks Module
-----------------------------
Utilities for handling bookmarks in Brave browser.
"""

import os
import json
import logging
import shutil
from datetime import datetime

logger = logging.getLogger('brave_extractor.bookmarks')

def read_bookmarks(bookmarks_file):
    """
    Read bookmarks from a Brave Bookmarks file.
    Returns the parsed bookmarks data as a Python object.
    """
    if not os.path.exists(bookmarks_file):
        logger.error(f"Bookmarks file not found: {bookmarks_file}")
        return None
        
    try:
        with open(bookmarks_file, 'r', encoding='utf-8') as f:
            bookmarks_data = json.load(f)
        return bookmarks_data
    except Exception as e:
        logger.error(f"Error reading bookmarks file: {e}")
        return None

def export_bookmarks(bookmarks_file, output_path=None):
    """
    Export bookmarks from a Brave Bookmarks file.
    If output_path is provided, writes the bookmarks to a JSON file.
    Returns the bookmarks data.
    """
    bookmarks_data = read_bookmarks(bookmarks_file)
    
    if not bookmarks_data:
        return None
    
    if output_path:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(bookmarks_data, f, indent=2)
            logger.info(f"Bookmarks exported to {output_path}")
        except Exception as e:
            logger.error(f"Error exporting bookmarks: {e}")
    
    return bookmarks_data

def export_bookmarks_html(bookmarks_file, output_path):
    """
    Export bookmarks from a Brave Bookmarks file to HTML format.
    This format is compatible with most browsers for import.
    """
    bookmarks_data = read_bookmarks(bookmarks_file)
    
    if not bookmarks_data:
        return False
    
    try:
        html = ['<!DOCTYPE NETSCAPE-Bookmark-file-1>',
                '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
                '<TITLE>Bookmarks</TITLE>',
                '<H1>Bookmarks</H1>',
                '<DL><p>']
        
        # Process bookmark bar
        bookmark_bar = bookmarks_data.get('roots', {}).get('bookmark_bar', {})
        if bookmark_bar:
            html.append(f'<DT><H3 ADD_DATE="{int(datetime.now().timestamp())}" PERSONAL_TOOLBAR_FOLDER="true">{bookmark_bar.get("name", "Bookmarks Bar")}</H3>')
            html.append('<DL><p>')
            
            process_bookmarks_folder(bookmark_bar, html)
            
            html.append('</DL><p>')
        
        # Process other bookmarks
        other = bookmarks_data.get('roots', {}).get('other', {})
        if other:
            html.append(f'<DT><H3 ADD_DATE="{int(datetime.now().timestamp())}">{other.get("name", "Other Bookmarks")}</H3>')
            html.append('<DL><p>')
            
            process_bookmarks_folder(other, html)
            
            html.append('</DL><p>')
        
        html.append('</DL><p>')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html))
        
        logger.info(f"Bookmarks exported to HTML at {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error exporting bookmarks to HTML: {e}")
        return False

def process_bookmarks_folder(folder, html, indent_level=1):
    """Helper function to process bookmarks folders recursively for HTML export."""
    for child in folder.get('children', []):
        if child.get('type') == 'url':
            url = child.get('url', '')
            name = child.get('name', url)
            add_date = child.get('date_added', int(datetime.now().timestamp()))
            html.append(f'{"  " * indent_level}<DT><A HREF="{url}" ADD_DATE="{add_date}">{name}</A>')
        elif child.get('type') == 'folder':
            name = child.get('name', 'Folder')
            add_date = child.get('date_added', int(datetime.now().timestamp()))
            html.append(f'{"  " * indent_level}<DT><H3 ADD_DATE="{add_date}">{name}</H3>')
            html.append(f'{"  " * indent_level}<DL><p>')
            
            process_bookmarks_folder(child, html, indent_level + 1)
            
            html.append(f'{"  " * indent_level}</DL><p>')

def import_bookmarks(input_file, bookmarks_file):
    """
    Import bookmarks from a JSON file to Brave's Bookmarks file.
    Returns True if successful, False otherwise.
    """
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return False
    
    try:
        # Read the input file
        with open(input_file, 'r', encoding='utf-8') as f:
            bookmarks_data = json.load(f)
        
        # Back up the current bookmarks file
        if os.path.exists(bookmarks_file):
            backup_file = f"{bookmarks_file}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            shutil.copy2(bookmarks_file, backup_file)
            logger.info(f"Backed up current bookmarks to {backup_file}")
        
        # Write the new bookmarks
        with open(bookmarks_file, 'w', encoding='utf-8') as f:
            json.dump(bookmarks_data, f, indent=2)
        
        logger.info(f"Bookmarks imported successfully to {bookmarks_file}")
        return True
    except Exception as e:
        logger.error(f"Error importing bookmarks: {e}")
        return False

def count_bookmarks(bookmarks_data):
    """Count the number of bookmarks in the data."""
    if not bookmarks_data:
        return 0
    
    count = 0
    
    def count_in_folder(folder):
        nonlocal count
        for child in folder.get('children', []):
            if child.get('type') == 'url':
                count += 1
            elif child.get('type') == 'folder':
                count_in_folder(child)
    
    roots = bookmarks_data.get('roots', {})
    for root_name in ['bookmark_bar', 'other', 'synced']:
        root = roots.get(root_name, {})
        count_in_folder(root)
    
    return count

if __name__ == "__main__":
    # Simple test if run directly
    import platform
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    system = platform.system()
    if system == 'Windows':
        bookmarks_file = os.path.expandvars(r'%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\Bookmarks')
    else:
        bookmarks_file = os.path.expanduser('~/.config/BraveSoftware/Brave-Browser/Default/Bookmarks')
    
    if os.path.exists(bookmarks_file):
        # Test read
        bookmarks = read_bookmarks(bookmarks_file)
        count = count_bookmarks(bookmarks)
        print(f"Found {count} bookmarks")
        
        # Test export to HTML
        if len(sys.argv) > 1:
            output_file = sys.argv[1]
            export_bookmarks_html(bookmarks_file, output_file)
            print(f"Exported bookmarks to {output_file}") 