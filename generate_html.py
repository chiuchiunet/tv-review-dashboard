#!/usr/bin/env python3
"""Generate HTML page from F1 database"""
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

def get_lap_times(race_id, limit=50):
    """Get lap times for a race (limited)"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT driver_code, lap, lap_time_ms
        FROM lap_times
        WHERE race_id = ?
        ORDER BY lap_time_ms ASC
        LIMIT ?
    ''', (race_id, limit))
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

def generate_html(output_path='index.html'):
    """Generate HTML page"""
    races = get_all_races()
    
    if not races:
        html = """<!DOCTYPE html>
<html>
<head>
    <title>F1 Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 900px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: #eee; }
        h1 { color: #e94560; }
        .no-data { text-align: center; padding: 50px; color: #888; }
    </style>
</head>
<body>
    <h1>🏎️ F1 Dashboard</h1>
    <div class="no-data">
        <p>No race data found.</p>
        <p>Run <code>python3 fetch_race_data.py</code> to fetch data.</p>
    </div>
</body>
</html>"""
        with open(output_path, 'w') as f:
            f.write(html)
        print(f"Created: {output_path}")
        return
    
    # Get latest race
    latest_race = races[0]
    race_id = latest_race[0]
    results = get_race_results(race_id)
    fastest_laps = get_lap_times(race_id, 10)
    
    # Build race selector
    race_options = []
    for r in races:
        selected = 'selected' if r[0] == race_id else ''
        race_options.append(f'<option value="{r[0]}" {selected}>{r[2]} - {r[1]}</option>')
    
    # Build results table
    results_rows = []
    for r in results:
        results_rows.append(f"""<tr>
            <td>{r[0]}</td>
            <td><span class="driver-code">{r[1]}</span></td>
            <td>{r[2]}</td>
            <td>{r[3]}</td>
            <td>{r[4]}</td>
            <td>{r[5]:.0f}</td>
        </tr>""")
    
    # Build fastest laps
    lap_rows = []
    for lap in fastest_laps:
        lap_rows.append(f"""<tr>
            <td>{lap[0]}</td>
            <td>{lap[1]}</td>
            <td class="fastest">{format_lap_time(lap[2])}</td>
        </tr>""")
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>F1 Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 1000px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: #eee; }}
        h1 {{ color: #e94560; margin-bottom: 10px; }}
        h2 {{ color: #0f3460; border-bottom: 2px solid #e94560; padding-bottom: 10px; }}
        
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
        .race-info {{ color: #888; }}
        
        select {{ padding: 10px; font-size: 16px; background: #16213e; color: #eee; 
                 border: 1px solid #0f3460; border-radius: 5px; }}
        
        .grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }}
        
        table {{ width: 100%; border-collapse: collapse; background: #16213e; 
                border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #0f3460; }}
        th {{ background: #0f3460; color: #fff; cursor: pointer; }}
        th:hover {{ background: #e94560; }}
        tr:hover {{ background: #1f4068; }}
        
        .driver-code {{ font-weight: bold; color: #e94560; }}
        .fastest {{ color: #4ade80; font-weight: bold; }}
        
        .card {{ background: #16213e; border-radius: 8px; padding: 20px; }}
        
        @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🏎️ F1 Dashboard</h1>
            <div class="race-info">{latest_race[3]} • {latest_race[4]}</div>
        </div>
        <select id="raceSelect" onchange="loadRace(this.value)">
            {''.join(race_options)}
        </select>
    </div>
    
    <div class="grid">
        <div class="card">
            <h2>📊 Race Results</h2>
            <table id="resultsTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">Pos</th>
                        <th onclick="sortTable(1)">Driver</th>
                        <th onclick="sortTable(2)">Name</th>
                        <th onclick="sortTable(3)">Team</th>
                        <th onclick="sortTable(4)">Gap</th>
                        <th onclick="sortTable(5)">Pts</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(results_rows)}
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>⚡ Fastest Laps</h2>
            <table>
                <thead>
                    <tr><th>Driver</th><th>Lap</th><th>Time</th></tr>
                </thead>
                <tbody>
                    {''.join(lap_rows) if lap_rows else '<tr><td colspan="3">No data</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        function loadRace(raceId) {{
            // In full version, this would fetch data via API
            alert('Race selection coming soon! Data will reload for race: ' + raceId);
        }}
        
        function sortTable(n) {{
            var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
            table = document.getElementById("resultsTable");
            switching = true;
            dir = "asc";
            while (switching) {{
                switching = false;
                rows = table.rows;
                for (i = 1; i < (rows.length - 1); i++) {{
                    shouldSwitch = false;
                    x = rows[i].getElementsByTagName("TD")[n];
                    y = rows[i + 1].getElementsByTagName("TD")[n];
                    if (dir == "asc") {{
                        if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {{
                            shouldSwitch = true;
                            break;
                        }}
                    }} else if (dir == "desc") {{
                        if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) {{
                            shouldSwitch = true;
                            break;
                        }}
                    }}
                }}
                if (shouldSwitch) {{
                    rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                    switching = true;
                    switchcount ++;
                }} else {{
                    if (switchcount == 0 && dir == "asc") {{
                        dir = "desc";
                        switching = true;
                    }}
                }}
            }}
        }}
    </script>
</body>
</html>"""
    
    with open(output_path, 'w') as f:
        f.write(html)
    print(f"Created: {output_path}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate F1 HTML')
    parser.add_argument('--output', default='index.html', help='Output file')
    args = parser.parse_args()
    
    generate_html(args.output)
