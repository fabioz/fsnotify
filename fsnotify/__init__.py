'''
Sample usage to track changes in a thread.

    import threading
    import time
    watcher = fsnotify.Watcher()

    # Configure target values to compute throttling.
    watcher.target_time_for_single_scan = 2.
    watcher.target_time_for_notification = 4.

    watcher.set_tracked_paths(target_big_dir)

    def on_change(change):  # Called from thread
        change_enum, change_path = change
        if change_enum == fsnotify.Change.added:
            print('Added: ', change_path)

        ...

    def start_watching():
        for change in watcher.iter_changes():
            on_change(change)

    t = threading.Thread(target=start_watching)
    t.daemon = True
    t.start()

    try:
        ...
    finally:
        watcher.dispose()

'''
import threading
import sys
try:
    from os import scandir
except:
    try:
        # Search an installed version (which may have speedups).
        from scandir import scandir
    except:
        # If all fails, use our vendored version (which won't have speedups).
        from .scandir_vendored import scandir

try:
    from enum import IntEnum
except:

    class IntEnum(object):
        pass

from collections import deque

import time

__author__ = 'Fabio Zadrozny'
__email__ = 'fabiofz@gmail.com'
__version__ = '0.1.0.dev0'

PRINT_SINGLE_POLL_TIME = False


class Change(IntEnum):
    added = 1
    modified = 2
    deleted = 3


class PathWatcher(object):

    def __init__(self, root_path, should_watch_dir, should_watch_file, sleep_time=.1):
        self._should_watch_dir = should_watch_dir
        self._should_watch_file = should_watch_file

        self._file_to_mtime = {}
        self._root_path = root_path

        # Initial sleep value for throttling, it'll be auto-updated based on the
        # Watcher.target_time_for_single_scan.
        self.sleep_time = sleep_time

        self.sleep_at_elapsed = 1. / 30.

        # When created, do the initial snapshot right away!
        self._check(lambda _change: None)

    def __eq__(self, o):
        if isinstance(o, PathWatcher):
            return self._root_path == o._root_path

        return False

    def __ne__(self, o):
        return not self == o

    def __hash__(self):
        return hash(self._root_path)

    def _check(self, append_change):
        last_sleep_time = time.time()

        stack = deque()
        stack.append(str(self._root_path))
        old_file_to_mtime = self._file_to_mtime
        self._file_to_mtime = new_files = {}

        count = 0

        while stack:
            dir_path = stack.pop()
            if isinstance(dir_path, bytes):
                dir_path = dir_path.decode(sys.getfilesystemencoding())

            try:
                for entry in scandir(dir_path):
                    count += 1

                    # Throttle if needed inside the loop
                    # to avoid consuming too much CPU.
                    if count % 300 == 0:
                        if self.sleep_time > 0:
                            t = time.time()
                            diff = t - last_sleep_time
                            if diff > self.sleep_at_elapsed:
                                time.sleep(self.sleep_time)
                                last_sleep_time = time.time()

                    if entry.is_dir():
                        if self._should_watch_dir(entry.path):
                            stack.append(entry.path)

                    elif self._should_watch_file(entry.name):
                        stat = entry.stat()
                        mtime = (stat.st_mtime_ns, stat.st_size)
                        path = entry.path
                        new_files[path] = mtime

                        old_mtime = old_file_to_mtime.pop(path, None)
                        if not old_mtime:
                            append_change((Change.added, path))
                        elif old_mtime != mtime:
                            append_change((Change.modified, path))
            except OSError:
                pass  # Directory was removed in the meanwhile.

        deleted = list(old_file_to_mtime)
        if deleted:
            for entry in deleted:
                append_change((Change.deleted, entry))

        self._file_to_mtime = new_files


class Watcher(object):

    # By default (if should_watch_dir is not specified), these will be the
    # ignored directories.
    ignored_dirs = {u'.git', u'__pycache__', u'.idea', u'node_modules', u'.metadata'}

    # By default (if should_watch_file is not specified), these will be the
    # accepted files.
    accepted_file_extensions = ()

    # Set to the target value for doing full scan of all files.
    # Lower values will consume more CPU.
    # Set to 0.0 to have no sleeps (which will result in a higher cpu load).
    target_time_for_single_scan = 2.0

    # Set the target value from the start of one scan to the start of another scan.
    # Lower values will consume more CPU.
    # Set to 0.0 to have a new scan start right away without any sleeps.
    target_time_for_notification = 4.0

    # Set to True to print the time for a single poll through all the paths.
    print_poll_time = False

    def __init__(self, should_watch_dir=None, should_watch_file=None):
        self._path_watchers = set()
        self._disposed = threading.Event()

        if should_watch_dir is None:
            should_watch_dir = lambda path_name: path_name not in self.ignored_dirs
        if should_watch_file is None:
            if self.accepted_file_extensions:
                should_watch_file = lambda path_name: \
                    path_name.endswith(self.accepted_file_extensions)
            else:  # No filters set.
                should_watch_file = lambda _: True
        self._should_watch_file = should_watch_file
        self._should_watch_dir = should_watch_dir

    def dispose(self):
        self._disposed.set()

    @property
    def path_watchers(self):
        return tuple(self._path_watchers)

    def set_tracked_paths(self, paths):
        """
        Note: always resets all path trackers.
        """
        if not isinstance(paths, (list, tuple, set)):
            paths = (paths,)
        path_watchers = set()
        for path in paths:
            sleep_time = 0.1
            if self.target_time_for_single_scan <= 0.0:
                sleep_time = 0.0
            path_watcher = PathWatcher(
                path, self._should_watch_dir, self._should_watch_file, sleep_time=sleep_time)

            path_watchers.add(path_watcher)
        self._path_watchers = path_watchers

    def iter_changes(self):
        '''
        Continuously provides changes (until dispose() is called).

        :rtype: Iterable[Tuple[Change, str]]
        '''
        while not self._disposed.is_set():
            initial_time = time.time()

            for path_watcher in self._path_watchers:
                changes = []
                path_watcher._check(changes.append)
                for change in changes:
                    yield change

            actual_time = (time.time() - initial_time)
            if self.print_poll_time:
                print('--- Total time: %.3fs' % actual_time)

            if actual_time > 0:
                if self.target_time_for_single_scan <= 0.0:
                    for path_watcher in self._path_watchers:
                        path_watcher.sleep_time = 0.0
                else:
                    perc = self.target_time_for_single_scan / actual_time

                    # Prevent from changing the values too much (go slowly into the right
                    # direction).
                    # (to prevent from cases where the user puts the machine on sleep and
                    # values become too skewed).
                    if perc > 2.:
                        perc = 2.
                    elif perc < 0.5:
                        perc = 0.5

                    for path_watcher in self._path_watchers:
                        new_sleep_time = path_watcher.sleep_time * perc

                        # Prevent from changing the values too much (go slowly into the right
                        # direction).
                        # (to prevent from cases where the user puts the machine on sleep and
                        # values become too skewed).
                        diff_sleep_time = new_sleep_time - path_watcher.sleep_time
                        path_watcher.sleep_time += (diff_sleep_time / (3.0 * len(self._path_watchers)))

                        if actual_time > 0:
                            self._disposed.wait(actual_time)

                        if path_watcher.sleep_time < 0.001:
                            path_watcher.sleep_time = 0.001

            # print('new sleep time: %s' % path_watcher.sleep_time)

            diff = self.target_time_for_notification - actual_time
            if diff > 0.:
                self._disposed.wait(diff)

