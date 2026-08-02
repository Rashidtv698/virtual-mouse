import math
from src.landmarks_reference import (
    THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP,
    THUMB_IP, INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP,
    PINKY_MCP
)

class GestureDetector:
    def __init__(self, pinch_threshold=40):
        """
        pinch_threshold: max pixel distance between two fingertips
        to count as a 'pinch' (click gesture). Tune this after testing —
        it depends on your camera distance and frame resolution.
        """
        self.pinch_threshold = pinch_threshold

    def _distance(self, p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def _landmark_dict(self, landmarks):
        # landmarks is [(id, x, y), ...] -> convert to {id: (x, y)} for easy lookup
        return {id: (x, y) for id, x, y in landmarks}

    def fingers_up(self, landmarks):
        """
        Returns a list of 5 booleans: [thumb, index, middle, ring, pinky]
        True = finger extended, False = finger curled down.
        """
        lm = self._landmark_dict(landmarks)
        fingers = []

        # Thumb: extended = tip is FARTHER from palm (pinky_mcp) than the IP joint is.
        # Distance-based, so it works the same for left AND right hands.
        thumb_tip_dist = self._distance(lm[THUMB_TIP], lm[PINKY_MCP])
        thumb_ip_dist = self._distance(lm[THUMB_IP], lm[PINKY_MCP])
        fingers.append(thumb_tip_dist > thumb_ip_dist)

        finger_pairs = [
            (INDEX_TIP, INDEX_PIP),
            (MIDDLE_TIP, MIDDLE_PIP),
            (RING_TIP, RING_PIP),
            (PINKY_TIP, PINKY_PIP),
        ]
        for tip, pip in finger_pairs:
            fingers.append(lm[tip][1] < lm[pip][1])

        return fingers  # e.g. [False, True, False, False, False] = only index up

    def get_pinch_distance(self, landmarks, tip_a, tip_b):
        lm = self._landmark_dict(landmarks)
        if tip_a not in lm or tip_b not in lm:
            return None
        return self._distance(lm[tip_a], lm[tip_b])

    def is_pinching(self, landmarks, tip_a, tip_b):
        dist = self.get_pinch_distance(landmarks, tip_a, tip_b)
        if dist is None:
            return False
        return dist < self.pinch_threshold