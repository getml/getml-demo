# getML on Vertex AI

### Requirements

- Python (>= 3.10)
- Hatch / pip
- gcloud
- Docker

Note: VSCode dev container available (instructions follow)

### Authenticate
First, authenticate with gitlab, for example:

```sh
ssh -T git@gitlab.com
```

### Install
This project uses [Hatch](https://hatch.pypa.io/latest/) to manage the Python environment and dependencies. Follow the steps below to set up the project:

1. **Install Hatch**:
    ```bash
    pip install hatch
    ```

2. **Clone the repository**:
    ```bash
    git clone git@gitlab.com:getml/all/playbooks.git
    cd playbooks
    ```

3. **Create and activate dev environment**:
    ```bash
    hatch shell
    ```

### Run

Now just run JupyterLab or any other Notebook Server to open `demo_binary_classification.ipynb`

```sh
jupyter lab demo_binary_classification.ipynb
```
