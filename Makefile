SOURCE=	nordflux.py

all: reformat lint
	
reformat:
	uv run ruff check --select I --fix
	uv run ruff format

lint:
	uv run ruff check $(SOURCE)

container:
	docker build -t nordflux .

clean:
	rm -fr dist
