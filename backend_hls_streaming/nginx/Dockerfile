FROM nginx:1.25-alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create necessary directories for nginx operation
RUN mkdir -p /tmp/client_temp /tmp/data/hls /tmp/nginx-logs && \
    chown -R nginx:nginx /tmp/client_temp /tmp/data /tmp/nginx-logs && \
    chmod -R 755 /tmp/client_temp /tmp/data /tmp/nginx-logs

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]