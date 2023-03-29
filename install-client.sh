#!/bin/bash
NAME=fsevents-sync-client

cp -f ./.$NAME.json ~/.$NAME.json
sudo cp -f ./scripts/$NAME.py /usr/local/bin/$NAME.py
sudo sed -i "s/\$USER/$USER/g" /usr/local/bin/$NAME.py
sudo systemctl disable $NAME.service
sudo cp -f ./$NAME.service /etc/systemd/system/$NAME.service
sudo systemctl daemon-reload
sudo systemctl enable $NAME.service
sudo systemctl start $NAME.service
