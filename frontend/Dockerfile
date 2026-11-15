FROM node:22-alpine
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
COPY terrain3d/ /app/terrain3d/
EXPOSE 5173
CMD ["npm","run","dev","--","--host","0.0.0.0"]
