# CnCNet Map Browser API


The backend for the CnCNet map browser.

UI is here https://github.com/CnCNet/cncnet-map-ui


# Kirovy


The mascot for the backend API is Kirovy, by [Direct & Dominate](https://www.youtube.com/@DirectandDominate)

![Kirovy enjoying his job](docs/images/kirovy_direct_and_dominate.png)

# Development


## Frontend devs

Just set up your environment file and run the full docker compose.

[Example env file](example.env)

## Backend devs

1. Download and install [pyenv](https://github.com/pyenv/pyenv)
2. Install [PostgreSQL](https://www.postgresql.org/) for your system. This is required for Django
   - On Mac you can do `brew install postgresql` if you have brew installed.
3. Checkout the repository
4. Switch to the repository directory
5. Setup Python
   - Install Python 3.12 `pyenv install 3.12` or whatever the latest python is.
   - Setup the virtual environments `pyenv virtualenv 3.12 cncnet-map-api`
   - Set the virtual enviornment for the directory `pyenv local cncnet-map-api`
6. Setup requirements `pip install -r requirements-dev.txt`
   -  On Apple Silicon you'll need to install lzo with `brew install lzo` then run
      `CFLAGS=-I$(brew --prefix)/include LDFLAGS=-L$(brew --prefix)/lib pip install -r requirements-dev.txt`
      to get `python-lzo` to install. You shouldn't need to include those flags again unless `python-lzo` updates.
7. Install the pre-commit hooks `pre-commit install`
8. Setup the environment variables
   - Create a `.env` file at the root of the repo
   - Copy the contents of `example.env` to your `.env` file.
   - Fill out the required values in `.env`
   - If the app doesn't run due to a missing required variable, add said variable to `example.env` because the person
   who made the variable forgot to do so.
9. Run the `db` service in `docker-compose`
10. Load your `.env` file into your shell, (you can use `./load_env.sh`) then migrate the database `./manage.py migrate`
11. `./manage.py runserver`

I **strongly** recommend using PyCharm and the `.env` plugin for running the PyTests.

You can technically use PyCharm to launch everything via `docker-compose`, but there is some
weird issue with breakpoints not triggering.
