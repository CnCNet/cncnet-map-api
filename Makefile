#desolate:
#    POSTGRES_DATA_DIR = $(shell cat .env | grep POSTGRES_DATA_DIR)

serve:
	docker compose build django
	docker compose up nginx-server

stop:
	docker compose stop

test:
	docker compose build django
	docker compose run test


django-bash:
	# For running developer `./mange,py` commands in local dev.
	docker compose build django
	docker compose run django bash
