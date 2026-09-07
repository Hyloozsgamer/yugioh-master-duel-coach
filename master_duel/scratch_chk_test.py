import cv2
import numpy as np

img = cv2.imread(r'C:\Users\msika\.gemini\antigravity-ide\brain\9eebdd4c-dea1-49c0-afcc-f063543bc732\phase_popup_check.png')
h, w = img.shape[:2]

NODES_SPECS = [
    {'name': 'Scenario',    'type': 'scenario',  'click': (0.18, 0.53), 'check': (0.215, 0.605)},
    {'name': 'Practice',    'type': 'practice',  'click': (0.31, 0.53), 'check': (0.342, 0.605)},
    {'name': 'Duel',        'type': 'duel',      'click': (0.44, 0.53), 'check': (0.472, 0.605)},
    {'name': 'Goal',        'type': 'scenario',  'click': (0.56, 0.53), 'check': (0.592, 0.605)},
    {'name': 'Locked',      'type': 'gate_lock', 'click': (0.56, 0.28), 'check': None},
    {'name': 'BranchDuel1', 'type': 'duel',      'click': (0.69, 0.28), 'check': (0.722, 0.355)},
    {'name': 'BranchDuel2', 'type': 'duel',      'click': (0.81, 0.28), 'check': (0.842, 0.355)},
]

completed = []
next_target = None

for node in NODES_SPECS:
    chk = node.get('check')
    if chk is None:
        continue
    chk_x, chk_y = chk
    cx = int(chk_x * w)
    cy = int(chk_y * h)
    crop = img[max(0, cy - 20):min(h, cy + 20), max(0, cx - 20):min(w, cx + 20)]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    # Orange or Yellow or Blue checkmark
    mask = cv2.inRange(hsv, np.array([5, 90, 90]), np.array([40, 255, 255])) + \
           cv2.inRange(hsv, np.array([90, 90, 90]), np.array([130, 255, 255]))
    pixels = np.count_nonzero(mask)
    is_done = pixels > 120
    print(f"{node['name']}: {pixels} pixels -> is_done: {is_done}")
    if is_done:
        completed.append(node['name'])
    elif next_target is None:
        next_target = node

print('COMPLETED:', completed)
print('NEXT TARGET:', next_target['name'] if next_target else None)
