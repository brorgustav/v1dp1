sudo apt update -y
sudo apt full-upgrade
sudo apt install python3-pip -y
sudo apt-get install portaudio19-dev -y
sudo apt install pulseaudio-utils
sudo usermod -a -G video bgw
source ./bin/activate
pip3 install sounddevice numpy