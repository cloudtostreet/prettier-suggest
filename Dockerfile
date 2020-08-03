# Container image that runs your code
FROM alpine

RUN apk add --no-cache python node

RUN npm install -g prettier

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["/entrypoint.sh"]