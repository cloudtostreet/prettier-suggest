# Container image that runs your code
FROM ubuntu

RUN apt-get update -y
RUN apt-get install -y curl
RUN curl -sL https://deb.nodesource.com/setup_14.x | bash -

RUN apt-get install -y nodejs python

RUN npm install -g prettier

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["/entrypoint.sh"]