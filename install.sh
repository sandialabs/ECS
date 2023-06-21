#!/bin/bash

#update and grab dependancies
sudo apt update
sudo apt install -y python3-pip

pip3 install pillow openpyxl paramiko scp