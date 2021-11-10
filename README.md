# Auto FT8

AutoFT8 is an experimental project for ham radio operators.

This program automatically controls WSJT-X to optimize contacts' chances during a contest or DX (make as many QSO as possible).

After a receive sequence, the program calculates, using the distance, SNR[^1], and azimuth has the most chances of completing the QSO.



[^1] Signal to Noise Ratio


## Auto FT8 JSON Configuration

- "mongo_server": IP address or hostname of the mongodb database.  
Type: string, Default: "localhost"

- "bind_address" is the ipaddress of the sequencer.  
Type: string, Default: "127.0.0.1"

- "wsjt_port": is the UDP communication port port between the sequenser and WSJT-X.  
Type: integer, Default: 2238

- "monitor_port": is the UDP communication port between the sequenser and ftconsole.  
This port is only for AutoFT internal use. Do not set that port in WSJT-X configuration.  
Type: integer, Default: 2240

- "call": Operator call sign.  
This field is mandatory and shoule be set by the operator.  
Type: string, Default: "N0CALL"

- "location": Operator location. This field is used to calculate the distance and azimuth between your station and the calling station.  
This field should be set by the operator.  
Type: string, Default: "CM87vl"
