import cv2
import numpy as np

img = cv2.imread(r'C:\Users\msika\.gemini\antigravity-ide\brain\9eebdd4c-dea1-49c0-afcc-f063543bc732\live_game_now.png')
h, w, _ = img.shape

NODES_SPECS = [
    {"name": "Scenario", "click": (0.18, 0.53), "check": (0.215, 0.605)},
    {"name": "Practice", "click": (0.31, 0.53), "check": (0.342, 0.605)},
    {"name": "Duel",     "click": (0.44, 0.53), "check": (0.472, 0.605)},
    {"name": "Goal",     "click": (0.56, 0.53), "check": (0.592, 0.605)},
    {"name": "Locked",   "click": (0.56, 0.28), "check": None},
    {"name": "BranchDuel1", "click": (0.69, 0.28), "check": (0.722, 0.355)},
    {"name": "BranchDuel2", "click": (0.81, 0.28), "check": (0.842, 0.355)},
]

completed = []
next_node = None

for node in NODES_SPECS:
    if node["check"] is None:
        continue
    chk_x, chk_y = node["check"]
    cx = int(chk_x * w)
    cy = int(chk_y * h)
    crop = img[cy-18:cy+18, cx-18:cx+18]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    gold = cv2.inRange(hsv, np.array([15, 140, 140]), np.array([35, 255, 255]))
    is_done = np.count_nonzero(gold) > 150
    if is_done:
        completed.append(node["name"])
    elif next_node is None:
        next_node = node

print("Detected completed nodes:", completed)
print("Next uncompleted target:", next_node["name"] if next_node else "ALL COMPLETED")
