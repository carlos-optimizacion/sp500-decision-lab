.PHONY: install refresh snapshot test run

install:
	python -m pip install -r requirements-dev.txt

refresh:
	python -m data.ingestion.pipeline --refresh

snapshot:
	python scripts/build_snapshot.py --refresh

test:
	python -m pytest

run:
	streamlit run streamlit_app.py

