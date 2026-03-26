# ── Multi-stage build for Vue.js ──

# Stage 1: Build
FROM node:18-alpine as build-stage

WORKDIR /app

# Install dependencies first (leverage Docker cache)
COPY package*.json ./
RUN npm ci

# Copy full source and build
COPY . .
# We can provide a build-time arg if VITE_API_BASE_URL is needed during build
# ARGs are consumed by Vite during build
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build


# Stage 2: Serve with Nginx
FROM nginx:alpine as production-stage

# Copy the built output from stage 1 to nginx html dir
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration to route traffic properly
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
