FROM python:3.11.8

RUN useradd getml
USER getml
WORKDIR /home/getml

COPY --chown=getml:getml --chmod=0777 ./requirements.txt /home/getml/requirements.txt

ENV PATH="/home/getml/.local/bin:$PATH"

RUN python3.11 \
    -mpip install \
    -r /home/getml/requirements.txt

ARG TARGETOS
ARG TARGETARCH
ARG GETML_VERSION_NUMBER

RUN mkdir /home/getml/.getML

RUN <<EOT
    #!/bin/bash
    if [ "${TARGETARCH}" = "amd64" ]; then
        export GETML_ARCH="x64"
    else
        export GETML_ARCH="${TARGETARCH}"
    fi;
    curl "https://storage.googleapis.com/static.getml.com/download/${GETML_VERSION_NUMBER}/getml-${GETML_VERSION_NUMBER}-"`echo \${GETML_ARCH}`"-${TARGETOS}.tar.gz" | 
        tar -C /home/getml/.getML -xvzf -
EOT

COPY --chown=getml:getml . /home/getml/demo/

EXPOSE 1709 8888
CMD [ "/home/getml/.local/bin/jupyter", "lab", "--ip='*'", "--port=8888", "--notebook-dir='/home/getml/demo'" ]