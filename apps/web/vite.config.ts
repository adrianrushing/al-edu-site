import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { TanStackRouterVite } from '@tanstack/router-plugin/vite'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        TanStackRouterVite(),
        react(),
    ],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    server: {
        proxy: {
            '/api': {
                target: process.env.NODE_ENV === 'development'
                    ? 'http://127.0.0.1:5000'
                    : process.env.VITE_API_BASE || 'http://127.0.0.1:5000',
                changeOrigin: true,
                rewrite: (path) => path,
            },
        },
    },
})
