python manage.py collectstatic --no-input
python manage.py migrate
# `python manage.py runserver`, but with gunicorn instead.
gunicorn "kirovy.wsgi:application" --bind "0.0.0.0:8000"
