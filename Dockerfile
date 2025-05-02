FROM python:alpine

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

RUN apk add firefox

RUN apk add geckodriver

COPY ./scrape_smart_meter_texas.py /code/scrape_smart_meter_texas.py
COPY ./login_information.py /code/login_information.py
COPY ./config_variables.py /code/config_variables.py

ENV TZ=America/Chicago

CMD ["python", "/code/scrape_smart_meter_texas.py"]