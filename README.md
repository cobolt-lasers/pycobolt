# pycobolt

## Official python package for Cobolt Lasers
This is a package to facilitate system integration of Cobolt Lasers in Python. Connect to your Cobolt Laser using either the serial number or COM-port of the laser. 

## Dependencies
[Setuptools](https://pypi.org/project/setuptools/) used for build process.

The package requires [Pyserial](https://pypi.org/project/pyserial/) and Python 3.

## Build and Installation
```
python -m build
```
resulting build is added to ``` ./dist/pycobolt-[version].[tar.gz/whl]```.

Installation in a project with pip, use pycobolt directory path.
```
python -m pip install ~/pycobolt/
```

## Usage
```python
import pycobolt

laser = pycobolt.CoboltLaser() # Creates a new Cobolt Laser object.
```