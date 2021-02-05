import os
import pytest
from fsnotify import Change
import fsnotify

try:
    TimeoutError
except NameError:
    class TimeoutError(Exception):
        pass

def wait_for_condition(condition, msg=None, timeout=5, sleep=1 / 20.0):
    import time

    curtime = time.time()

    while True:
        if condition():
            break
        if timeout is not None and (time.time() - curtime > timeout):
            error_msg = "Condition not reached in %s seconds" % (timeout,)
            if msg is not None:
                error_msg += "\n"
                if callable(msg):
                    error_msg += msg()
                else:
                    error_msg += str(msg)

            raise TimeoutError(error_msg)
        time.sleep(sleep)


@pytest.fixture
def changes():
    return []


@pytest.fixture
def watcher(tmpdir, changes):
    import threading

    watcher = fsnotify.Watcher()
    
    watcher.target_time_for_single_scan = 0.1
    watcher.target_time_for_notification = 0.1
    watcher.set_tracked_paths(str(tmpdir))

    def start_watching():
        for change in watcher.iter_changes():
            changes.append(change)

    t = threading.Thread(target=start_watching)
    t.start()
    yield watcher

    watcher.dispose()
    t.join()


def test_filtering(tmpdir, watcher, changes):
    for path_watcher in watcher.path_watchers:
        path_watcher._should_watch_file = lambda filename: filename.endswith('.py')

    path_txt = tmpdir.join('my.txt')
    path_txt.write('foo')

    path_py = tmpdir.join('my.py')
    path_py.write('foo')

    wait_for_condition(lambda: len(changes) >= 1)
    assert len(changes) == 1
    assert changes.pop(0) == (Change.added, str(path_py))
    assert not changes

    path_txt.write('something else')
    path_py.write('something else')
    wait_for_condition(lambda: len(changes) >= 1)
    assert changes.pop(0) == (Change.modified, str(path_py))
    assert not changes

    path_txt.remove()
    path_py.remove()
    wait_for_condition(lambda: len(changes) >= 1)
    assert changes.pop(0) == (Change.deleted, str(path_py))
    assert not changes


def test_basic(tmpdir, watcher, changes):
    path = tmpdir.join('my.txt')
    path.write('foo')
    wait_for_condition(lambda: len(changes) >= 1)
    assert changes.pop(0) == (Change.added, str(path))
    assert not changes

    path.write('something else')
    wait_for_condition(lambda: len(changes) >= 1)
    assert changes.pop(0) == (Change.modified, str(path))
    assert not changes

    path.remove()
    wait_for_condition(lambda: len(changes) >= 1)
    assert changes.pop(0) == (Change.deleted, str(path))
    assert not changes

    dirpath = tmpdir.join('dir')
    dirpath.mkdir()
    path = dirpath.join('my.txt')
    path.write('foo')
    wait_for_condition(lambda: len(changes) >= 1)
    assert changes.pop(0) == (Change.added, str(path))
    assert not changes

    path.remove()
    dirpath.remove()

    wait_for_condition(lambda: len(changes) >= 1)
    assert changes.pop(0) == (Change.deleted, str(path))
    assert not changes


def gen_structure(basedir):
    dirs_created = 0
    files_created = 0

    for i in range(100):
        try:
            os.makedirs(basedir)
        except:
            pass

        dpath = os.path.join(basedir, 'mydir_%05d' % (i,))
        try:
            os.makedirs(dpath)
        except:
            pass
        dirs_created += 1
        for j in range(100):
            fpath = os.path.join(dpath, 'myfile_%05d' % (j,))
            with open(str(fpath), 'w') as stream:
                stream.write(str(fpath))
            files_created += 1

    print('Total dirs: %s' % dirs_created)
    print('Total files: %s' % files_created)
    print('Created files at: %s' % (basedir,))


target_big_dir = r'C:\temp\a'


def _test_performance():
    import threading
    import time
    watcher = fsnotify.Watcher()
    watcher.target_time_for_single_scan = 0.
    watcher.target_time_for_notification = 0.
    watcher.print_poll_time = True
    watcher.set_tracked_paths(target_big_dir)
    changes = []

    def start_watching():
        for change in watcher.iter_changes():
            changes.append(change)
            print(change)

    t = threading.Thread(target=start_watching)
    t.start()

    try:
        # Uncomment to generate initial structure.
        # gen_structure(target_big_dir)
        time.sleep(100)
    finally:
        watcher.dispose()
        t.join()



# def _test_watchgod_performance():
#     from watchgod import watch
# 
#     import threading
#     import time
# 
#     def start_watching():
#         from watchgod.watcher import AllWatcher
#         for changes in watch(target_big_dir, watcher_cls=AllWatcher):
#             print(changes)
# 
#     t = threading.Thread(target=start_watching)
#     t.start()
# 
#     try:
#         time.sleep(100)
#     finally:
#         t.join()
