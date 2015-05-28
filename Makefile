init:
	pip install -r requirements.txt

test:
	py.test tests

unittest:
	python -m unittest discover -s tests

develop:
	pip install -e .

coverage:
	py.test --verbose --cov-report term --cov=snarf test_snarf.py

publish:
	python setup.py register
	python setup.py sdist upload
	# python setup.py bdist_wheel upload
 