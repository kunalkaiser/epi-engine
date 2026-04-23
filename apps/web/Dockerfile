FROM node:20-alpine

WORKDIR /app/apps/web

ENV NODE_ENV=production

COPY apps/web/package.json ./package.json
COPY apps/web/package-lock.json ./package-lock.json
RUN npm ci

COPY apps/web ./

EXPOSE 3000

ARG API_BASE_URL
ARG API_AUTH_TOKEN
ENV API_BASE_URL=$API_BASE_URL
ENV API_AUTH_TOKEN=$API_AUTH_TOKEN
RUN npm run build

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3000"]
