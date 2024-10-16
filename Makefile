SOURCE=	nordflux.py

all: reformat lint
	
reformat:
	isort $(SOURCE)
	black $(SOURCE)

lint:
	pylama $(SOURCE)

build:
	poetry build

container:
	docker build -t nordflux .

clean:
	rm -fr dist
