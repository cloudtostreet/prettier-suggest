# Container image that runs your code
FROM ubuntu


RUN curl -sL https://deb.nodesource.com/setup_14.x | sudo -E bash -

RUN apt-get update
RUN apt-get install nodejs python

RUN npm install -g prettier

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["/entrypoint.sh"]