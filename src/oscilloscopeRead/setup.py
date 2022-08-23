from setuptools import setup, find_packages

setup(
    name='oscilloscopeRead',
    version='0.1.0',
    packages=find_packages(include=['dso1kb.py', 'gw_com_1kb.py', 'gw_lan.py', 'scopeRead.py']),
    install_requires=[
        'matplotlib',
        'numpy',
        'PyQt5',
        'Pillow',
        'PySerial'
    ]
)