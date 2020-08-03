# Container image that runs your code
FROM node

RUN npm install -g prettier

COPY . .

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["/entrypoint.sh"]