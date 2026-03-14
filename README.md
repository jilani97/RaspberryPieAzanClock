# RaspberryPieAzanClock

This repository contains a simple prayer clock script intended to run unattended on a small Linux device such as a DietPi-based RockPi 4SE.

## DietPi systemd setup

The repo includes a ready-to-edit service file at [systemd/azan-clock.service](systemd/azan-clock.service).

Recommended install layout on the device:

1. Copy the repository to `/opt/azan-clock`.
2. Install runtime packages:

```bash
sudo apt update
sudo apt install -y python3 python3-pip mpg123
python3 -m pip install --break-system-packages requests tabulate
```

3. Copy the service file into systemd:

```bash
sudo cp /opt/azan-clock/systemd/azan-clock.service /etc/systemd/system/azan-clock.service
```

4. Edit the service file if needed:
	Change `User`, `WorkingDirectory`, `ExecStart`, and `Environment` values to match your device.

5. Reload systemd and enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now azan-clock.service
```

6. Check logs:

```bash
sudo systemctl status azan-clock.service
journalctl -u azan-clock.service -f
```

## Notes

- The service waits for network availability before starting, because prayer times are fetched from the API.
- Audio playback uses `mpg123`, so the device must have a working audio output path.
- The current service file runs [wimPrayerTimesV2.py](wimPrayerTimesV2.py).