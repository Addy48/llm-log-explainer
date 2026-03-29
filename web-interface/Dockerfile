FROM node:20-alpine

WORKDIR /app

COPY index.html app.js style.css ./

RUN npm install -g http-server

EXPOSE 3000

CMD ["http-server", "-p", "3000", "--cors"]
