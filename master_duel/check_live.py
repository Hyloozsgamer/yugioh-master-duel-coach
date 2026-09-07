import time, cv2
from master_duel.vision.screen_capture import ScreenCapture
from master_duel.input.input_controller import InputController
cap = ScreenCapture(game_title='masterduel')
inp = InputController(screen_capture=cap)
inp.bring_to_front()
time.sleep(0.5)
f = cap.capture()
if f is not None:
    cv2.imwrite(r'C:\Users\msika\.gemini\antigravity-ide\brain\9eebdd4c-dea1-49c0-afcc-f063543bc732\live_game_now.png', f)
    print('Captured live_game_now')
