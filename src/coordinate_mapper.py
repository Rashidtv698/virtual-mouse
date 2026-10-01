import numpy as np

class CoordinateMapper:
    def __init__(self, cam_width, cam_height, screen_width, screen_height, margin=100):
    
        self.cam_width = cam_width
        self.cam_height = cam_height
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.margin = margin

        # Active region boundaries within the camera frame
        self.active_x_min = margin
        self.active_x_max = cam_width - margin
        self.active_y_min = margin
        self.active_y_max = cam_height - margin

    def map_to_screen(self, cam_x, cam_y):
        cam_x = np.clip(cam_x, self.active_x_min, self.active_x_max)
        cam_y = np.clip(cam_y, self.active_y_min, self.active_y_max)

        screen_x = np.interp(cam_x, [self.active_x_min, self.active_x_max],
                            [2, self.screen_width - 2])   # inset by 2px from true edges
        screen_y = np.interp(cam_y, [self.active_y_min, self.active_y_max],
                            [2, self.screen_height - 2])

        return int(screen_x), int(screen_y)