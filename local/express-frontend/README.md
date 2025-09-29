PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="case-autou-express-app"
NEW_TAG="v1"
docker build -t $SERVICE_NAME:$NEW_TAG .
docker tag $SERVICE_NAME:$NEW_TAG gcr.io/$PROJECT_ID/$SERVICE_NAME:$NEW_TAG
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:$NEW_TAG
gcloud run deploy $SERVICE_NAME   --image gcr.io/$PROJECT_ID/$SERVICE_NAME:$NEW_TAG   --set-secrets FAST_API=fast-api-route:latest   --platform managed   --region us-central1   --allow-unauthenticated   --port 8080

# 1. Build the new image locally
docker build -t $SERVICE_NAME:$NEW_TAG .

# 2. Tag the new image for the remote registry
docker tag $SERVICE_NAME:$NEW_TAG gcr.io/$PROJECT_ID/$SERVICE_NAME:$NEW_TAG

# 3. Push the new image to the Artifact Registry
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:$NEW_TAG

gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:$NEW_TAG \
  --set-env-vars="FAST_API=fast-api-route:latest" \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080

Local Test:

Build the image: docker build -t case-autou-webapp . (run this in the functions directory).

Run the container: docker run -p 8080:8080 case-autou-webapp

Test file upload at http://localhost:8080/. If it works here, the problem is definitively fixed!


pip install -r requirements.txt