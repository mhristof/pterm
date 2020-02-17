#
#

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:


.build: ./pterm/* scripts/pterm
	docker build -t pterm .
	touch .build

pytest: .build
	docker run -it -v $(PWD)/scripts/test_pterm.py:/work/scripts/test_pterm.py pterm

all:
	@echo "Makefile needs your attention"


# vim:ft=make
#
