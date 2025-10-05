# =========================
# Stage 1 - Build React App
# =========================
FROM node:18 AS build
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Accept build arguments
ARG REACT_APP_BACKEND_URL
ARG REACT_APP_FASTAPI_URL

# Set environment variables for build
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
ENV REACT_APP_FASTAPI_URL=$REACT_APP_FASTAPI_URL

# Build React app
RUN npm run build

# =========================
# Stage 2 - Serve with Nginx
# =========================
FROM nginx:alpine
WORKDIR /usr/share/nginx/html

# Remove default nginx static files
RUN rm -rf ./*

# Copy the React build output
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]