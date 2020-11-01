DB=db.db
PYTHON=$(which python3)

build:
	touch $(DB)
	$(PYTHON) -m venv .env
	source .env/bin/activate
	python3 db.py



