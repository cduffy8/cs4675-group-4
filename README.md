For running the backend:
1. Make sure to update .env file to contain MONGO_DB connection string (ask Danny/Duffy if confused)
2. Navigate to 'app' directory
3. Run `uvicorn main:app --reload`

For running the frontend:
1. cd into 'frontend-search' directory
2. make sure node is version 18+
3. make sure npm is installed
4. make sure vite is installed
5. run `npm run dev`

For running testin suite:
1. Make sure to update .env file to contain MONGO_DB connection string
2. Navigate to 'app' directory
3. Run `python test.py`