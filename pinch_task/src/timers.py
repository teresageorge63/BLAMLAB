import time
# Note: depends on python 3.3+ (for perf_counter)
# Note to self: Recheck once we incorporate toon 
# (we'll probably only need CountdownTimer then, toon.input.clock.MonoClock will let us relate device time to local time)
class Timer(object):
    def __init__(self):
        self.ref_time = time.perf_counter()
    def elapsed(self):
        return time.perf_counter() - self.ref_time
    def reset(self):
        self.ref_time = time.perf_counter()

class CountdownTimer(object):
    def __init__(self, ref_time=0):
        self.ref_offset = ref_time
        self.ref_time = self.ref_offset + time.perf_counter()
    def elapsed(self):
        return self.ref_time - time.perf_counter()
    def reset(self, ref_time=None):
        if not ref_time:
            self.ref_time = self.ref_offset + time.perf_counter()
        else:
            self.ref_offset = ref_time
            self.ref_time = self.ref_offset + time.perf_counter()

