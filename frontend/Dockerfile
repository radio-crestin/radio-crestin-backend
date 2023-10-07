# Production image, copy all the files and run next
FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
# Check https://github.com/nodejs/docker-node/tree/b4117f9333da4138b03a546ec926ef50a31506c3#nodealpine to understand why libc6-compat might be needed.
RUN apk add --no-cache libc6-compat curl

COPY yarn.lock package.json ./
RUN yarn install --frozen-lockfile

COPY . .
ARG FRONTEND_CDN_IMAGE_PREFIX
ENV FRONTEND_CDN_IMAGE_PREFIX=$FRONTEND_CDN_IMAGE_PREFIX
RUN yarn build

#RUN addgroup -g 1001 -S nodejs
#RUN adduser -S nextjs -u 1001
#USER nextjs
#RUN chown -R nextjs:node /app/.next

EXPOSE 8080

ENV PORT 8080

# Next.js collects completely anonymous telemetry data about general usage.
# Learn more here: https://nextjs.org/telemetry
# Uncomment the following line in case you want to disable telemetry.
# ENV NEXT_TELEMETRY_DISABLED 1

CMD ["yarn", "run", "start"]
