FROM alpine

RUN apk --no-cache add \
    build-base \
    python3 \
    python3-dev \
    # wget dependency
    openssl \
    # dev dependencies
    bash \
    git \
    py3-pip \
    sudo \
    # Pillow dependencies
    freetype-dev \
    fribidi-dev \
    harfbuzz-dev \
    jpeg-dev \
    lcms2-dev \
    openjpeg-dev \
    tcl-dev \
    tiff-dev \
    tk-dev \
    zlib-dev

RUN python3 -m pip install --upgrade pip

RUN python3 -m pip install --upgrade Pillow

RUN pip install pilbox

EXPOSE 8888

CMD [ "python3", "-m" , "pilbox.app"]
