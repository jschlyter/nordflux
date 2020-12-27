all: reformat lint
	
reformat:
	isort nordflux
	black nordflux

lint:
	pylama nordflux

build:
	poetry build

container: build
	docker build -t nordflux .

clean:
	rm -fr dist
