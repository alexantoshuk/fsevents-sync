#!/bin/bash
cp -f ./.fsevents-sync-server.json ~/.fsevents-sync-server.json
sudo cp -f ./scripts/fsevents-sync-server.py /usr/local/bin/fsevents-sync-server.py
sudo sed -i "s/\$USER/$USER/g" /usr/local/bin/fsevents-sync-server.py
sudo systemctl disable fsevents-sync-server.service
sudo cp -f ./rclone-sync.service /etc/systemd/system/fsevents-sync-server.service
sudo systemctl daemon-reload
sudo systemctl enable fsevents-sync-server.service
sudo systemctl start fsevents-sync-server.service
