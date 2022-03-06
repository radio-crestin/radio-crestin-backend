FROM node:16.14.0-alpine3.14

RUN apk add --no-cache --update bash\
   && rm -rf /var/cache/apk/*

WORKDIR /home/node/app

COPY package.json package.json
COPY yarn.lock yarn.lock
RUN yarn install

COPY . /home/node/app

RUN yarn run test

ENV NODE_ENV production
RUN yarn run build

RUN addgroup -g 1001 -S app
RUN adduser -S app -u 1001

EXPOSE 8080

USER app

ENTRYPOINT ["yarn", "run", "start"]
