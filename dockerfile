FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

#RUN rm settings.py

CMD [ "python", "gardener.py" ]

# docker build -t dripgarden:latest .
# docker run --restart=unless-stopped -e MINIMUM_NEW_PLANTS=7 --name dripgarden -d dripgarden:latest

# docker run -d -e MINIMUM_NEW_PLANTS=1500 -v "$PWD":/usr/src/myapp dlv111/crypto-web3:latest python gardener.py