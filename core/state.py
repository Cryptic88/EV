import threading


class AssistantState:

    def __init__(self):

        self.stop_event = threading.Event()

        self.log_callback = print
        self.status_callback = lambda status: None

        self.current_status = "idle"

    def log(self, *text):

        self.log_callback(*text)

    def set_status(self, status):

        self.current_status = status

        self.status_callback(status)

    def stop(self):

        self.stop_event.set()

    def reset(self):

        self.stop_event.clear()

        self.current_status = "idle"

    def is_stopped(self):

        return self.stop_event.is_set()