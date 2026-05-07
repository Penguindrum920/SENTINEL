# Azure Backend Deployment

This project is ready to run the backend on **Azure App Service (Linux, custom container)** while keeping the frontend on **Vercel**.

## Recommended Topology

- Frontend: Vercel
- Backend: Azure App Service (Linux, custom container)
- Frontend URL example: `https://sentinel-app.vercel.app`
- Backend URL example: `https://sentinel-api.azurewebsites.net`

This backend keeps simulation state in memory, so run it as a **single instance**.

## Why App Service

- Works well with the existing Docker-based backend
- Supports WebSockets on Linux apps
- Lets you keep one always-on backend process for the in-memory simulator

## Backend App Settings

Set these in Azure App Service:

```text
WEBSITES_PORT=8000
FRONTEND_URL=https://your-vercel-domain.vercel.app
ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app
SIMULATION_DURATION=23400
INITIAL_PRICE=100.0
```

If you use a custom Vercel domain, set `FRONTEND_URL` and `ALLOWED_ORIGINS` to that production domain instead.

## Azure Portal Steps

1. Create an Azure Container Registry.
2. Build and push the backend image from `backend/`.
3. Create an App Service using:
   - Publish: `Container`
   - Operating System: `Linux`
   - Region: close to your users
   - Plan: production plan with Always On support
4. In Deployment Center, point the app to your container image.
5. Add the app settings listed above.
6. In Configuration > General settings, enable `Web sockets`.
7. In App Service Health check, set the path to `/api/health`.
8. Keep instance count at `1`.
9. In Vercel, set:
   - `NEXT_PUBLIC_API_URL=https://<your-app>.azurewebsites.net`
   - `NEXT_PUBLIC_WS_URL=wss://<your-app>.azurewebsites.net`

Use the backend origin only. Do not append `/api` or `/ws` to those Vercel values.

## Azure CLI Example

Replace the placeholder values before running:

```bash
az acr create \
  --resource-group <rg> \
  --name <acr-name> \
  --sku Basic

az acr build \
  --registry <acr-name> \
  --image sentinel-backend:latest \
  ./backend

az appservice plan create \
  --resource-group <rg> \
  --name <plan-name> \
  --is-linux \
  --sku B1

az webapp create \
  --resource-group <rg> \
  --plan <plan-name> \
  --name <app-name> \
  --deployment-container-image-name <acr-name>.azurecr.io/sentinel-backend:latest

PRINCIPAL_ID=$(az webapp identity assign \
  --resource-group <rg> \
  --name <app-name> \
  --query principalId \
  --output tsv)

REGISTRY_ID=$(az acr show \
  --resource-group <rg> \
  --name <acr-name> \
  --query id \
  --output tsv)

az role assignment create \
  --assignee "$PRINCIPAL_ID" \
  --scope "$REGISTRY_ID" \
  --role AcrPull

az webapp config set \
  --resource-group <rg> \
  --name <app-name> \
  --generic-configurations '{"acrUseManagedIdentityCreds": true}'

az webapp config appsettings set \
  --resource-group <rg> \
  --name <app-name> \
  --settings \
    WEBSITES_PORT=8000 \
    FRONTEND_URL=https://your-vercel-domain.vercel.app \
    ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app \
    SIMULATION_DURATION=23400 \
    INITIAL_PRICE=100.0
```

After the app is created, configure:

- Web sockets: enabled
- Health check path: `/api/health`
- Instance count: `1`
- Always On: enabled

## Frontend Setup On Vercel

Set these environment variables in Vercel:

```text
NEXT_PUBLIC_API_URL=https://<your-app>.azurewebsites.net
NEXT_PUBLIC_WS_URL=wss://<your-app>.azurewebsites.net
```

Do not append `/api` or `/ws` to those variables.

## Operational Notes

- Do not scale out this backend horizontally unless you first move simulator state and WebSocket fanout out of process.
- Restarting the app resets the in-memory simulation state.
- If CORS fails, verify the exact Vercel production domain in `FRONTEND_URL` and `ALLOWED_ORIGINS`.
