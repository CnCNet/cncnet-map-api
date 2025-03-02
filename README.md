# CnCNet Map Browser API


The backend for the CnCNet map browser.

UI is here https://github.com/CnCNet/cncnet-map-ui


# Kirovy


The mascot for the backend API is Kirovy, by [Direct & Dominate](https://www.youtube.com/@DirectandDominate)

![Kirovy enjoying his job](docs/images/kirovy_direct_and_dominate.png)

# Development

## Frontend devs

Just set up your environment file and run `docker compose up web -d`.

This will launch the database, run the migrations, and start the django web server.

[Example env file](example.env)

## Backend devs

You can use docker compose if you'd like, but here are the native OS instructions.

### Linux and Mac

1. Download and install [pyenv](https://github.com/pyenv/pyenv)
   > You don't have to use `pyenv` but it makes life much easier when dealing with virtual environments.
2. Install [PostgreSQL](https://www.postgresql.org/) for your system. This is required for Django
   - On Mac you can do `brew install postgresql` if you have brew installed.
3. Install LibMagic for [Python Magic](https://github.com/ahupp/python-magic)
   - On Mac you can do `brew install libmagic` if you have brew installed.
   > LibMagic is used for checking file types.
4. Checkout the repository
5. Switch to the repository directory
6. Setup Python
   - Install Python 3.12 `pyenv install 3.12` or whatever the latest python is.
   - Setup the virtual environments `pyenv virtualenv 3.12 cncnet-map-api`
   - Set the virtual environment for the directory `pyenv local cncnet-map-api`
7. Install the dev requirements `pip install -r requirements-dev.txt`
   -  On Apple Silicon you'll need to install lzo with `brew install lzo` then run
      `CFLAGS=-I$(brew --prefix)/include LDFLAGS=-L$(brew --prefix)/lib pip install -r requirements-dev.txt`
      to get `python-lzo` to install. You shouldn't need to include those flags again unless `python-lzo` updates.
8. Install the pre-commit hooks `pre-commit install`
9. Setup the environment variables
   - Create a `.env` file at the root of the repo
   - Copy the contents of `example.env` to your `.env` file.
   - Fill out the required values in `.env`
   - If the app doesn't run due to a missing required variable, add said variable to `example.env` because the person
   who made the variable forgot to do so.
10. Run the `db` service in `docker-compose`
11. Load your `.env` file into your shell, (you can use `source load_env.sh && read_env`)<a name="load-shell-env"></a>
then migrate the database `./manage.py migrate`
12. Run the django server with `./manage.py runserver`

Tests can be run by following [these instructions](#running-tests-backend-devs)


### Windows

Chairman Bing of the Massivesoft corporation strikes again; getting the `LZO` libraries running
natively on Windows is a... less-than-pleasant effort. So use docker instead.

1. Install docker for windows. I have had success with [Rancher Desktop](https://rancherdesktop.io/)
   or [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/)
2. After docker is running, switch to your local git repo and run `docker compose up windows-dev -d`.
   Make sure the build succeeds.
3. Set `windows-dev` as your python interpreter for whichever editor you use.

> [!TIP]
> In Pycharm you go to `Settings > Project > Python Interpreter > Add Interpreter > Docker Compose`


## Running tests (backend devs)

I strongly recommend using PyCharm (or any other Python IDE with breakpoints) and the `.env` plugin for running the PyTests.
All you need to do is run the database from `docker-compose`, then launch the tests via PyCharm.

**If you want to run the tests via CLI:**

- Make sure your database is running from the docker compose file. `docker-compose start db`
- Make sure your environment variables are setup and loaded to your shell. See [backend dev setup](#load-shell-env)
- Run `DJANGO_SETTINGS_MODULE="kirovy.settings.testing" pytest tests`

Django should automatically run migrations as part of the test startup.

**Run tests with docker compose:**

- `docker-compose up --build test`
