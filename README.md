1. Make sure you have docker installed
2. Run `docker pull qdrant/qdrant`
3. Run `docker run -p 6333:6333 -p 6334:6334 -v "$(pwd)/qdrant_storage:/qdrant/storage:z" qdrant/qdrant`
4. Navigate to 'app' directory
5. Run `uvicorn main:app --reload`
6. Make sure to clean up any docker containers/images after running
