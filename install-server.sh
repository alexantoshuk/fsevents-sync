#!/bin/bash
NAME=fsevents-sync-server
FSEVENTSDIR = /mnt/data/tk/scripts/fsevents

cp -f ./.$NAME.json ~/.$NAME.json
sudo cp -f ./scripts/$NAME.py /usr/local/bin/$NAME.py
sudo systemctl disable $NAME.service
sudo cp -f ./$NAME.service /etc/systemd/system/$NAME.service
sudo sed -i "s/\$USER/$USER/g; s/\$FSEVENTSDIR/$FSEVENTSDIR/g" /etc/systemd/system/$NAME.service
sudo systemctl daemon-reload
sudo systemctl enable $NAME.service
sudo systemctl start $NAME.service
