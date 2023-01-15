FROM nginx:alpine AS builder

# Download sources
RUN wget "http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz" -O nginx.tar.gz && \
    wget "https://github.com/openresty/headers-more-nginx-module/archive/refs/tags/v0.34.tar.gz" -O headers-more-nginx-module.tar.gz

# For latest build deps, see https://github.com/nginxinc/docker-nginx/blob/master/mainline/alpine/Dockerfile
RUN apk add --no-cache --virtual .build-deps \
  gcc \
  libc-dev \
  make \
  openssl-dev \
  pcre-dev \
  zlib-dev \
  linux-headers \
  curl \
  gnupg \
  libxslt-dev \
  gd-dev \
  geoip-dev

# Reuse same cli arguments as the nginx:alpine image used to build
RUN CONFARGS=$(nginx -V 2>&1 | sed -n -e 's/^.*arguments: //p') \
	mkdir -p /usr/src && tar -zxC /usr/src -f nginx.tar.gz && \
  tar -zxC /usr/src -f "headers-more-nginx-module.tar.gz" && \
  cd /usr/src/nginx-$NGINX_VERSION && \
  ./configure --with-compat $CONFARGS --add-dynamic-module="/usr/src/headers-more-nginx-module-0.34" && \
  make && make install

FROM nginx:alpine
# Extract the dynamic module NCHAN from the builder image
COPY --from=builder /usr/local/nginx/modules/ngx_http_headers_more_filter_module.so /etc/nginx/modules/ngx_http_headers_more_filter_module.so

EXPOSE 80
STOPSIGNAL SIGTERM
CMD ["nginx", "-g", "daemon off;"]