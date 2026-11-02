FROM node:22-alpine
WORKDIR /app
COPY lib/atlas-storage.mjs lib/chunked-graph.mjs ./lib/
COPY portable/server.mjs portable/file-bucket.mjs ./portable/
ENV HOST=0.0.0.0 PORT=8787 ATLAS_DATA_DIR=/data NODE_ENV=production
USER node
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD node -e "fetch('http://127.0.0.1:8787/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "portable/server.mjs"]
