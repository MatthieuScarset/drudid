#################################################################################
# GLOBALS                                                                       #
#################################################################################

# Load .env file if it exists, create from example if not
ifeq (,$(wildcard .env))
    $(shell cp .env.example .env 2>/dev/null || true)
endif
ifneq (,$(wildcard .env))
    include .env
    export
endif

PYTHON_CMD := $(PYTHON_INTERPRETER)$(PYTHON_VERSION)

## ---------------
## Global commands
## ---------------

.DEFAULT_GOAL := help

help:	## Self Documenting Commands
	@sed -ne '/@sed/!s/## //p' $(MAKEFILE_LIST)

install:	## Set up Python interpreter environment and install dependencies
	$(PYTHON_CMD) -m venv .venv
	@echo ">>> Virtual environment created."
	@echo ">>> Installing dependencies..."
	./.venv/bin/python -m pip install --upgrade pip
	./.venv/bin/python -m pip install -r requirements.txt
	./.venv/bin/python -m nbautoexport install
	@echo ">>> Installation complete. Activate with:"
	@echo ">>> source ./.venv/bin/activate"
	
clean:	## Delete all compiled Python files
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

lint:	## Lint using ruff (use `make format` to do formatting)
	ruff format --check
	ruff check

format:	## Format source code with ruff
	ruff check --fix
	ruff format

test:	## Run tests
	$(PYTHON_CMD) -m pytest tests

notebooks:	## Export all notebooks to script format
	$(PYTHON_CMD) -m nbautoexport export notebooks/

##  
## -------------
## Data pipeline
## -------------

sync_data_down:	## Download Data from storage system
	gsutil -m rsync -r gs://drudid/data/ data/

sync_data_up:	## Upload Data to storage system
	gsutil -m rsync -r data/ gs://drudid/data/

.PHONY: data
data:	## Dataset operations
	$(PYTHON_CMD) -m drudid.dataset $(if $(ARGS),$(ARGS),--help)

