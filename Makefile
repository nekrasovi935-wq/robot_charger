.PHONY: install run run-no-window test lint clean


install:
	pip install -r requirements.txt


run:
	python main.py
run-headless:
	python main.py --no-window
test:
	python -m pytest tests/ -v
lint:
	black .
	flake8 . --max-line-length=100
clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf tests/__pycache__