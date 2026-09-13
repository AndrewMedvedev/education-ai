FROM node:20-slim AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

# Принимаем аргументы из docker-compose
ARG VITE_API_URL
# Делаем их доступными как ENV для процесса сборки
ENV VITE_API_URL=$VITE_API_URL
COPY . .
RUN npm run build

FROM nginx:alpine

# Копируем собранные файлы
COPY --from=builder /app/dist /usr/share/nginx/html

# Копируем конфиг nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
