# -*- coding: utf-8 -*-
"""
Module name: dso1kb

Copyright:
----------------------------------------------------------------------
dso1kb is Copyright (c) 2014 Good Will Instrument Co., Ltd All Rights Reserved.

This program is free software; you can redistribute it and/or modify it under the terms 
of the GNU Lesser General Public License as published by the Free Software Foundation; 
either version 2.1 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; 
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
See the GNU Lesser General Public License for more details.

You can receive a copy of the GNU Lesser General Public License from 
http://www.gnu.org/

Note:
dso1kb uses third party software which is copyrighted by its respective copyright holder. 
For details see the copyright notice of the individual package.

----------------------------------------------------------------------
Description:
dso1kb is a python driver module used to get waveform and image from DSO.

Module imported:
  1. PIL 1.1.7
  2. Numpy 1.8.0

Version: 1.03

Created on JUL 12 2018 by Kevin Meng

Adapted for python3 in 2019 by Tom Dietel

Modified on APR 01 2020 by Nina Nathanson

Modified again in OCT 2021 by Miles Kidson
"""
"""
Some notes from Miles Kidson:
This program was originally written for python2 and that can by found at https://github.com/OpenWave-GW/OpenWave-1KB. This is an adapted version of that in order to work with the Transmission Radiation Detector (TRD) in the UCT Physics department. 

At some point, this became unusable for the application as it was not interpreting the data correctly (in the getRawData function) but some fixes were made that aren't quite in the style of the original program. These work for us but there's no saying whether they will work for you as they do things a bit differently to what was intended.

I've tried to make it work as generally as possible, but it could be that it only works for our specific oscilloscope, which is model IDS-1074B. Best of luck trying to understand this if it breaks, but I hope for your sake that it just works.

An important note is that if you are passing any commands to the oscilloscope using self.write(), you need to put a line break at the end of it, like this

self.write('COMMAND\n')

These commands can be found at https://www.gwinstek.com/en-global/products/downloadSeriesDownNew/1700/130

P.S. any comments with a double # are from me trying to explain things
"""
from oscilloscopeRead.gw_com_1kb import com
from oscilloscopeRead.gw_lan import lan
from PIL import Image
from struct import unpack
import struct
import numpy as np
import io, os, sys, time, platform, re

__version__ = "1.01" #dso1kb module's version.

sModelList = [['GDS-1072B','DCS-1072B','IDS-1072B','GDS-71072B','GDS-1072R','DSO-1072D',
             'GDS-1102B','DCS-1102B','IDS-1102B','GDS-71102B','GDS-1102R','DSO-1102D'],
            ['GDS-1054B','DCS-1054B','IDS-1054B','GDS-71054B','GDS-1054R',
             'GDS-1074B','DCS-1074B','IDS-1074B','GDS-71074B','GDS-1074R','DSO-1072D',
             'GDS-1104B','DCS-1104B','IDS-1104B','GDS-71104B','GDS-1104R','DSO-1102D']]

def generate_lut():
    global lu_table
    num = 65536
    lu_table = []
    for i in range(num):
        pixel888 = [0]*3
        pixel888[0] = (i>>8)&0xf8
        pixel888[1] = (i>>3)&0xfc
        pixel888[2] = (i<<3)&0xf8
        lu_table.append(pixel888)

