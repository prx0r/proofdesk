#!/bin/bash
set -e

echo "ProofDesk — Deploy to Railway"
echo "=============================="
echo ""

# Check if railway is installed
if ! command -v railway &>/dev/null; then
    echo "Installing Railway CLI..."
    npm install -g @railway/cli
fi

# Check if logged in
if ! railway whoami &>/dev/null; then
    echo "Please log in to Railway:"
    railway login
fi

# Link or create project
echo "Linking to Railway project..."
railway link 2>/dev/null || railway init

# Set environment variable
echo "Setting NUTRIENT_API_KEY..."
railway variables set NUTRIENT_API_KEY="pdf_live_hAAUR0ppmrzrIQcOqnPH29ea5z0uioX8pO9SGG6XYmk"

# Deploy
echo "Deploying..."
railway up

# Get URL
echo ""
echo "Deployed! Check your Railway dashboard for the URL."
echo "Or run: railway domain"
