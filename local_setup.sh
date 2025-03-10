#!/usr/local/bin/python
pip install -r requirements/local.txt && \
python manage.py makemigrations && \
python manage.py migrate && \
echo yes | python manage.py collectstatic && \
pre-commit install && \
echo 'Setup completed!'
