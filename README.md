# Auto FT8

AutoFT8 is an experimental project for ham radio operators.

This program automatically controls WSJT-X to optimize contacts' chances during a contest or DX (make as many QSO as possible).

After a receive sequence, the program calculates, using the distance, SNR[^1], and azimuth has the most chances of completing the QSO.



## Auto FT8 YAML Configuration

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
