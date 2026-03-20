#!/usr/bin/env python3
"""Generate WhatsApp-style text report from F1 database"""
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

def get_race_info(race_id):
    """Get race info"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT name, date, country, circuit FROM races WHERE id = ?', (race_id,))
    race = cursor.fetchone()
    conn.close()
    return race

RACE_NAMES = {
    'Australia': '澳洲大獎賽',
    'China': '中國大獎賽',
    'Japan': '日本大獎賽',
    'Bahrain': '巴林大獎賽',
    'Saudi Arabia': '沙特阿拉伯大獎賽',
    'United States': '美國大獎賽',
    'Canada': '加拿大大獎賽',
    'Monaco': '摩納哥大獎賽',
    'Spain': '西班牙大獎賽',
    'Austria': '奧地利大獎賽',
    'United Kingdom': '英國大獎賽',
    'Belgium': '比利時大獎賽',
    'Hungary': '匈牙利大獎賽',
    'Netherlands': '荷蘭大獎賽',
    'Italy': '意大利大獎賽',
    'Azerbaijan': '阿塞拜疆大獎賽',
    'Singapore': '新加坡大獎賽',
    'Mexico': '墨西哥大獎賽',
    'Brazil': '巴西大獎賽',
    'Qatar': '卡塔爾大獎賽',
    'United Arab Emirates': '阿布扎比大獎賽',
}

CIRCUIT_NAMES = {
    'Shanghai': '上海國際賽車場',
    'Suzuka': '鈴鹿賽道',
    'Melbourne': '墨爾本阿爾伯特公園',
    'Sakhir': '巴林國際賽道',
    'Jeddah': '吉達濱海大道',
    'Austin': '美洲賽道',
    'Montreal': '維倫紐夫賽道',
    'Monaco': '蒙特卡洛街道賽道',
    'Barcelona-Catalunya': '加泰羅尼亞賽道',
    'Red Bull Ring': '紅牛環',
    'Silverstone': '銀石賽道',
    'Spa-Francorchamps': '斯帕-弗朗克爾尚',
    'Hungaroring': '匈牙利環',
    'Zandvoort': '讚德沃爾特',
    'Monza': '蒙扎國家賽道',
    'Baku': '巴庫城市賽道',
    'Marina Bay': '濱海灣街道賽道',
    'Mexico City': '羅德里格斯兄弟賽道',
    'Interlagos': '英特拉格斯',
    'Losail': '洛塞爾國際賽道',
    'Yas Marina': '亞斯碼頭',
}

def generate_whatsapp_report(race_id=None):
    """Generate WhatsApp-style text report"""
    races = get_all_races()
    
    if not races:
        return "⚠️ 沒有數據！請先运行 fetch_race_data.py"
    
    if race_id is None:
        race_id = races[0][0]
    
    race_info = get_race_info(race_id)
    if not race_info:
        race_info = races[0]
        race_id = race_info[0]
    
    race_name = race_info[0]
    race_date = race_info[1]
    country = race_info[2]
    circuit = race_info[3]
    
    # Convert to Chinese names
    race_name_cn = RACE_NAMES.get(country, country)
    circuit_cn = CIRCUIT_NAMES.get(circuit, circuit)
    
    results = get_race_results(race_id)
    
    # Build WhatsApp report (simplified)
    lines = []
    lines.append(f"🏎️ *{race_name_cn}* | 📅 {race_date}")
    lines.append("")
    
    for r in results:
        pos = r[0]
        code = r[1]
        name = r[2]
        team = r[3]
        gap = r[4] or ''
        
        # Format position with emoji
        if pos == 1:
            pos_emoji = "🥇"
        elif pos == 2:
            pos_emoji = "🥈"
        elif pos == 3:
            pos_emoji = "🥉"
        else:
            pos_emoji = f"{pos}."
        
        # Short team name
        team_short = team.split()[0] if team else ''
        
        line = f"{pos_emoji} {code} {name} ({team_short})"
        if gap:
            line += f" +{gap}"
        lines.append(line)
    
    lines.append("")
    lines.append("📊 #F1")
    
    return "\n".join(lines)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--race-id', type=int)
    args = parser.parse_args()
    
    print(generate_whatsapp_report(args.race_id))

if __name__ == '__main__':
    main()
