#!/bin/bash

# -------------------------
# 기본 설정
# -------------------------
APP_NAME="assetlog-backend"
OUTER_PORT=8000
INNER_PORT=8000
ENV_FILE="/home/nogamsung/app/env/assetlog-backend"
LOG_DIR="/home/nogamsung/app/assetlog-backend/logs"
IMAGE="ghcr.io/nogamsung/assetlog-backend:latest"

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
    $IMAGE \
    uvicorn app.main:app \
    --host 0.0.0.0 \
    --port $INNER_PORT

# -------------------------
# 새 애플리케이션 로그 확인
# -------------------------
sudo docker logs -f $APP_NAME
