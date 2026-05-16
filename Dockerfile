FROM zixia/wine:6.0

USER root
WORKDIR /

ENV WINEPREFIX=/home/user/.wine \
    LANG=zh_CN.UTF-8 \
    LC_ALL=zh_CN.UTF-8 \
    DISPLAY=:5 \
    VNCPASS=YourSafeVNCPassword \
    COMWECHAT=https://github.com/ljc545w/ComWeChatRobot/releases/download/3.7.0.30-0.1.1-pre/3.7.0.30-0.1.1-pre.zip

# 提示 vnc 使用的端口， dll 的端口自行映射
EXPOSE 5905


RUN rm /etc/apt/sources.list.d/wine-obs.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        ca-certificates \
        winbind \
        tigervnc-standalone-server \
        tigervnc-common \
        openbox \
        xdotool && \
    rm -rf /var/lib/apt/lists/*

ADD wine/simsun.ttc /home/user/.wine/drive_c/windows/Fonts/simsun.ttc
ADD wine/微信.lnk /home/user/.wine/drive_c/users/Public/Desktop/微信.lnk
ADD wine/system.reg wine/user.reg wine/userdef.reg /home/user/.wine/

# COPY wine/Tencent.zip /Tencent.zip
RUN wget --no-check-certificate -O /Tencent.zip "https://github.com/tom-snow/docker-ComWechat/releases/download/v0.2_wc3.7.0.30/Tencent.zip" && \
    wget --no-check-certificate -O /bin/dumb-init "https://github.com/Yelp/dumb-init/releases/download/v1.2.5/dumb-init_1.2.5_x86_64" && \
    mkdir -p "/home/user/WeChat Files" "/home/user/.wine/drive_c/users/user/Application Data" && \
    chmod a+x /bin/dumb-init && \
    rm -rf "/home/user/.wine/drive_c/Program Files/Tencent/" && \
    unzip Tencent.zip && \
    mv wine/Tencent "/home/user/.wine/drive_c/Program Files/" && \
    chown root:root -R /home/user/.wine && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf wine Tencent.zip /tmp/*

ADD WeChatHook.exe run.py run2.py comwechat_bridge.py /
RUN chmod a+x /run.py /run2.py

ENTRYPOINT [ "/bin/dumb-init" ]
CMD ["/run2.py", "start"]
