#!/usr/bin/env python3
"""Generate markdown report from F1 database"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from db import get_conn

def get_all_races():
    """Get all races from database"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, date, country, circuit FROM races ORDER BY date DESC')
    races = cursor.fetchall()
    conn.close()
    return races

def get_race_results(race_id):
    """Get results for a specific race"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT position, driver_code, driver_name, team, time_gap, points
        FROM race_results
        WHERE race_id = ?
        ORDER BY position
    ''', (race_id,))
    results = cursor.fetchall()
    conn.close()
    return results

def get_lap_times(race_id, driver_code=None):
    """Get lap times for a race"""
    conn = get_conn()
    cursor = conn.cursor()
    if driver_code:
        cursor.execute('''
            SELECT driver_code, lap, lap_time_ms, timestamp
            FROM lap_times
            WHERE race_id = ? AND driver_code = ?
            ORDER BY lap
        ''', (race_id, driver_code))
    else:
        cursor.execute('''
            SELECT driver_code, lap, lap_time_ms, timestamp
            FROM lap_times
            WHERE race_id = ?
            ORDER BY lap, driver_code
        ''', (race_id,))
    laps = cursor.fetchall()
    conn.close()
    return laps

def format_lap_time(ms):
    """Format lap time from milliseconds"""
    if not ms:
        return '--:--.---'
    seconds = ms / 1000
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:06.3f}"

def generate_report(race_id=None, format='markdown'):
    """Generate report for a race or all races"""
    races = get_all_races()
    
    if not races:
        return "No race data found. Run fetch_race_data.py first!"
    
    if race_id is None:
        race_id = races[0][0]
    
    # Find race info
    race_info = None
    for r in races:
        if r[0] == race_id:
            race_info = r
            break
    
    if not race_info:
        race_info = races[0]
        race_id = race_info[0]
    
    results = get_race_results(race_id)
    laps = get_lap_times(race_id)
    
    # Build report
    lines = []
    lines.append(f"# 🏎️ {race_info[1]}")
    lines.append("")
    lines.append(f"**Date:** {race_info[2]}")
    lines.append(f"**Country:** {race_info[3]}")
    lines.append(f"**Circuit:** {race_info[4]}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📊 Race Results")
    lines.append("")
    lines.append("| Pos | Driver | Team | Time Gap | Points |")
    lines.append("|-----|--------|------|----------|--------|")
    
    for r in results:
        lines.append(f"| {r[0]} | {r[1]} | {r[3]} | {r[4]} | {r[5]:.0f} |")
    
    # Lap times section
    if laps:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## ⏱️ Lap Times")
        lines.append("")
        
        # Group by driver
        driver_laps = {}
        for lap in laps:
            code = lap[0]
            if code not in driver_laps:
                driver_laps[code] = []
            driver_laps[code].append(lap)
        
        for code, driver_laps_data in sorted(driver_laps.items()):
            lines.append(f"### {code}")
            lines.append("")
            lines.append("| Lap | Time |")
            lines.append("|-----|------|")
            for lap_data in driver_laps_data:
                lines.append(f"| {lap_data[1]} | {format_lap_time(lap_data[2])} |")
            lines.append("")
    
    return "\n".join(lines)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate F1 report')
    parser.add_argument('--race-id', type=int, help='Race ID')
    parser.add_argument('--format', default='markdown', help='Output format')
    args = parser.parse_args()
    
    report = generate_report(race_id=args.race_id, format=args.format)
    print(report)

if __name__ == '__main__':
    main()
