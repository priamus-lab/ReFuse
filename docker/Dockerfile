FROM ubuntu:20.04 as python-base

    # python
ENV PYTHONUNBUFFERED=1 \
    # prevents python creating .pyc files
    PYTHONDONTWRITEBYTECODE=1 \
    \
    # pip
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    \
    # poetry
    # https://python-poetry.org/docs/configuration/#using-environment-variables
    POETRY_VERSION=1.1.5 \
    # make poetry install to this location
    POETRY_HOME="/opt/poetry" \
    # make poetry create the virtual environment in the project's root
    # it gets named `.venv`
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    # do not ask any interactive question
    POETRY_NO_INTERACTION=1 \
    \
    # paths
    # this is where our requirements + virtual environment will live
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv" \
    # Set system locale
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    TZ=Europe/Rome \
    AWS_RETRY_MODE=adaptive \
    DEBIAN_FRONTEND=noninteractive \
    AWS_MAX_ATTEMPTS=100  \
    CDS_HOME="/root" \
    ECCODES_DIR="/usr/src/eccodes" \
    ECCODES_DEFINITION_PATH="/usr/src/eccodes/share/eccodes/definitions"

# prepend poetry and venv to path
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# install runtime lib deps (python, gdal, postgres, ...)
RUN apt-get update && \
    apt-get install -y gcc tini git tcl && \
    mkdir /root/.prefect/ && \
    apt-get install -y --no-install-recommends --yes python3 && \
    apt-get install -y --no-install-recommends python3-pip && \
    pip3 install "pip==20.2.4" && \
    # install GDAL dependencies for rasterio
    # apt-get install -y software-properties-common && \
    # add-apt-repository ppa:ubuntugis/ppa && \
    # apt-get install -y python-numpy gdal-bin libgdal-dev && \
    # apt-get install -y --no-install-recommends gdal-bin=3.0.4\* && \
    # apt-get install -y --no-install-recommends libgdal-dev=3.0.4\*  && \
    apt-get install -y python3-dev && \
    apt-get install -y libpq-dev && \
    apt-get clean && apt-get autoremove -y && \
    rm -rf /var/lib/apt-get/lists/*

FROM python-base as gis-builder-base
RUN apt-get install -y --no-install-recommends --yes libnetcdf-dev libnetcdff-dev libopenjp2-7-dev gcc gfortran make unzip git cmake wget
RUN mkdir source_builds && \
    cd source_builds && mkdir eccodes && cd eccodes && \
    wget https://confluence.ecmwf.int/download/attachments/45757960/eccodes-2.23.0-Source.tar.gz && \
    tar -xzf eccodes-2.23.0-Source.tar.gz && \
    mkdir build && cd build && mkdir $ECCODES_DIR && \
    cmake -DCMAKE_INSTALL_PREFIX=$ECCODES_DIR -DENABLE_JPG=ON ../eccodes-2.23.0-Source && make && ctest && make install

FROM python-base as gis-base
COPY --from=gis-builder-base $ECCODES_DIR $ECCODES_DIR
RUN apt-get install -y --no-install-recommends --yes libnetcdf-dev
RUN apt-get install -y --no-install-recommends --yes libnetcdff-dev
RUN apt-get install -y --no-install-recommends --yes libopenjp2-7-dev
RUN cp -r $ECCODES_DIR/bin/* /usr/bin && cp $ECCODES_DIR/lib/libeccodes.so /usr/lib && cp /usr/src/eccodes/include/* /usr/include/ && \
    pip3 install eccodes-python


FROM python-base as builder-base
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        # deps for installing poetry
        curl \
        # deps for building python deps
        build-essential \
        python3-venv

# install poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python3

# copy project requirement files here to ensure they will be cached.
WORKDIR $PYSETUP_PATH
COPY poetry.lock pyproject.toml ./
# install runtime dependencies - uses $POETRY_VIRTUALENVS_IN_PROJECT internally
RUN poetry install --no-dev --no-root

# install package as wheel
COPY . .
RUN poetry build && \
    $VENV_PATH/bin/pip install --no-deps dist/*.whl \
    && rm -rf dist *.egg-info

# Production image used for runtime
FROM gis-base as production
COPY --from=builder-base $VENV_PATH $VENV_PATH
COPY .cdsapirc $CDS_HOME/.cdsapirc
