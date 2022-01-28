
PyTRD - Utilities for the ALICE TRD, implemented in Python
==========================================================

This repository contains utilities inteded for the ALICE TRD prac at the
University of Cape Town. It is intended as a collection point for all Python
software, from control software for the TRD chamber, a monitoring programme,
raw data reader and in the future also software related to the readout of the oscilloscope and analysis tools.


Installation
------------

This package uses setuptools.
```
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Once installed, add `venv/bin` to the path, or run
```
~/path/to/pydcs/venv/bin/trdmon`
```
