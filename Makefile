start:
	docker-compose up

stop:
	docker-compose stop

clean:
	docker-compose down

build:
	docker-compose build

test:
	docker-compose run --rm daemon python test.py

lint: # lint currently staged files
	pre-commit run

lint-all: # lint all files in repository
	pre-commit run --all-files

code-syle-check:
	docker-compose run daemon pre-commit run --all-files
