TESTS=

init:
	pip install -r requirements.txt

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
 