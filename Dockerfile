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
# getml-demo
FROM getml-base AS getml-demo

ARG TARGETARCH
ARG TARGETOS
RUN \
    if [ "${TARGETARCH}" = "amd64" ]; then \
        export GETML_ARCH="x64" ;\
    else \
        export GETML_ARCH="${TARGETARCH}" ;\
    fi; \
    export GETML_VERSION=$(grep -o "^getml==.*$" requirements.txt | cut -b8-) ;\
    export GETML_BUCKET="https://storage.googleapis.com/static.getml.com/download" ;\
    export GETML_ENGINE_FILE="getml-${GETML_VERSION}-${GETML_ARCH}-${TARGETOS}.tar.gz" ;\
    export GETML_ENGINE_URL="${GETML_BUCKET}/${GETML_VERSION}/${GETML_ENGINE_FILE}" ;\
    echo "Downloading getML engine from ${GETML_ENGINE_URL}" ;\
    curl ${GETML_ENGINE_URL} | tar -C /home/getml/.getML -xvzf -

COPY --chown=getml:getml . /home/getml/demo/

EXPOSE 1709 8888
CMD [ "/home/getml/.local/bin/jupyter", "lab", "--ip='*'", "--port=8888", "--notebook-dir='/home/getml/demo'" ]
