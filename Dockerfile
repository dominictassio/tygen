FROM python:3.13-alpine
WORKDIR /usr/src/app
RUN apk add nodejs npm
RUN npm install --global typescript
COPY tarballs tarballs
COPY pyproject.toml .
RUN pip install .
COPY main.py tsconfig.json .
CMD ["python", "main.py"]
