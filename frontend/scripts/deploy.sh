#!/bin/bash

# -------------------------
# 기본 설정
# -------------------------
APP_NAME="assetlog-frontend"
OUTER_PORT=3000
INNER_PORT=3000
ENV_FILE="/home/nogamsung/app/env/assetlog-frontend"
LOG_DIR="/home/nogamsung/app/assetlog-frontend/logs"
IMAGE="ghcr.io/nogamsung/assetlog-frontend:latest"

# -------------------------
# 이전 컨테이너 종료
# -------------------------
sudo docker kill $APP_NAME
sudo docker rm $APP_NAME

# -------------------------
# 새 컨테이너 실행
# -------------------------
docker run -itd \
    --name $APP_NAME \
    --restart=always \
    --env-file $ENV_FILE \
    -p $OUTER_PORT:$INNER_PORT \
    -v $LOG_DIR:/logs \
    -e PORT=$INNER_PORT \
    -e HOSTNAME=0.0.0.0 \
    -e NODE_ENV=production \
    $IMAGE

# -------------------------
# 새 애플리케이션 로그 확인
# -------------------------
sudo docker logs -f $APP_NAME
