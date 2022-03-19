FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

#RUN rm settings.py

CMD [ "python", "gardener.py" ]

# docker build -t dripgarden:latest .
# docker run --name dripgarden -d dripgarden:latest
