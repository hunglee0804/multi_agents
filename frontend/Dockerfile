# Sử dụng Nginx siêu nhẹ
FROM nginx:alpine

# Xóa cấu hình Nginx mặc định
RUN rm /etc/nginx/conf.d/default.conf

# Copy file cấu hình và toàn bộ code giao diện vào
COPY nginx.conf /etc/nginx/conf.d/
COPY . /usr/share/nginx/html

# ==========================================
# THIẾT LẬP BẢO MẬT NON-ROOT USER
# ==========================================
# Cấp quyền sở hữu cho user 'nginx' tại các thư mục nó cần đọc/ghi
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Kích hoạt user non-root (từ chối quyền root)
USER nginx

# Expose port 8080 (khớp với file nginx.conf)
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]