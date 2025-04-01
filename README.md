For running the backend:
1. Make sure you have docker installed
2. Make sure to update .env file to contain MONGO_DB connection string (ask Danny/Duffy if confused)
3. Navigate to 'app' directory
4. Run `docker pull qdrant/qdrant`
5. Run `docker run -p 6333:6333 -p 6334:6334 -v "$(pwd)/qdrant_storage:/qdrant/storage:z" qdrant/qdrant`
6. Run `uvicorn main:app --reload`
7. Make sure to clean up any docker containers/images after running

For running the frontend:
1. cd into 'frontend-search' directory
2. make sure node is version 18+
3. make sure npm is installed
4. make sure vite is installed
5. run `npm run dev`
