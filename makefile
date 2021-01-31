PYTHON=$(which python3)

install:
	sudo apt install git python3 python3-pip git-core python3-gpiozero
	pip3 install -r requirements.txt

run_pumpman1:
	python3 pumpman.py --config=config_pm1.ini

run_transfer_tank1:
	python3 transfer_tank.py --config=config_pm1.ini

run_pumpman2:
	python3 pumpman.py --config=config_pm2.ini

run_transfer_tank2:
	python3 transfer_tank.py --config=config_pm2.ini
