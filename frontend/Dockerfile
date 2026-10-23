FROM node:20-slim AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

# Принимаем аргументы из docker-compose
ARG VITE_API_URL
ARG VITE_MEDIA_BASE_URL=/media
ARG VITE_STORAGE_PUBLIC_HOST=/media
# Делаем их доступными как ENV для процесса сборки
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_MEDIA_BASE_URL=$VITE_MEDIA_BASE_URL
ENV VITE_STORAGE_PUBLIC_HOST=$VITE_STORAGE_PUBLIC_HOST
COPY . .
RUN npm run build

FROM nginx:alpine

# Копируем собранные файлы
COPY --from=builder /app/dist /usr/share/nginx/html

# Копируем конфиг nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
