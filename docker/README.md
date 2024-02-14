# Running the Jupyter Lab notebooks locally in a container

## Using docker-compose or podman-compose

### Download the repository

`git clone https://github.com/getml/getml-demo.git`

### Change into the docker folder

`cd getml-demo/docker`

### Build the image

`podman-compose build`

### Run the service

Using Python 3.8

`podman-compose up getml_on_3_8`

or using Python 3.11

`podman-compose up getml_on_3_11`

⚠️ As they are set up to use the same ports and volume, you can't run both at the same time. 

### Open Jupyter Lab in the browser

Look for this line in the output and copy-paste it in your browser:

> Or copy and paste one of these URLs:
>
> http://localhost:8888/lab?token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

### Open getML Monitor in the browser

Look for this line in the output and copy-paste it in your browser:

> Please open a browser and point it to the following URL:
>
> http://localhost:1709/#/token/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
