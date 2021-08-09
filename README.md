# pycobolt
## Official python package for Cobolt Lasers
This is a package to facilitate system integration of Cobolt Lasers in Python. Connect to your Cobolt Laser using either the serial number or COM-port of the laser. 

This package is under development and is not officially released yet. Feel free to use, we will work to solve any issues in a swift manner.

[Setuptools](https://pypi.org/project/setuptools/) used for build process.



## Build and Installation
Install from main development branch
```
python -m pip install git+https://github.com/cobolt-lasers/pycobolt.git
```

## Usage
```python
import pycobolt

laser = pycobolt.CoboltLaser() # Creates a new Cobolt Laser object.
```