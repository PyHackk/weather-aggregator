# 1. Get your API keys (free tier works):
# - https://openweathermap.org/api
# - https://www.weatherapi.com/

# 2. Setup
cp .env.example .env
# Edit .env and add your API keys

# 3. Run
docker-compose up --build

# 4. Initialize DB (in another terminal)
docker-compose exec web flask db init
docker-compose exec web flask db migrate -m "Initial migration"
docker-compose exec web flask db upgrade

# 5. Test it
curl http://localhost:5000/api/weather/Amsterdam