import redis
import os

# Trong thực tế, URL này nên được lấy từ biến môi trường (ví dụ: dotenv)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# decode_responses=True giúp dữ liệu trả về là chuỗi (string) thay vì bytes
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def check_redis_connection():
    try:
        redis_client.ping()
        print("✅ Successfully connected to the Redis Server!")
    except redis.ConnectionError:
        print("⚠️ Unable to connect to the Redis server. Please check again.")