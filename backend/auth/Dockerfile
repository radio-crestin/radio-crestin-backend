FROM node:18.13.0-alpine3.17

RUN apk add --no-cache --update bash\
   && rm -rf /var/cache/apk/*

WORKDIR /home/node/app

COPY . /home/node/app
RUN yarn install --frozen-lockfile
ENV NODE_ENV production
RUN yarn build


RUN addgroup --system --gid 1001 app \
    && adduser --system --home /tmp/workdir --uid 1001 --ingroup app app

USER 1001

EXPOSE 8080

ENTRYPOINT ["yarn", "run", "start"]
