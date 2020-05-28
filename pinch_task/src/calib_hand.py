
import struct
import numpy as np
from scipy.io import loadmat
import hid
from toon.input.base_input import BaseInput
from ctypes import c_double, c_uint


class Hand(BaseInput):
    """Hand Articulation Neuro-Training Device (HAND)."""

    @staticmethod
    def samp_freq(**kwargs):
        return kwargs.get('sampling_frequency', 1000)

    @staticmethod
    def data_shapes(**kwargs):
        return [[15]]

    @staticmethod
    def data_types(**kwargs):
        return [c_double]

    def __init__(self, calibration_files, **kwargs):
        super(Hand, self).__init__(**kwargs)
        self._sqrt2 = np.sqrt(2)
        self._device = None
        self._data_buffer = np.full(15, np.nan)  # forces (~-1, 1??)
        self._calib_buffer = np.full(15, np.nan)
        self.calib_matrices = []
        for i in calibration_files:
            self.calib_matrices.append(loadmat(i)['C'])

    def __enter__(self):
        self._device = hid.device()
        dev_path = next((dev for dev in hid.enumerate()
                         if dev['vendor_id'] == 0x16c0 and dev['interface_number'] == 0), None)['path']
        self._device.open_path(dev_path)
        return self

    def __exit__(self, *args):
        self._device.close()

    def read(self):
        data = self._device.read(46)
        time = self.clock()
        if data:
            data = struct.unpack('>Lh' + 'H'*20, bytearray(data))  # Timestamp, deviation, and 20 unsigned ints
            data = np.array(data, dtype='uint')
            data = data.astype(c_double)
            data[0] /= 1000.0
            data[2:] /= 65535.0
            self._data_buffer[0::3] = (data[2::4] - data[3::4])/self._sqrt2  # x
            self._data_buffer[1::3] = (data[2::4] + data[3::4])/self._sqrt2  # y
            self._data_buffer[2::3] = data[4::4] + data[5::4]  # z
            # flip x and z axes
            self._data_buffer[0::3] *= -1
            self._data_buffer[2::3] *= -1 # add gain on z axis
            # apply calibration
            n = 0
            # for each finger, apply calibration
            for i in self.calib_matrices:
                self._calib_buffer[0+n:3+n] = np.dot(i, self._data_buffer[0+n:3+n])
                n += 3
            return (time, self._calib_buffer)
