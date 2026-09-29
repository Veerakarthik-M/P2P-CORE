import sys
sys.path.insert(0, 'SIH26123')
errors = []

try:
    import config
    print(f'[OK]  config -- BATTERY_INIT={config.BATTERY_INIT}, LOW={config.BATTERY_LOW}, CRIT={config.BATTERY_CRITICAL}, CHARGER_COLOR={config.COLOR_CHARGER}')
except Exception as e: errors.append(f'config: {e}')

try:
    import warehouse
    w = warehouse.Warehouse()
    print(f'[OK]  warehouse -- grid {w.rows}x{w.cols}, lanes={len(w.narrow_lanes)}, chargers={[c["id"] for c in w.charging_stations]}')
except Exception as e: errors.append(f'warehouse: {e}')

try:
    import robot
    r = robot.Robot('R1', (1,1), task_priority=5, urgency=4)
    r.calculate_score()
    r.update_battery(1.0, is_moving=True)
    print(f'[OK]  robot -- score={r.score:.2f}, battery={r.battery:.1f}, CHARGING_state={robot.CHARGING}')
    r2 = robot.Robot('R3', (1,1))
    r2.battery = 12.0
    r2.battery_status = robot._battery_status(12.0)
    print(f'[OK]  robot._battery_status(12%)={r2.battery_status}')
except Exception as e: errors.append(f'robot: {e}')

try:
    import communication
    bus = communication.MessageBus()
    bus.log_negotiation('R1','R2','NEGOTIATE', 1.0, 'test negotiate')
    bus.log_negotiation('R1','R2','BATT_LOW', 2.0, 'battery critical')
    bus.log_negotiation('R1','R2','CHARGING', 3.0, 'docked at C1')
    log = bus.get_negotiation_log()
    print(f'[OK]  communication -- neg_log entries: {len(log)}, last: {log[-1][:60]}')
except Exception as e: errors.append(f'communication: {e}')

try:
    import conflict
    w2 = warehouse.Warehouse()
    cm = conflict.ConflictManager(w2)
    print(f'[OK]  conflict -- lane_owner keys: {list(cm.lane_owner.keys())}')
except Exception as e: errors.append(f'conflict: {e}')

try:
    import scenarios
    w3 = warehouse.Warehouse()
    total = len(scenarios.SCENARIOS)
    print(f'[OK]  scenarios -- {total} scenarios total')
    for i, sc in enumerate(scenarios.SCENARIOS):
        robots_sc, name_sc = sc(w3)
        ids = [r.robot_id for r in robots_sc]
        batts = [f'{r.robot_id}={r.battery:.0f}%' for r in robots_sc]
        print(f'  Scenario {i+1}: "{name_sc}" -- robots={ids}, batteries={batts}')
except Exception as e: errors.append(f'scenarios: {e}')

try:
    import priority
    s = priority.priority_score(5, 4, 0)
    print(f'[OK]  priority -- score(P=5,U=4,W=0)={s:.2f}')
    winner = priority.choose_lane_owner([robot.Robot('R1',(1,1),5,4), robot.Robot('R2',(2,2),3,2)])
    print(f'[OK]  priority -- choose_lane_owner R1 vs R2 -> winner={winner.robot_id}')
except Exception as e: errors.append(f'priority: {e}')

try:
    import metrics
    m = metrics.MetricsTracker()
    print(f'[OK]  metrics -- tracker created OK')
except Exception as e: errors.append(f'metrics: {e}')

print()
if errors:
    print('ERRORS FOUND:')
    for e in errors: print(' ', e)
    sys.exit(1)
else:
    print('ALL MODULES: PASS')
