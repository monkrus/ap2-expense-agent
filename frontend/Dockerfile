# AP2 Expense Agent - Frontend Dockerfile
# Multi-stage build for optimized production deployment

# Build stage
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && \
    npm cache clean --force

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Production stage - Serve with nginx
FROM nginx:1.25-alpine

# Install curl for health checks
RUN apk add --no-cache curl

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built application from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Add healthcheck script
RUN echo '#!/bin/sh' > /healthcheck.sh && \
    echo 'curl -f http://localhost:80/ || exit 1' >> /healthcheck.sh && \
    chmod +x /healthcheck.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["/healthcheck.sh"]

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
