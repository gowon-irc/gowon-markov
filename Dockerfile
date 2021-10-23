FROM python:3.10-slim AS build-env

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . /src
WORKDIR /src
RUN pip install -r requirements.txt
RUN pip install .

FROM python:3.10-slim
COPY --from=build-env /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"
CMD ["gowon-markov"]
