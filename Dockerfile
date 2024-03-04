ARG TARGETPLATFORM
FROM --platform=${TARGETPLATFORM} python:3.11.8

RUN useradd getml
USER getml
WORKDIR /home/getml

COPY --chown=getml:getml --chmod=0777 ./requirements.txt /home/getml/requirements.txt

ENV PATH="$PATH:/home/getml/.local/bin"
RUN python3.11 \
    -mpip install \
    -r /home/getml/requirements.txt

ARG TARGETOS
ARG TARGETARCH

ENV GETML_VERSION 1.4.0

RUN mkdir /home/getml/.getML /home/getml/.getML/logs /home/getml/.getML/projects /home/getml/demo
RUN if [ "${TARGETARCH}" = "amd64" ]; then \
        export GETML_ARCH="x64"; \
    else \
        export GETML_ARCH="${TARGETARCH}"; \
    fi;\
    curl https://storage.googleapis.com/static.getml.com/download/${GETML_VERSION}/getml-${GETML_VERSION}-${GETML_ARCH}-${TARGETOS}.tar.gz | tar -C /home/getml/.getML -xvzf -

EXPOSE 1709 8888
CMD [ "/home/getml/.local/bin/jupyter", "lab", "--ip='*'", "--port=8888", "--notebook-dir='/home/getml/demo'" ]