# 1단계: 빌드용 Node 환경
FROM node:18-alpine AS builder

WORKDIR /app
COPY . .
RUN npm install && npm run build

# 2단계: nginx로 정적 파일 서빙
FROM nginx:stable-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
