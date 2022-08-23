#!/usr/bin/env python3
"""
Program written to create an object in the minidaq file such that data can easily be taken from the oscilloscope by simply calling a method on that object.
Note that it is designed to be initialised outside a loop, which connects it to the scope, and then on each iteration, when data is taken, getData() is called, returning the waveforms. 
The settings initially set in the __init__ method are specific to our current set-up and will need to be modified if you're doing things differently.
Our set-up had the two scintillators feeding to channel 1 and 2 of the scope, and then going to the TRD box discriminators. The pre-trigger from the TRD box then came back to channel 3 of the scope. Channel 4 was not used but is set to display anyway for generality.
The details of what these commands do can be found in the Programming Manual in the downloads section of https://www.gwinstek.com/en-global/products/detail/GDS-1000B.
"""

import oscilloscopeRead.dso1kb as dso1kb
import numpy as np
import matplotlib.pyplot as plt
import os
import re

class Reader:
    """
    Opens the connection to the oscilloscope. This can take a few seconds as it needs to clear all the scope output.

    Parameters
    ----------
    interface : str
        The device name in the system. This is usually 'ttyACM1' or something similar. The actual value can be found by running
        $ dmesg 
        after plugging the scope into a USB port and looking for the entry with "Product: IDS-1074B". It should show the device name in the line that reads
        "cdc_acm 3-8:2.0: {name}: USB ACM device"

    """
    def __init__(self, interface):
        self.dso = dso1kb.Dso(f'/dev/{interface}')
        # Sets the scope to the right settings 
        # self.dso.write(':CHAN1:DISP ON\n')
        # self.dso.write(':CHAN2:DISP ON\n')
        # self.dso.write(':CHAN3:DISP ON\n')
        # self.dso.write(':CHAN4:DISP ON\n')
        # self.dso.write(':CHAN1:SCAL 2E-1\n')
        # self.dso.write(':CHAN2:SCAL 2E-1\n')
        # self.dso.write(':CHAN3:SCAL 2E0\n')
        # self.dso.write(':CHAN4:SCAL 2E-1\n')
        # self.dso.write(':CHAN4:POS 6E0\n')
        # self.dso.write(':TRIG:SOUR CH3\n')
        # self.dso.write(':TRIG:LEV 1.2E\n')
        # self.dso.write(':TRIG:EDG:SLOP RIS\n')
        # self.dso.write(':TRIG:MOD NORM\n')
        # self.dso.write(':ACQ:RECO 1E3\n')
        # self.dso.write(':TIM:POS 0\n')
        # self.dso.write(':TIM:SCAL 200E-9\n')
        # self.dso.readlines()

    def getData(self, channels=[1,2,3], save_png=False):
        """
        Gets the data from the number of channels specified, converts to a waveform, and outputs a single array containing all the channels.

        Parameters
        ----------
        channels : list
            List of the channels that data will be taken from. Entries need to be ints.
        
        save_png : bool, default=False
            If set to true, this will save a plot of the waveforms saved to the screenshots folder. This is meant to be used simply for debugging purposes, not actual data analysis
        
        Returns
        -------
        waveforms : list
            List of data from each channel in voltage, with each data point separated by 4 ns
        """
        # Gets the raw data for each channel specified and saves it to a variable in the self.dso object. header_on is set to True as data from the header is needed when converting from hex to voltage values
        for i in channels:
            self.dso.getRawData(True, i)

        waveforms = []

        # The convertWaveForm function takes the raw data from the dso object, formats it as a list of floats, and then returns that list.
        for i in channels:
            waveforms.append(self.dso.convertWaveform(i, 1))
        
        # Resets the ch_list variable in the self.dso object. Without resetting it will only take 4 waveforms and then break.
        self.dso.resetChList()

        if save_png:
            t = np.arange(0,self.dso.points_num)
            for c in channels:
                plt.plot(t, waveforms[c-1])
            
            plt.savefig('oscilloscopeRead/screenshots/testplot.png')
                
        return np.array(waveforms)

    def takeScreenshot(self):
        self.dso.write(':DISP:OUTP?\n')
        self.dso.getBlockData()
        self.dso.ImageDecode(1)

        plt.imshow(self.dso.im)
        saveName = str(input('Enter the name the screenshot will be saved under: '))
        # requires a screenshots folder in the outer directory
        plt.savefig(f'oscilloscopeRead/screenshots/{saveName}.png')


def getInterfaceName():
    interfaceName = re.findall("ttyACM.{1}", os.popen("dmesg | grep ttyACM").read().split('\n')[-2])[0]

    return interfaceName
# if __name__ == "__main__":
#     devstr = str(input('Enter the device name: '))
#     scope = reader(devstr)
#     scope.takeScreenshot()
