VERSION=$(shell grep version beesly/version.py | cut -f2 -d '=' | xargs | tr -d '"')
WORKERS=4
PORT=8000

install:
	pipenv --python 3.6; \
	pipenv install --dev; \
	pipenv lock -r > requirements.txt; \

test:
	nose2 -v -s beesly/ -C --coverage-report html

coverage:
	coverage run --source=beesly -m unittest discover -s beesly/tests

lint:
	flake8 --statistics --ignore E221,E501,E722 beesly/

build:
	docker build -t beesly:$(VERSION) .

clean:
	find . -name "*pyc" -exec rm -f "{}" \;
	coverage erase && rm -rf htmlcov

run:
	pipenv run gunicorn -c gconfig.py --preload -w $(WORKERS) -b '0.0.0.0:$(PORT)' serve:app

run-container:
	docker run -d -p $(PORT):$(PORT) beesly:$(VERSION)
