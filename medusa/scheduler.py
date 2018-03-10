# coding=utf-8

import datetime
import logging
import threading
import time

from medusa import exception_handler
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Scheduler(threading.Thread):
    """

    """

    def __init__(self, action, cycle_time=datetime.timedelta(minutes=10), run_delay=datetime.timedelta(minutes=0),
                 start_time=None, thread_name="ScheduledThread", silent=True):
        super(Scheduler, self).__init__()

        self.run_delay = run_delay
        if start_time is None:
            self.lastRun = datetime.datetime.now() + self.run_delay - cycle_time
        else:
            # Set last run to the last full hour
            temp_now = datetime.datetime.now() + cycle_time
            self.lastRun = datetime.datetime(temp_now.year, temp_now.month, temp_now.day, temp_now.hour, 0, 0, 0) + self.run_delay - cycle_time
        self.action = action
        self.cycle_time = cycle_time
        self.start_time = start_time

        self.name = thread_name
        self.silent = silent
        self.stop = threading.Event()
        self.force = False
        self.enable = False

    def time_left(self):
        """
        Check how long we have until we run again.

        :return: timedelta
        """
        if self.isAlive():
            if self.start_time is None:
                return self.cycle_time - (datetime.datetime.now() - self.lastRun)
            else:
                time_now = datetime.datetime.now()
                start_time_today = datetime.datetime.combine(time_now.date(), self.start_time)
                start_time_tomorrow = datetime.datetime.combine(time_now.date(), self.start_time) + datetime.timedelta(days=1)
                if time_now.hour >= self.start_time.hour:
                    return start_time_tomorrow - time_now
                elif time_now.hour < self.start_time.hour:
                    return start_time_today - time_now
        else:
            return datetime.timedelta(seconds=0)

    def force_run(self):
        """

        :return:
        """
        if not self.action.am_active:
            self.force = True
            return True
        return False

    def run(self):
        """Run the thread."""
        try:
            while not self.stop.is_set():
                if self.enable:
                    current_time = datetime.datetime.now()
                    should_run = False
                    # Is self.force enable
                    if self.force:
                        should_run = True
                    # check if interval has passed
                    elif current_time - self.lastRun >= self.cycle_time:
                        # check if wanting to start around certain time taking interval into account
                        if self.start_time is not None:
                            hour_diff = current_time.time().hour - self.start_time.hour
                            if not hour_diff < 0 and hour_diff < self.cycle_time.seconds / 3600:
                                should_run = True
                            else:
                                # set lastRun to only check start_time after another cycle_time
                                self.lastRun = current_time
                        else:
                            should_run = True

                    if should_run:
                        self.lastRun = current_time
                        if not self.silent:
                            log.debug(u'Starting new thread: {name}', {'name': self.name})
                        self.action.run(self.force)

                    if self.force:
                        self.force = False

                time.sleep(1)
            # exiting thread
            self.stop.clear()
        except Exception as e:
            exception_handler.handle(e)
