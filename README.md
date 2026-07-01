# How to Use

### 1. Clone the repository

```bash
git clone https://github.com/luis-otavio-dias/road-asset-recovery
cd road-asset-recovery
```

### 2. Configure Environment Variables

Rename `.env-example` to `.env` and replace `YOUR-TOKEN` with your actual Mapillary Access Token (you can get one at [https://www.mapillary.com/dashboard/developers](https://www.mapillary.com/dashboard/developers)):

```bash
cp .env-example .env
```

Inside the `.env` file, ensure the following is set:
```
MAPILLARY_ACCESS_TOKEN="YOUR-TOKEN"
```

### 3. Create container

```bash
docker compose up --build
# or: docker-compose up --build
```

### 4. Access the application

The application will be disponible in:

```bash
http://0.0.0.0:8001
```
