import re
import time
import subprocess
import os
import stat
import config.config as conf
from common import get_config_option

def num_cpus():
    '''Return the number of CPUs in the system.'''

    lnx_re = re.compile(r'^(processor|online)')
    cpus = 0

    with open('/proc/cpuinfo', 'r') as f:
        for line in f:
            if lnx_re.match(line):
                cpus += 1
    return cpus

def ft_freq():
    '''The frequency (in MHz) of the clock used by feather trace.'''
    if get_config_option('CPU_V7') == 'y':
        # Arm V7s use a millisecond timer
        freq = 1000.0
    elif get_config_option('X86') == 'y':
        # X86 timer is equal to processor clock
        reg = re.compile(r'^cpu MHz\s*:\s*(?P<FREQ>\d+)', re.M)
        with open('/proc/cpuinfo', 'r') as f:
            data = f.read()

        match = re.search(reg, data)
        if not match:
            raise Exception("Cannot parse CPU frequency from x86 CPU!")
        freq = int(match.group('FREQ'))
    else:
        # You're on your own
        freq = 0
    return freq

def switch_scheduler(switch_to_in):
    '''Switch the scheduler to whatever is passed in.

    This methods sleeps for two seconds to give Linux the chance to execute
    schedule switching code. Raises an exception if the switch does not work.

    '''

    switch_to = str(switch_to_in).strip()

    with open('/proc/litmus/active_plugin', 'w') as active_plugin:
        subprocess.Popen(["echo", switch_to], stdout=active_plugin)

    # it takes a bit to do the switch, sleep an arbitrary amount of time
    time.sleep(2)

    with open('/proc/litmus/active_plugin', 'r') as active_plugin:
        cur_plugin = active_plugin.read().strip()

    if switch_to != cur_plugin:
        raise Exception("Could not switch to plugin: %s" % switch_to)

def uname_matches(reg):
    data = subprocess.check_output(["uname", "-r"])
    return bool( re.match(reg, data) )

def is_executable(fname):
    '''Return whether the file passed in is executable'''
    mode = os.stat(fname)[stat.ST_MODE]
    return mode & stat.S_IXUSR and mode & stat.S_IRUSR

def is_device(dev):
    if not os.path.exists(dev):
        return False
    mode = os.stat(dev)[stat.ST_MODE]
    return not (not mode & stat.S_IFCHR)

def waiting_tasks():
    reg = re.compile(r'^ready.*(?P<READY>\d+)$', re.M)
    with open('/proc/litmus/stats', 'r') as f:
        data = f.read()

    # Ignore if no tasks are waiting for release
    match = re.search(reg, data)
    ready = match.group("READY")

    return 0 if not ready else int(ready)

def release_tasks():

    try:
        data = subprocess.check_output([conf.BINS['release']])
    except subprocess.CalledProcessError:
        raise Exception('Something went wrong in release_ts')

    released = re.findall(r"([0-9]+) real-time", data)[0]

    return int(released)
