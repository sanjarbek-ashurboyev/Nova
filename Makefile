# DEBUG is off by default; every local target turns it on.
DEV := DJANGO_DEBUG=1

test:
	$(DEV) python manage.py test

mig:
	$(DEV) python manage.py makemigrations
	$(DEV) python manage.py migrate
run:
	$(DEV) python manage.py runserver
