# STAGE 1 - Builder 
FROM python:3.12.12-slim-bookworm AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Copy file cấu hình uv 
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev --no-cache

# COPY BACKEND CODE
COPY app/ ./app/
COPY multi_agents/ ./multi_agents/
COPY faiss_cache/ ./faiss_cache/
COPY main.py ./

# ==========================================
# STAGE 2 - Runtime
# ==========================================
FROM python:3.12.12-slim-bookworm AS runtime

# TẠO NON-ROOT USER: Tạo group và user tên là 'appuser' không có quyền admin
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"

# CHUYỂN QUYỀN SỞ HỮU: Dùng cờ --chown để đảm bảo appuser có quyền đọc/thực thi các file này
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/app/ ./app/
COPY --from=builder --chown=appuser:appuser /app/multi_agents/ ./multi_agents/
COPY --from=builder --chown=appuser:appuser /app/faiss_cache/ ./faiss_cache/
COPY --from=builder --chown=appuser:appuser /app/main.py ./

# KÍCH HOẠT NON-ROOT USER: Từ dòng này trở đi, mọi lệnh sẽ chạy dưới quyền của 'appuser'
USER appuser

# Expose port cho backend
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]