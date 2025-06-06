#/bin/bash
sudo apt update -y
sudo apt install python3-pip -y
sudo apt-get install portaudio19-dev -y
sudo usermod -a -G video bgw
source ./bin/activate
pip3 install sounddevice numpy