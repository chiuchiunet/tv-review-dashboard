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
    1: "NOR",    # Lando Norris
    3: "VER",    # Max Verstappen
    5: "BOR",    # Gabriel Bortoleto
    6: "HAD",    # Isack Hadjar
    10: "GAS",   # Pierre Gasly
    11: "PER",   # Sergio Perez
    12: "ANT",   # Kimi Antonelli
    14: "ALO",   # Fernando Alonso
    16: "LEC",   # Charles Leclerc
    18: "STR",   # Lance Stroll
    23: "ALB",   # Alexander Albon
    27: "HUL",   # Nico Hulkenberg
    30: "LAW",   # Liam Lawson
    31: "OCO",   # Esteban Ocon
    41: "LIN",   # Arvid Lindblad
    43: "COL",   # Franco Colapinto
    44: "HAM",   # Lewis Hamilton
    55: "SAI",   # Carlos Sainz
    63: "RUS",   # George Russell
    77: "BOT",   # Valtteri Bottas
    81: "PIA",   # Oscar Piastri
    87: "BEA",   # Oliver Bearman
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
