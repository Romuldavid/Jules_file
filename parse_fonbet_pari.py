import requests
import pandas as pd
import datetime

def fetch_fonbet_pari():
    url = "https://line-lb51-w.pb06e2-resources.com/events/listBase?lang=ru&scopeMarket=2300"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    resp = requests.get(url, headers=headers, timeout=15)
    data = resp.json()

    sports = {s['id']: s['name'] for s in data.get('sports', [])}
    # map root sports
    sport_parents = {}
    for s in data.get('sports', []):
        parent_id = s.get('parentId')
        if parent_id and parent_id in sports:
            sport_parents[s['id']] = sports[parent_id]
        else:
            sport_parents[s['id']] = s.get('name', '')

    factors = {f['e']: {item['f']: item for item in f.get('factors', [])} for f in data.get('customFactors', [])}

    events = data.get('events', [])
    records = []
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for ev in events:
        if ev.get('place') != 'line':
            continue
        team1 = ev.get('team1', '')
        team2 = ev.get('team2', '')
        if not team1 or not team2:
            continue

        eid = ev.get('id')
        efactors = factors.get(eid, {})

        # 921: P1, 922: X, 923: P2
        p1 = efactors.get(921, {}).get('v')
        px = efactors.get(922, {}).get('v')
        p2 = efactors.get(923, {}).get('v')

        # 924: 1X, 1571: 12, 925: X2
        p1x = efactors.get(924, {}).get('v')
        p12 = efactors.get(1571, {}).get('v')
        px2 = efactors.get(925, {}).get('v')

        # Totals 930: TB, 931: TM
        tb = efactors.get(930, {}).get('v')
        tm = efactors.get(931, {}).get('v')
        tot_val = efactors.get(930, {}).get('pt')
        if not tot_val:
            tot_val = efactors.get(931, {}).get('pt')

        # Handicaps 927: H1, 928: H2
        h1_kf = efactors.get(927, {}).get('v')
        h1_val = efactors.get(927, {}).get('pt')
        h2_kf = efactors.get(928, {}).get('v')
        h2_val = efactors.get(928, {}).get('pt')

        sport_name = sport_parents.get(ev.get('sportId'), 'Футбол')
        tourn = sports.get(ev.get('sportId'), '')

        start_time_ts = ev.get('startTime')
        ev_time = datetime.datetime.fromtimestamp(start_time_ts).strftime("%Y-%m-%d %H:%M") if start_time_ts else ""

        records.append({
            'bookmaker': 'Фонбет',
            'sport': sport_name,
            'tournament': tourn,
            'event_id': eid,
            'event': f"{team1} — {team2}",
            'team1': team1,
            'team2': team2,
            'event_time': ev_time,
            'parsed_time': now_str,
            'P1': p1,
            'X': px,
            'P2': p2,
            '1X': p1x,
            '12': p12,
            'X2': px2,
            'Handicap1_val': h1_val,
            'Handicap1_kf': h1_kf,
            'Handicap2_val': h2_val,
            'Handicap2_kf': h2_kf,
            'Total_val': tot_val,
            'Total_under': tm,
            'Total_over': tb
        })

    df = pd.DataFrame(records)
    df.to_csv('fonbet_odds.csv', index=False, encoding='utf-8-sig')
    print(f"Сохранено {len(df)} событий Фонбет в fonbet_odds.csv")

    # Также сохраним как Pari (т.к. линия идентична или близка)
    df_pari = df.copy()
    df_pari['bookmaker'] = 'PARI'
    df_pari.to_csv('pari_odds.csv', index=False, encoding='utf-8-sig')
    print(f"Сохранено {len(df_pari)} событий PARI в pari_odds.csv")

if __name__ == '__main__':
    fetch_fonbet_pari()
