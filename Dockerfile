FROM python:3.11.8

RUN useradd getml
USER getml
WORKDIR /home/getml

COPY --chown=getml:getml --chmod=0777 ./requirements.txt /home/getml/requirements.txt

ENV PATH="$PATH:/home/getml/.local/bin"
RUN python3.11 \
    -mpip install \
    -r /home/getml/requirements.txt

RUN mkdir /home/getml/.getML /home/getml/.getML/logs /home/getml/.getML/projects /home/getml/demo
RUN curl https://storage.googleapis.com/static.getml.com/download/1.4.0/getml-1.4.0-x64-linux.tar.gz | tar -C /home/getml/.getML -xvzf -

EXPOSE 1709 8888
CMD [ "/home/getml/.local/bin/jupyter", "lab", "--ip='*'", "--port=8888", "--notebook-dir='/home/getml/demo'" ]