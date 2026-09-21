FROM ubuntu:20.04

# 避免交互式提示
ENV DEBIAN_FRONTEND=noninteractive

# 安裝必要的依賴
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common \
    python3 \
    python3-pip

# 添加 Microsoft Edge 存儲庫
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    add-apt-repository "deb [arch=amd64] https://packages.microsoft.com/repos/edge stable main"

# 安裝 Microsoft Edge
RUN apt-get update && apt-get install -y microsoft-edge-dev

# 設置工作目錄
WORKDIR /app

# 複製並安裝 Python 依賴
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# 複製應用代碼
COPY . .

# 運行應用
CMD ["python3", "stock_warning.py"]