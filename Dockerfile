################################################################################
# getml-base
FROM python:3.11.8 AS getml-base

RUN useradd getml
USER getml
WORKDIR /home/getml

COPY --chown=getml:getml --chmod=0777 ./requirements.txt /home/getml/requirements.txt

ENV PATH="/home/getml/.local/bin:$PATH"

RUN python3.11 \
    -mpip install \
    -r /home/getml/requirements.txt

RUN mkdir /home/getml/.getML

################################################################################
# getml-amd64
FROM getml-base AS getml-amd64
ARG GETML_ARCH=x64

################################################################################
# getml-arm64
FROM getml-base AS getml-arm64
ARG GETML_ARCH=arm64

################################################################################
# getml-demo
FROM getml-${TARGETARCH} AS getml-demo

ARG TARGETOS
ARG GETML_VERSION
ARG GETML_BUCKET="https://storage.googleapis.com/static.getml.com/download"
ARG GETML_ENGINE_FILE="getml-${GETML_VERSION}-${GETML_ARCH}-${TARGETOS}.tar.gz"
ARG GETML_ENGINE_URL="${GETML_BUCKET}/${GETML_VERSION}/${GETML_ENGINE_FILE}"

RUN curl "${GETML_ENGINE_URL}" | tar -C /home/getml/.getML -xvzf -

COPY --chown=getml:getml . /home/getml/demo/

EXPOSE 1709 8888
CMD [ "/home/getml/.local/bin/jupyter", "lab", "--ip='*'", "--port=8888", "--notebook-dir='/home/getml/demo'" ]