#!/usr/bin/env python3
"""Fetch race data from OpenF1 API and save to database"""
import json
import urllib.request
import urllib.error
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))
from db import get_conn, init_db

API_BASE = "https://api.openf1.org/v1"

# Driver number to code mapping (2026 grid)
DRIVER_CODES = {
    1: "NOR", 3: "VER", 4: "PIA", 5: "BOR", 6: "ALO",
    10: "GAS", 11: "MAG", 12: "BUI", 14: "ALO", 16: "LEC",
    18: "STR", 20: "MAG", 21: "DRR", 22: "TSU", 23: "COL",
    24: "ZHO", 27: "HUL", 30: "LAW", 31: "OCO", 36: "LAW",
    37: "BEO", 38: "HAD", 39: "NISS", 40: "BEO", 41: "VEST",
    43: "DOO", 44: "HAM", 45: "BEAR", 46: "OSM", 47: "SCH",
    50: "AUB", 51: "MA", 52: "BAY", 53: "MANS", 54: "ISA",
    55: "SAI", 56: "RUS", 57: "RUS", 63: "RUSS", 64: "SIM",
    70: "MANS", 71: "ISA", 73: "VEST", 74: "PHI", 77: "ANT",
    78: "GAS", 79: "BER", 81: "PIA", 87: "OCO", 88: "DRR",
    89: "LAT", 91: "GAS", 92: "SAI", 93: "HAD", 94: "NISS",
    95: "ZHO", 96: "ZHO", 97: "BORT", 98: "GARC", 99: "FIA"
}

def fetch_json(url):
    """Fetch JSON from OpenF1 API"""
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_session_key(year=2026, country=None):
    """Get session key for a race"""
    sessions = fetch_json(f"{API_BASE}/sessions?year={year}&session_name=Race")
    if not sessions:
        return None
    
    # If no country specified, return latest
    if not country:
        return sessions[-1].get('session_key')
    
    for s in reversed(sessions):
        if s.get('country_name') == country:
            return s.get('session_key')
    return sessions[-1].get('session_key')

def fetch_race_results(session_key):
    """Fetch race results for a session"""
    # Get position data
    positions = fetch_json(f"{API_BASE}/position?session_key={session_key}")
    if not positions:
        return []
    
    # Group by driver and get final position
    driver_positions = {}
    for p in positions:
        driver = p.get('driver_number')
        if driver not in driver_positions:
            driver_positions[driver] = []
        driver_positions[driver].append(p)
    
    results = []
    for driver, pos_data in driver_positions.items():
        # Get final position (last data point)
        final_pos = pos_data[-1]
        
        # Get driver info
        drivers = fetch_json(f"{API_BASE}/drivers?driver_number={driver}&session_key={session_key}")
        driver_info = drivers[0] if drivers else {}
        
        # Get driver code from mapping or use number
        driver_code = DRIVER_CODES.get(driver, str(driver))
        
        results.append({
            'position': final_pos.get('position'),
            'driver_code': driver_code,
            'driver_name': f"{driver_info.get('first_name', '')} {driver_info.get('last_name', '')}".strip(),
            'team': driver_info.get('team_name', 'Unknown'),
        })
    
    # Sort by position
    results.sort(key=lambda x: x['position'] or 999)
    return results

def fetch_lap_times(session_key, driver_number=None):
    """Fetch lap times"""
    url = f"{API_BASE}/lap_times?session_key={session_key}"
    if driver_number:
        url += f"&driver_number={driver_number}"
    
    laps = fetch_json(url) or []
    
    # Add driver code to each lap
    for lap in laps:
        driver_num = lap.get('driver_number')
        lap['driver_code'] = DRIVER_CODES.get(driver_num, str(driver_num))
    
    return laps

def save_race(session_key, race_name, date, country, circuit, results, laps):
    """Save race data to database"""
    conn = get_conn()
    cursor = conn.cursor()
    
    # Insert race
    cursor.execute('''
        INSERT OR REPLACE INTO races (session_key, name, date, country, circuit)
        VALUES (?, ?, ?, ?, ?)
    ''', (session_key, race_name, date, country, circuit))
    
    race_id = cursor.lastrowid
    
    # Get race_id if already exists
    cursor.execute('SELECT id FROM races WHERE session_key = ?', (session_key,))
    race_id = cursor.fetchone()[0]
    
    # Clear existing results for this race
    cursor.execute('DELETE FROM race_results WHERE race_id = ?', (race_id,))
    cursor.execute('DELETE FROM lap_times WHERE race_id = ?', (race_id,))
    
    # Insert results
    for r in results:
        cursor.execute('''
            INSERT INTO race_results (race_id, position, driver_code, driver_name, team, time_gap, points)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (race_id, r['position'], r['driver_code'], r['driver_name'], r['team'], 
              r.get('time_gap', ''), r.get('points', 0)))
    
    # Insert lap times
    for lap in laps:
        cursor.execute('''
            INSERT INTO lap_times (race_id, driver_code, lap, lap_time_ms, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (race_id, lap.get('driver_code'), lap.get('lap'), 
              lap.get('lap_time'), lap.get('date')))
    
    conn.commit()
    conn.close()
    print(f"Saved race: {race_name} (ID: {race_id})")
    return race_id

def fetch_and_save(session_key=None, country=None):
    """Main function to fetch and save race data"""
    init_db()
    
    if not session_key:
        session_key = get_session_key(country=country)
        if not session_key:
            print("No session found")
            return
    
    # Get session info
    sessions = fetch_json(f"{API_BASE}/sessions?session_key={session_key}")
    if not sessions:
        print("Session not found")
        return
    
    session = sessions[0]
    race_name = session.get('meeting_name', 'Unknown Race')
    date = session.get('date_start', '')[:10]
    country = session.get('country_name', country or 'Unknown')
    circuit = session.get('circuit_short_name', 'Unknown')
    
    print(f"Fetching data for: {race_name} ({country})")
    
    # Fetch results and laps
    results = fetch_race_results(session_key)
    laps = fetch_lap_times(session_key)
    
    print(f"Got {len(results)} drivers, {len(laps)} lap times")
    
    # Save to database
    save_race(session_key, race_name, date, country, circuit, results, laps)
    print("Done!")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Fetch F1 race data')
    parser.add_argument('--session-key', type=int, help='Session key')
    parser.add_argument('--country', type=str, help='Country name')
    args = parser.parse_args()
    
    fetch_and_save(session_key=args.session_key, country=args.country)
