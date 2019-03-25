import sched
import time
import threading
from datetime import datetime


def execSchedule(exectime_str, func, args=()):
    now = datetime.now()
    exectime = datetime.strptime(exectime_str, '%Y/%M/%d %H:%M:%S')
    lefttime = exectime - now
    if lefttime.seconds < 0:
        return -1

    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(lefttime.seconds, 1, func, args)
    scheduler.run()


class printScheduler:
    def __init__(self, printer):
        self.printer = printer
        self.id_count = 0
        self.is_finish = False
        self.is_started = False
        self.schedules = []

    def add(self, datetime, filename):
        id = self.id_count
        self.schedules.append(
            {'id': id, 'time': datetime, 'filename': filename}
            )
        self.id_count += 1
        # return schedule id
        return id

    def start(self):
        if not self.is_started:
            self.is_finish = False
            self.th = threading.Thread(
                        target=self.__scheduler_proc,
                        name="scheduler_thread"
                        )
            self.th.setDaemon(True)
            self.th.start()

    def finish(self):
        self.is_finish = True
        self.th.join()
        self.is_started = False

    def __scheduler_proc(self):
        while True:
            if self.is_finish:
                break

            now = datetime.now()
            for index, schedule in enumerate(self.schedules):
                if now >= schedule['time']:
                    if not self.printer.is_printing:
                        self.printer.startPrint(schedule['filename'])
                        self.schedules.pop(index)
                        break

            time.sleep(60.0)
