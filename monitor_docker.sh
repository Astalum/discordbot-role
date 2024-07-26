#!/bin/bash

# 監視対象のコンテナ名
CONTAINER_NAME="attender"

# 監視間隔（秒）
INTERVAL=3600

# 無限ループで監視を行う
while true; do
    # コンテナのステータスを取得
    STATUS=$(docker inspect -f '{{.State.Status}}' $CONTAINER_NAME)

    # コンテナが停止している場合
    if [ "$STATUS" != "running" ]; then
        echo "$(date) - Container $CONTAINER_NAME is not running. Status: $STATUS"
        
        # コンテナを再起動
        echo "$(date) - Restarting container $CONTAINER_NAME..."
        docker restart $CONTAINER_NAME
        
        # 再起動の結果を表示
        if [ $? -eq 0 ]; then
            echo "$(date) - Container $CONTAINER_NAME restarted successfully."
        else
            echo "$(date) - Failed to restart container $CONTAINER_NAME."
        fi
    else
        echo "$(date) - Container $CONTAINER_NAME is running."
    fi

    # 監視間隔の時間だけ待機
    sleep $INTERVAL
done
