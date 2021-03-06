#
#

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:

ifndef GITHUB_RUN_ID
DOCKER_ARGS := -it
endif

.build: ./pterm/* scripts/pterm
	docker build -t pterm .
	touch .build

pytest: .build
	docker run $(DOCKER_ARGS) -v $(PWD)/scripts/test_pterm.py:/work/scripts/test_pterm.py pterm

dist:
	python3 setup.py sdist bdist_wheel
.PHONY: dist

all:
	@echo "Makefile needs your attention"


# vim:ft=make
#
