# Container image that runs your code
FROM ubuntu

RUN apt-get update && apt-get install python node

RUN npm install -g prettier

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["/entrypoint.sh"]