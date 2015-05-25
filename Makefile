init:
	pip install -r requirements.txt

test:
	py.test test_snarf.py

unittest:
	python -m unittest test_snarf

develop:
	pip install -e .

coverage:
	py.test --verbose --cov-report term --cov=snarf test_snarf.py

publish:
	python setup.py register
	python setup.py sdist upload
	# python setup.py bdist_wheel upload
 