# Raspberry-Pi-Battery-Power-Monitor

Monitors voltage, current, and power of a battery and if voltage goes below a threshold, shuts down the Raspberry Pi.

```shell
pi@pi3:~ $ 
Broadcast message from root@pi3 (Sat 2022-12-17 15:27:19 CST):

Battery Voltage Low
The system is going down for poweroff at Sat 2022-12-17 15:32:19 CST!
```

Also implements the command `battery` to display current battery stats and cpu temp:

```shell
pi@pi3:~ $ battery
battery voltage = 12.451 volts.  Run time = 0.3071861111111111 hours
battery current = 332.275 mA.  Capacity used = 98.555 mAh
CPU temp = 49.93 deg C.
```

The project uses the INA226 Bi-Directional Current and Power Monitor breakout board, found on Amazon and other places.  The script currently assumes a 3 cell Li-Ion battery so the voltage cutoff is 3.5v per cell , 10.5 volts.  This can be changed in the script `monitor2.py`.

## Installation and Configuration

Edit `/boot/config.txt` to turn on the i2c interface by adding this line:

```shell
dtparam=i2c_arm=on
```





Copy `monitor2.py` and `battery.py` into `usr/local/bin`.  Rename `battery.py` to `battery` to make it an easier command and make both executable:

```shell
mv battery.py battery
chmod +x monitor2.py battery
```

Install the python library to write a systemd service:

```shell
sudo apt install python3-systemd
```

Create a new systemd service:

```shell
cd  /etc/systemd/system
sudo touch battery-monitor.service
```

Then put in the following text into the file

```shell
[Unit]
Description=Battery Monitor Service
After=basic.target
StartLimitIntervalSec=0

[Service]
Type=notify
Restart=always
RestartSec=10
User=pi
ExecStart=/usr/bin/python3 /usr/local/bin/monitor2.py
Environment=PYTHONUNBUFFERED=1
KillMode=mixed

[Install]
WantedBy=default.target
```

Start the service

```shell
sudo systemctl start battery-monitor
```

```shell
sudo systemctl status battery-monitor
```

Enable the service to have it start at boot

```shell
sudo systemctl enable battery-monitor
```

Run the script `battery`

```shell
pi@pi3:~ $ battery
battery voltage = 12.451 volts.  Run time = 0.3071861111111111 hours
battery current = 332.275 mA.  Capacity used = 98.555 mAh
CPU temp = 49.93 deg C.
```


