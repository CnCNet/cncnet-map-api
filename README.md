# CnCNet Map Browser API

The backend for the CnCNet map browser.

UI is here https://github.com/CnCNet/cncnet-map-ui


# Development

1. Download and install [pyenv](https://github.com/pyenv/pyenv)
2. Install [PostgreSQL](https://www.postgresql.org/) for your system. This is required for Django
   - On Mac you can do `brew install postgresql` if you have brew installed.
3. Checkout the repository
4. Switch to the repository directory
5. Setup Python
   - Install Python 3.11 `pyenv install 3.11`
   - Setup the virtual environments `pyenv virtualenv 3.11 cncnet-map-api`
   - Set the virtual enviornment for the directory `pyenv local cncnet-map-api`
6. Setup requirements `pip install -r requirements-dev.txt`
7. Install the pre-commit hooks `pre-commit install`
8. Setup the environment variables
   - Create a `.env` file at the root of the repo
   - Copy the contents of `example.env` to your `.env` file.
   - Fill out the required values in `.env`
   - If the app doesn't run due to a missing required variable, add said variable to `example.env` because the person
   who made the variable forgot to do so.
9.
