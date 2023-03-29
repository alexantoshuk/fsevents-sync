#!/bin/bash
cp -f ./.fsevents-sync-client.json ~/.fsevents-sync-client.json
sudo cp -f ./scripts/fsevents-sync-client.py /usr/local/bin/fsevents-sync-client.py
sudo sed -i "s/\$USER/$USER/g" /usr/local/bin/fsevents-sync-client.py
sudo systemctl disable fsevents-sync-client.service
sudo cp -f ./rclone-sync.service /etc/systemd/system/fsevents-sync-client.service
sudo systemctl daemon-reload
sudo systemctl enable fsevents-sync-client.service
sudo systemctl start fsevents-sync-client.service
