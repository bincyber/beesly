install:
	pip install -r requirements-dev.txt

test:
	nose2 -v -s beesly/ -C --coverage-report html

coverage:
	coverage run --source=beesly -m unittest discover -s beesly/tests

lint:
	flake8 --statistics --ignore E221,E501 beesly/

build:
	docker build -t beesly:latest .

clean:
	find . -name "*pyc" -exec rm -f "{}" \;
	coverage erase && rm -rf htmlcov

run:
	gunicorn -c gconfig.py -w 2 -b '0.0.0.0:8000' serve:app

run-container:
	docker run -d -P beesly:latest
