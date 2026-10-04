@echo off
docker run --rm -it -e APP_ENV=dev -e MONGODB_SETTINGS -e SEND_GRID_KEY -p 8000:8000 mal-service-image
