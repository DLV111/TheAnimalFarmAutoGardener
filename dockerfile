FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

#RUN rm settings.py

CMD [ "python", "gardener.py" ]

# docker build -t dripgarden:latest .
# docker run --restart=unless-stopped -e MINIMUM_NEW_PLANTS=7 --name dripgarden -d dripgarden:latest
