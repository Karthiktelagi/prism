from dashboard.alert_store import push_alert, get_alerts, acknowledge, unread_count, ack_all, schedule_all_critical, get_stats
import os

id1 = push_alert('CNC_02', 85.0, 'critical', 'High vibration and temperature spike detected', {'temperature_C': 95.2})
id2 = push_alert('PUMP_03', 72.5, 'alert', 'Sustained current drift above baseline', {'current_A': 18.4})
id3 = push_alert('CNC_01', 45.0, 'watch', 'RPM deviating from normal range', {'rpm': 2850})
print('Pushed:', id1, id2, id3)

alerts = get_alerts(10)
print('Stored alerts:', len(alerts))
print('First alert:', alerts[0]['machine_id'], alerts[0]['risk_level'], alerts[0]['risk_score'])
print('Unread count:', unread_count())
acknowledge(id1, 'manager')
print('After ack:', unread_count())
stats = get_stats()
print('Stats:', stats)
db = os.path.abspath(os.path.join('data', 'alerts.db'))
print('DB path:', db, 'exists:', os.path.exists(db))