class Dso:
    def __init__(self, interface):
        if (os.name == 'posix'): #unix
            if (os.uname()[1] == 'raspberrypi'):
                self.osname = 'pi'
            else:
                self.osname = 'unix'
        else:
            if (platform.uname()[2] == 'XP'):
                self.osname = 'win'
            else:
                os_ver = int(platform.uname()[2])
                #print 'os_ver=', os_ver
                #if(os_ver >= 10):
                if(os_ver >= 8):  #You might get wrong OS version here(when OpenWave-2KE.exe is running), especially for Win 10.
                    self.osname = 'win10'
                else:
                    self.osname = 'win'
        if (interface != ''):
            print(interface)
            self.connect(interface)
        else:
            self.chnum = 4
            self.connection_status = 0
        global inBuffer
        self.ver = __version__ #Driver version.
        self.iWave = [[], [], [], []]
        self.vdiv = [[], [], [], []]
        self.vunit = [[], [], [], []]
        self.dt = [[], [], [], []]
        self.vpos = [[], [], [], []]
        self.hpos = [[], [], [], []]
        self.ch_list = []
        self.info = [[], [], [], []]
        generate_lut()
    
    def connect(self, dev):
        if (dev.count('.') == 3 and dev.count(':') == 1): # Checks if dev is an ip address or not
            try:
                self.IO = lan(dev)
            except:
                print('Open LAN port failed!')
                return
        
        elif ('/dev/ttyACM' in dev) or ('COM' in dev) or ('/dev/cu.' in dev): # Checks if dev is a COM port (USB)
            try:
                print(f'Opening serial port {dev}')
                self.IO = com(dev)
            except:
                print('Open COM port failed!')
                return
            self.IO.clearBuf()
        else:
            print(f'ERROR: unknown device: {dev}')
            return
        
        self.write = self.IO.write
        self.read = self.IO.read
        self.readBytes = self.IO.readBytes
        self.closeIO = self.IO.closeIO
        self.readlines = self.IO.readlines
        self.clearBuf = self.IO.clearBuf
        self.clearBuf()    # Clears the buffer to avoid spillage from earlier sessions
        self.write('*IDN?\n')
        model_name = self.read().decode().split(',')[1]
        print(f'{model_name} connected to {dev} successfully!')
        if (self.osname=='win10') and ('COM' in dev):
            self.write(':USBDelay ON\n')  #Prevent data loss on Win 10.
            print ('Send :USBDelay ON')
        if (model_name in sModelList[0]):
            self.chnum = 2   #Got a 2 channel DSO.
            self.connection_status = 1

        elif(model_name in sModelList[1]):
            self.chnum = 4   #Got a 4 channel DSO.
            self.connection_status = 1
        else:
            self.chnum = 4
            self.connection_status = 0
            print ('Device not found!')
            return

        if not os.path.exists('port.config'):
            f = open('port.config', 'w')
            f.write(dev)
            f.close()
        
    def getBlockData(self): # Gets image data
        global inBuffer
        #print("TEST",self.readBytes(20518))
        #inBuffer=self.readBytes(10)
        inBuffer = self.read()
        length = len(inBuffer)
        self.headerlen = 2 + int(inBuffer[1:2].decode())
        pkg_length = int(inBuffer[2:self.headerlen]) + self.headerlen + 1 #Block #48000[..8000bytes raw data...]<LF>
        print ('Data transferring...')

        pkg_length = pkg_length-length
        while True:
            print(f'{pkg_length}\r')
            if (pkg_length == 0):
                break
            else:
                if (pkg_length > 100000):
                    length = 100000
                else:
                    length = pkg_length
                try:
                    buf = self.readBytes(length)
                except:
                    print('KeyboardInterrupt!')
                    self.clrBuf()
                    self.closeIO()
                    sys.exit(0)
                num = len(buf)
                inBuffer += buf
                pkg_length = pkg_length-num

    def ImageDecode(self, type):
        if (type):  # 1 for RLE decode, 0 for PNG decode.
            raw_data=[]
            # Convert 8 bits array to 16 bits array.
            data = unpack(f'<{len(inBuffer[self.headerlen:-1])//2}H', inBuffer[self.headerlen:-1])
            l = len(data)
            if( l%2 != 0): # Ignore reserved data.
                l -= 1
            package_length = len(data)
            index = 0
            bmp_size = 0
            while True:
                length = data[index]
                value = data[index+1]
                index += 2
                bmp_size += length
                buf = [ value for x in range(0,length)]
                raw_data += buf
                if(index >= l):
                    break
            width = 800
            height = 480
            # Convert from rgb565 into rgb888
            index = 0
            rgb_buf = []
            num = width*height
            for index in range(num):
                rgb_buf += lu_table[raw_data[index]]
            img_buf = struct.pack("1152000B", *rgb_buf)
            self.im = Image.frombuffer('RGB',(width,height), img_buf, 'raw', 'RGB',0,1)
        else:  #0 for PNG decode.
            self.im = Image.open(io.BytesIO(inBuffer[self.headerlen:-1]))
            print ('PngDecode()')
        if(self.osname=='pi'):
            self.im = self.im.transpose(Image.FLIP_TOP_BOTTOM) #For raspberry pi only.

    def getRawData(self, header_on, ch): # Gets raw data for waveform on channel ch
        global inBuffer
        self.dataMode=[]
        print(f'Waiting CH{ch} data... ')
        if (header_on==True):
            self.write(':HEAD ON\n')
        else:
            self.write(':HEAD OFF\n')
        
        if (self.checkAcqState(ch)==-1):
            return
        self.write(f':ACQ{ch}:MEM?\n') # Requests the raw data from the scope
        index = len(self.ch_list)
        if (header_on == True):
            if (index == 0):
                self.info=[[], [], [], []]

            ## Here is where we deviated from the original method. It originally processed it all at once and then called getBlockData and did some things, but that just didn't seem to work for us. I suspect it's something to do with the change from python2 to 3. This should work, but there are still some parts that I don't understand. Best to not touch it :)

            # rDat = self.read()
            # bArr = bytearray(rDat)
            # bArrSplit = bArr.split(b'\n')
            # header = bArrSplit[0]
            # dataS = bArrSplit[1]

            self.info[index] = self.read().decode('ascii').split(';')
            dataS = self.read()
            num = len(self.info[index])
            # print(f'Number of elements in the header: {num}')

            self.info[index][num-1] = self.info[index][num-2]
            self.info[index][num-2] = 'Mode,Fast'
            sCh = [s for s in self.info[index] if 'Source' in s]
            self.ch_list.append(sCh[0].split(',')[1])
            sDt = [s for s in self.info[index] if 'Sampling Period' in s]
            self.dt[index] = float(sDt[0].split(',')[1])
            sDv = [s for s in self.info[index] if 'Vertical Scale' in s]
            self.vdiv[index] = float(sDv[0].split(',')[1])
            sVpos = [s for s in self.info[index] if 'Vertical Position' in s]
            self.vpos[index] = float(sVpos[0].split(',')[1])
            sHpos = [s for s in self.info[index] if 'Horizontal Position' in s]
            self.hpos[index] = float(sHpos[0].split(',')[1])
            sVunit = [s for s in self.info[index] if 'Vertical Units' in s]
            self.vunit[index] = sVunit[0].split(',')[1]
        
        else:
            dataS = self.read()
        
        ## Note the various uses of a *2 or a /2 here, it really is weird when dealing with byte arrays filled with hex values. the lengths of arrays are really weird but I think this works
        dataInfoHeader = dataS[:2]
        dataInfo = int(dataInfoHeader.decode()[1])
        pointsByte = dataS[2:2+dataInfo]
        self.points_num = int(int(pointsByte.decode())/2)
        dataS = dataS[2+dataInfo:-1] # Needs the -1 at the end to exclude the \n.

        try:
            self.iWave[index] = unpack(f'>{self.points_num}h', dataS)
        except:
            """
            This is an area that definitely can be improved. I ran into the issue of the scope occasionally outputting bad data that is split up by \n, so the read() function only gets part of it. I think there must be some way to get each section of the data and put it all together, but it wasn't working for me. It currently just gives zeros, so it can be easily ignored in analysis, but fixing this would be a great help.
            """
            # print('Buffer wrong size, setting all to zero')
            self.clearBuf()
            tempArr = bytearray(int(self.points_num*2))
            self.iWave[index] = unpack(f'>{self.points_num}h', tempArr)

        return index
    
    def checkAcqState(self,  ch):
        str_stat = f':ACQ{ch}:STAT?\n'
        loop_cnt = 0
        max_cnt = 0
        while True: # Checks if acquisition is ready or not. i.e. if there is a signal on that channel
            self.write(str_stat)
            state=self.read().decode()
            if(state[0] == '1'):
                break
            time.sleep(0.1)
            loop_cnt +=1
            if(loop_cnt >= 50):
                print('Please check signal!')
                loop_cnt=0
                max_cnt+=1
                if(max_cnt==5):
                    return -1
        return 0
    
    def convertWaveform(self, ch, factor):
        # print(self.vdiv)
        chPos = ch-1
        dv = self.vdiv[chPos]/25
        # print('DV', dv)
        if (factor == 1):
            num = self.points_num
            fWave = [0]*num
            for x in range(num): # Converts 16 bits signed to floating point number.
                fWave[x] = float(self.iWave[chPos][x])*dv 

            # f = open("dataPlottableCh%s" % ch,'w')
            # f.write(str(fWave))
            # f.close()

        else: #Reduced to helf points.
            num = self.points_num/factor
            fWave = [0]*num
            for x in range(num): # Converts 16 bits signed to floating point number.
                i = factor*x
                fWave[x] = float(self.iWave[chPos][i])*dv
        return fWave

    def readRawDataFile(self,  fileName): ## Fairly redundant for our usage. I really don't know how it works so good luck if you decide to use it.
        # Checks file format (csv or lsf)
        self.info = [[], [], [], []]
        if (fileName.lower().endswith('.csv')):
            self.dataType = 'csv'
        elif (fileName.lower().endswith('.lsf')):
            self.dataType = 'lsf'
        else:
            return -1
        f = open(fileName, 'rb')
        info = []
        #Read file header.
        if (self.dataType == 'csv'):
            for x in range(25):
                info.append(f.readline().split(',\r\n')[0])
            if (info[0].split(',')[1] != '1.0B'): #Check format version
                f.close()
                return -1
            count = info[5].count('CH')  #Check channel number in file.
            wave = f.read().decode().splitlines() #Read raw data from file.
            self.points_num = len(wave)
            if (info[23].split(',')[1]=='Fast'):
                self.dataMode = 'Fast'
            else:
                self.dataMode = 'Detail'
        else:
            info = f.readline().split(';') #The last item will be '\n'.
            if(info[0].split('Format,')[1] != '1.0B'): #Check format version
                f.close()
                return -1
            if(f.read(1) != '#'):
                print('Format error!')
                sys.exit(0)
            digit = int(f.read(1))
            num = int(f.read(digit))
            count = 1
            wave = f.read() #Read raw data from file.
            self.points_num = len(wave)/2   #Calculate sample points length.
            self.dataMode = 'Fast'
        f.close()

        print('Plotting waveform...')
        if (count == 1): #1 channel
            self.iWave[0] = [0]*self.points_num
            self.ch_list.append(info[5].split(',')[1])
            self.vunit[0] = info[6].split(',')[1] #Get vertical units.
            self.vdiv[0]  = float(info[12].split(',')[1]) #Get vertical scale. => Voltage for ADC's single step.
            self.vpos[0] = float(info[13].split(',')[1]) #Get vertical position.
            self.hpos[0] = float(info[16].split(',')[1]) #Get horizontal position.
            self.dt[0] = float(info[19].split(',')[1]) #Get sample period.
            dv1 = self.vdiv[0]/25
            vpos = int(self.vpos[0]/dv1)+128
            vpos1 = self.vpos[0]
            num = self.points_num
            if (self.dataType == 'csv'):
                for x in range(25):
                    self.info[0].append(info[x])
                if (self.dataMode == 'Fast'):
                    for x in range(num):
                        value = int(wave[x].split(',')[0])
                        self.iWave[0][x] = value
                else:
                    for x in range(num):
                        value = float(wave[x].split(',')[1])
                        self.iWave[0][x] = int(value/dv1)
            else: #lsf file
                for x in range(23):
                    self.info[0].append(info[x])
                self.info[0].append('Mode,Fast') #Convert info[] to csv compatible format.
                self.info[0].append(info[23])
                self.iWave[0] = np.array(unpack(f'<{len(wave)/2}h', wave)) #!!!!
                for x in range(num): #Convert 16 bits signed number to floating point number.
                    self.iWave[0][x] -= vpos
            del wave
            return 1

        else: #multi channel, csv file only.
            #write waveform's info to self.info[]
            for ch in range(count):
                self.info[ch].append(info[0])
            for x in range(1, 24):
                str = info[x].split(',')
                for ch in range(count):
                    self.info[ch].append(f'{2*ch}, {2*ch+1}')
            str = info[24].split(',')
            for ch in range(count):
                self.info[ch].append(str[2*ch])

            for ch in range(count):
                self.ch_list.append(info[5].split(',')[2*ch+1])
                self.iWave[ch] = [0]*self.points_num
                self.vunit[ch] = info[6].split(',')[2*ch+1] #Get vertical units.
                self.vdiv[ch] = float(info[12].split(',')[2*ch+1]) #Get vertical scale. => Voltage for ADC's single step.
                self.vpos[ch] = float(info[13].split(',')[2*ch+1]) #Get vertical position.
                self.hpos[ch] = float(info[16].split(',')[2*ch+1]) #Get horizontal position.
                self.dt[ch] = float(info[19].split(',')[2*ch+1]) #Get sample period.
            num = self.points_num
            if(self.dataMode == 'Fast'):
                for ch in range(count):
                    self.iWave[ch] = [0]*num
                for i in range(num):
                    str = wave[i].split(',')
                    for ch in range(count):
                        index = 2*ch
                        self.iWave[ch][i] = int(str[index])
            else:
                dv=[]
                for ch in range(count):
                    dv.append(self.vdiv[ch]/25)
                for i in range(num):
                    str = wave[i].split(',')
                    for ch in range(count):
                        index = 2*ch+1
                        value = float(wave[i].split(',')[index])
                        self.iWave[ch][i] = int(value/dv[ch])
            del wave
            return count

    def isChannelOn(self, ch):
        self.write(f':CHAN{ch}:DISP?\n')
        onoff = self.read().decode()
        onoff = onoff[:-1]
        if(onoff == 'ON'):
            return True
        else:
            return False

    def resetChList(self):
        self.ch_list = []
    
    def readlines(self):
        null = self.readlines()


def getInterfaceName():
    interfaceName = re.findall("ttyACM.{1}", os.popen("dmesg | grep ttyACM").read().split('\n')[-2])[0]

    return interfaceName
