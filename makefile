PYTHON=$(which python3)

install:
	sudo apt install git python3 python3-pip git-core python3-gpiozero
	pip3 install -r requirements.txt

run_pumpman:
	python3 pumpman.py

run_transfer_tank:
	python3 transfer_tank.py

run:
	python3 pumpman.py
	python3 transfer_tank.py
