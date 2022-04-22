## How run any example?

```shell

# Clone git repository
git clone https://github.com/kyzima-spb/flask-restlib.git

# Go to example directory
cd <EXAMPLE_DIR>

# Build docker images
docker-compose build

# Run the containers
docker-compose up -d

# Initialize database with test data
docker-compose exec backend db init
```
