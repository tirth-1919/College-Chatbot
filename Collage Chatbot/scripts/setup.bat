@echo off
echo =========================================================
echo Ahmedabad Institute of Technology (AIT) AI Assistant Setup
echo =========================================================

echo [1/3] Installing Python backend packages...
pip install -r backend/requirements.txt

echo [2/3] Seeding AIT Master Database...
python -m database.seed.seed_data

echo [3/3] Installing Frontend dependencies...
cd frontend
call npm install
cd ..

echo =========================================================
echo Setup Complete!
echo Run Backend: python backend/run.py
echo Run Frontend: cd frontend ^&^& npm run dev
echo Run Tests: python -m pytest tests/test_master_acceptance.py -v
echo =========================================================
pause
