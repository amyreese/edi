setup:
	python3 -m pip install -U black mypy pylint twine
	python3 -m pip install -Ur requirements.txt

dev:
	python3 setup.py develop

release: lint test clean
	python3 setup.py sdist
	python3 -m twine upload dist/*

black:
	python3 -m black .

lint:
	python3 -m black --check .
	python3 -m pylint --rcfile .pylint edi tests
	-python3 -m mypy --python-version 3.6 .

test:
	python3 -m unittest tests

clean:
	rm -rf build dist README MANIFEST edi_slack.egg-info .mypy_cache
