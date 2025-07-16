FROM python:3.13-slim

ENV PYTHONBUFFERED 1

RUN apt-get update && apt-get install -y curl git

RUN python -m pip install pip

WORKDIR /docker
COPY ./docker/flask/entrypoint.sh .
RUN chmod +x ./entrypoint.sh

WORKDIR /requirements
COPY ./igvf-catalog-llm/requirements.txt .
RUN pip install -r requirements.txt

WORKDIR /igvf-catalog-llm

COPY . .

WORKDIR /igvf-catalog-llm/igvf-catalog-llm

EXPOSE 5000

ENTRYPOINT ["/docker/entrypoint.sh"]

CMD ["flask", "run", "--host=0.0.0.0"]
