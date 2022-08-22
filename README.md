
PyTRD - Utilities for the ALICE TRD, implemented in Python
==========================================================

This repository contains utilities intended for the ALICE TRD prac at the
University of Cape Town. It is intended as a collection point for all Python
software, from control software for the TRD chamber, a monitoring programme,
raw data reader and in the future also software related to the readout of the oscilloscope and analysis tools.


Installation
------------

This package uses setuptools. For now, I suggest to install it in a virtual environment:
```
python3 -m venv venv
. venv/bin/activate
python -m pip install upgrade pip
python -m pip install -r requirements.txt
python -m install -e .
```

Once installed, activate the environment with `. path/to/pytrd/venv/bin/activate`, add `venv/bin` to the path, or run the commands with the full path `path/to/pytrd/venv/bin/trdmon`.

Usage
-----

This section is work in progress, certainly incomplete and maybe incorrect. Read with caution, and refer to the source if in doubt.

### TRD monitor

This is a basic monitor for DCS services. It is run without any arguments: `trdmon`. Modify the source code to add more services or change the layout.

### Event dump

Parse raw data files in various formats (time frames, the historical o32 format and a new format invented for the ZeroMQ DAQ (partially) contained in this repository). 