# Auto FT8
## About
AutoFT8 originated is an experimental project for ham radio operators who want to added autopilot to their FT8 experience. This program automatically controls WSJT-X to optimize contacts' chances during a contest or DX (make as many QSO as possible). After a receive sequence, the program calculates, using the distance, SNR[^1], and azimuth has the most chances of completing the QSO.

#
## Technical Specifications

### Dependencies:
- Python runtime envrionment: Python 3.8 or greater

### Structure of Auto FT8 YAML Configuration
Below is an example on how to setup your configuration file.

```yaml
**mongo_server**: IP address or hostname of the MongoDB database.

    Type: string,
    Default: "localhost"

**bind_address** is the IP address of the sequencer.

    Type: string,
    Default: "127.0.0.1"

**wsjt_port**: is the UDP communication port between the sequencer and WSJT-X.

    Type: integer,
    Default: 2238

**monitor_port**: is the UDP communication port between the sequencer and ftconsole.
This port is only for AutoFT internal use. Do not set that port in WSJT-X configuration.

    Type: integer,
    Default: 2240

**call**: Operator call sign.
This field is mandatory and should be set by the operator.

    Type: string,
    Default: "N0CALL"

**location**: Operator location. This field is used to calculate the distance and azimuth between your station and the calling station.
The operator should set this field.

    Type: string,
    Default: "CM87vl"

**follow_frequency**: Change the transmit frequency to transmit on the same frequency as the caller

    Type: boolean,
    Default: True


[^1]: Signal to Noise Ratio
```
#
## Installation and Usage
There are a few pathways for using AutoFT8, first clone the repository and install dependencies from source. Alternatively, leverage the contained `pyproject.toml` or `Pipfile` to install dependecies and run from a virtual environment.
### Clone from Source
Start by cloning the repo before you begin and place the contents into a place accessible for various OS processes. To obtain clone URL from [HERE](https://github.com/0x9900/AutoFT8):
```sh
git clone <enter git url>
cd autoft8
```
### Setup using Python package management (Pipenv)
For instructions on installation and usage of [Pipenv](https://pipenv.pypa.io/en/latest/install/)

Once the AutoFT8 repository is in an accessible place, run the below command from a commandline interface to setup project dependencies and establish a virtual environment.
```sh
pipenv install
```
Activate the virtual environment and run AutoFT8
```sh
pipenv shell
```

### Setup using Python package management (Poetry)
For instructions on installation and usage of [Poetry](https://python-poetry.org)

Once the AutoFT8 repository is in an accessible place, run the below command from a commandline interface to setup project dependencies and establish a virtual environment. This will setup the project using the supplied .toml file.

```sh
poetry install
```
Activate the virtual environment and run AutoFT8
```sh
poetry shell
```

## Usage
$TODO: Add expected user workflow here.

# Project Roadmap
Build docker file for easy deployment


# References
[WSJT-X Website](https://physics.princeton.edu/pulsar/k1jt/wsjtx.html), Joe Taylor, K1JT

# Authorship
Fred Cirera
