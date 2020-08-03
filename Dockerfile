# Container image that runs your code
FROM python:3

RUN npm install -g prettier

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["/entrypoint.sh"]