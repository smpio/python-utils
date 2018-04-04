import time
import threading


class WatchdogThread(threading.Thread):
    def __init__(self, func, interval_seconds):
        super().__init__(daemon=True)
        self.do_loop = True
        self.func = func
        self.interval_seconds = interval_seconds

    def stop(self):
        self.do_loop = False

    def run(self):
        while self.do_loop:
            self.func()
            time.sleep(self.interval_seconds)
