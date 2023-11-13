python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn --workers=3 --threads=3 app.wsgi --bind 0.0.0.0:8000 --timeout=300
