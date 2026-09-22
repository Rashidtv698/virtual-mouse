import pyautogui

# Failsafe: moving mouse to a screen corner (0,0) aborts the script.
# Keep this ON while developing — it's a safety net if the cursor goes rogue.
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0  # don't let pyautogui add its own delay per call — we control frame rate

class MouseController:
    def __init__(self, smoothing_factor=0.5):
        self.scroll_ref_y = None
        self.smoothing_factor = smoothing_factor
        self.prev_x, self.prev_y = 0, 0

    def move(self, target_x, target_y):
        
        smooth_x = self.prev_x + (target_x - self.prev_x) * (1 - self.smoothing_factor)
        smooth_y = self.prev_y + (target_y - self.prev_y) * (1 - self.smoothing_factor)

        pyautogui.moveTo(smooth_x, smooth_y)

        self.prev_x, self.prev_y = smooth_x, smooth_y