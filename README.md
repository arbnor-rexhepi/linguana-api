# linguana-api

## Environment files
First create .env.local, .env, .env.prod .env.dev files
Look in .env.example for all possible configs
You need to setup the environment
EXPORT ENV=local|dev|prod


## Locally setting up without docker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py collectstatic
python manage.py migrate


## With docker
sudo docker build -t linguana-api .
sudo docker run -d -p 8000:8000 --name linguana-api linguana-api

## Loading Languages from languanges.json file
python manage.py loaddata languages.json

## Creating Google authentication APP
To setup google authentication you need to first setup the site
Click to Sites on Admin
Change name from example.com to the name of the application, like api.linguana.io, or api-dev.linguana.io
Click to Social Application on Admin
Click Add New Application
Set Provider to Google
Fill Client id and Secret key, also move the site from available sites to Choosen sites
You can find or create client on OAuth in Google Cloud
Also you need to set frontend origins that are allowed to login like app.linguana.io or localhost:3000
to Authorized JavaScript origins section in google
