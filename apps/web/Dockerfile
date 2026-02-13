FROM node:20-alpine

WORKDIR /app

# Install dependencies first (better layer caching)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code
COPY . .

EXPOSE 5173

# Run Vite dev server, accessible from outside the container
CMD ["npx", "vite", "--host", "0.0.0.0"]
