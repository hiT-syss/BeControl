import time
from collections import deque
from queue import Empty, Queue
from threading import Event, Thread

import cv2
import mediapipe as mp

HANDS = ("Red", "Green")
FINGERS = ("Index", "Middle", "Ring", "Pinky")
GESTURES = {
    mask: ("Fist" if mask == 0 else "Open palm" if mask == 15 else
           " + ".join(name for index, name in enumerate(FINGERS) if mask & (1 << index)))
    for mask in range(16)
}


class Camera(Thread):
    def __init__(self, index):
        super().__init__(daemon=True)
        self.index = index
        self.frames = Queue(maxsize=1)
        self.stop = Event()
        self.error = None

    def run(self):
        capture = None
        try:
            capture = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
            if not capture.isOpened():
                raise RuntimeError("Could not open the camera. Check the camera number and Windows camera permissions.")
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            history = {side: deque(maxlen=4) for side in HANDS}
            stable = dict.fromkeys(HANDS)
            failures = 0
            with mp.solutions.hands.Hands(max_num_hands=2, min_detection_confidence=0.7,
                                          min_tracking_confidence=0.7) as tracker:
                while not self.stop.is_set():
                    ok, frame = capture.read()
                    if not ok:
                        failures += 1
                        if failures >= 10:
                            raise RuntimeError("Could not read a frame from the camera.")
                        self.stop.wait(0.05)
                        continue
                    failures = 0
                    frame = cv2.flip(frame, 1)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    result = tracker.process(rgb)
                    observed = dict.fromkeys(HANDS)
                    tilt = 0
                    hands = sorted(result.multi_hand_landmarks or [], key=lambda hand: hand.landmark[0].x)
                    for index, hand in enumerate(hands):
                        points = hand.landmark
                        side = index if len(hands) == 2 else int(points[0].x >= 0.5)
                        color = (255, 65, 90) if side == 0 else (40, 235, 150)
                        style = mp.solutions.drawing_utils.DrawingSpec(color=color, thickness=2, circle_radius=3)
                        mp.solutions.drawing_utils.draw_landmarks(
                            rgb, hand, mp.solutions.hands.HAND_CONNECTIONS, style, style)
                        observed[HANDS[side]] = sum(
                            1 << finger for finger, tip in enumerate((8, 12, 16, 20))
                            if points[tip].y < points[tip - 2].y
                        )
                        if side == 0:
                            tilt = points[9].x - points[0].x
                    for side, mask in observed.items():
                        samples = history[side]
                        if mask is None:
                            samples.clear()
                            stable[side] = None
                        else:
                            samples.append(mask)
                            if len(samples) == 4 and len(set(samples)) == 1:
                                stable[side] = mask
                    try:
                        self.frames.get_nowait()
                    except Empty:
                        pass
                    self.frames.put_nowait((rgb, stable.copy(), tilt, time.monotonic()))
        except Exception as error:
            self.error = str(error)
        finally:
            if capture is not None:
                capture.release()
