#!/usr/bin/env python3
"""
Test scraper locally with correct anon key
"""

import os
import sys
import subprocess

# Set environment variables with the correct anon key
os.environ['SUPABASE_URL'] = 'https://yqawmzggcgpeyaaynrjk.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlxYXdtemdnY2dwZXlhYXlucmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTUwMTA5MjYsImV4cCI6MjA3MDU4NjkyNn0.zyEEYeQkKq4O3h47KPiKvDD0qwMaostsMguxcNR4ah4'

print("Environment variables set:")
print(f"SUPABASE_URL: {os.environ.get('SUPABASE_URL')}")
print(f"SUPABASE_KEY: {os.environ.get('SUPABASE_KEY')[:20]}...")

# Run the main script with arguments
if __name__ == '__main__':
    args = ['--mode', 'full', '--batch-size', '1', '--limit', '3']
    print(f"Running: python main.py {' '.join(args)}")
    result = subprocess.run([sys.executable, 'main.py'] + args)
    sys.exit(result.returncode)
