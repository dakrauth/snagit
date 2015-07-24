TESTS=

uninstall:
	- pip uninstall --yes snarf >/dev/null
	@echo

init: uninstall
	pip install -U -r requirements.txt
	pip install -U -e .
	@echo

test:
	py.test tests

test-only:
	# Example: make test-only TEST="select"
	@echo Only testing $(TESTS)
	py.test tests -k $(TESTS)

unittest:
	@echo $(TESTS)
	python -m unittest discover -s tests $(TESTS)

develop:
	pip install -e .

coverage:
	py.test --verbose --cov-report term --cov=snarf test_snarf.py

publish:
	python setup.py register
	python setup.py sdist upload
	# python setup.py bdist_wheel upload

clean:
	rm -rf .tox *.egg dist build .coverage
	find . -name '__pycache__' -delete -print -o -name '*.pyc' -delete -print
	@echo