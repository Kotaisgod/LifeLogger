#!/bin/bash
# LifeLogger - macOS launchd 自動起動設定スクリプト

PLIST_NAME="com.lifelogger.agent"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
PYTHON_PATH=$(which python3)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"

mkdir -p "$LOG_DIR"

install() {
    echo "LifeLogger launchd エージェントをインストールしています..."

    cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_PATH}</string>
        <string>${SCRIPT_DIR}/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF

    launchctl load "$PLIST_PATH"
    echo "インストール完了！LifeLoggerはバックグラウンドで実行中です。"
    echo "ログ: ${LOG_DIR}/"
}

uninstall() {
    echo "LifeLogger launchd エージェントを停止・削除しています..."
    launchctl unload "$PLIST_PATH" 2>/dev/null
    rm -f "$PLIST_PATH"
    echo "アンインストール完了"
}

status() {
    if launchctl list | grep -q "$PLIST_NAME"; then
        echo "LifeLogger: 実行中"
        launchctl list "$PLIST_NAME"
    else
        echo "LifeLogger: 停止中"
    fi
}

restart() {
    echo "LifeLogger を再起動しています..."
    launchctl unload "$PLIST_PATH" 2>/dev/null
    sleep 1
    launchctl load "$PLIST_PATH"
    echo "再起動完了"
}

case "$1" in
    install)   install ;;
    uninstall) uninstall ;;
    status)    status ;;
    restart)   restart ;;
    *)
        echo "使い方: $0 {install|uninstall|status|restart}"
        exit 1
        ;;
esac
