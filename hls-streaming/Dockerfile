###############################
# Build the FFmpeg-build image.
FROM --platform=linux/amd64 alpine:3.13 as build

ARG PREFIX=/opt/ffmpeg
ARG LD_LIBRARY_PATH=/opt/ffmpeg/lib
ARG MAKEFLAGS="-j4"

# FFmpeg build dependencies.
RUN apk add --update \
  git \
  build-base \
  coreutils \
  freetype-dev \
  gcc \
  lame-dev \
  libogg-dev \
  libass \
  libass-dev \
  libvpx-dev \
  libvorbis-dev \
  libwebp-dev \
  libtheora-dev \
  opus-dev \
  openssl \
  openssl-dev \
  pkgconf \
  pkgconfig \
  rtmpdump-dev \
  wget \
  x264-dev \
  x265-dev \
  yasm

# Get fdk-aac from community.
RUN echo http://dl-cdn.alpinelinux.org/alpine/edge/community >> /etc/apk/repositories && \
  apk add --update fdk-aac-dev

# Get rav1e from testing.
RUN echo http://dl-cdn.alpinelinux.org/alpine/edge/testing >> /etc/apk/repositories && \
  apk add --update rav1e-dev

# Get ffmpeg source.
RUN cd /tmp/ && \
  git clone https://github.com/iosifnicolae2/FFmpeg.git ffmpeg

# Compile ffmpeg.
RUN cd /tmp/ffmpeg && \
  ./configure \
  --enable-version3 \
  --enable-gpl \
  --enable-nonfree \
  --enable-small \
  --enable-libmp3lame \
  --enable-libx264 \
  --enable-libx265 \
  --enable-libvpx \
  --enable-libtheora \
  --enable-libvorbis \
  --enable-libopus \
  --enable-libfdk-aac \
  --enable-libass \
  --enable-libwebp \
  --enable-librtmp \
  --enable-librav1e \
  --enable-postproc \
  --enable-libfreetype \
  --enable-openssl \
  --disable-debug \
  --disable-doc \
  --disable-ffplay \
  --extra-cflags="-I${PREFIX}/include" \
  --extra-ldflags="-L${PREFIX}/lib" \
  --extra-libs="-lpthread -lm" \
  --prefix="${PREFIX}" && \
  make && make install && make distclean

# Cleanup.
RUN rm -rf /var/cache/apk/* /tmp/*

##########################
# Build the release image.
FROM --platform=linux/amd64 alpine:3.13
LABEL MAINTAINER Alfred Gutierrez <alf.g.jr@gmail.com>
ENV PATH=/opt/ffmpeg/bin:$PATH

RUN apk add --update \
  ca-certificates \
  openssl \
  pcre \
  lame \
  libogg \
  libass \
  libvpx \
  libvorbis \
  libwebp \
  libtheora \
  opus \
  rtmpdump \
  x264-dev \
  x265-dev \
  bash

RUN apk add rav1e-libs --repository=https://dl-cdn.alpinelinux.org/alpine/edge/testing

COPY --from=build /opt/ffmpeg /opt/ffmpeg
COPY --from=build /usr/lib/libfdk-aac.so.2 /usr/lib/libfdk-aac.so.2
COPY --from=build /usr/lib/librav1e.so /usr/lib/librav1e.so

HEALTHCHECK --interval=5s --timeout=3s \
  CMD s=$(( $(date +%s) - $(stat /data/index.m3u8   -c %Y) )) && [ "$s" -lt "60" ] && echo "is up" || echo "is down" && rm -f /data/index.m3u8 ||  exit 1

CMD ["ffmpeg"]