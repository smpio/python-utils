import sys
import queue
import threading


class SupervisedThreadGroup:
    def __init__(self):
        self.queue = queue.Queue()
        self.threads = []

    def add_thread(self, thread):
        if not isinstance(thread, SupervisedThread):
            raise Exception(f'Thread {thread} is not of SupervisedThread class')

        thread._supervise_queue = self.queue
        self.threads.append(thread)

    def start_all(self):
        for thread in self.threads:
            thread.start()

    def wait_any(self):
        thread, ret, exc_info = self.queue.get()
        thread.join()  # wait for thread to finalize
        return thread, ret, exc_info


class SupervisedThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('daemon', True)
        super().__init__(*args, **kwargs)

    def run(self):
        try:
            ret = self.run_supervised()
            exc_info = None
        except:  # noqa
            ret = None
            exc_info = sys.exc_info()
            raise
        finally:
            queue = getattr(self, '_supervise_queue', None)
            if queue:
                queue.put((self, ret, exc_info))

    def run_supervised(self):
        raise NotImplementedError
