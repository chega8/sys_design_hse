DBT = dbt --profiles-dir .
.PHONY: deps build test docs serve lint clean
deps:
	$(DBT) deps
build:
	$(DBT) build
test:
	$(DBT) test
docs:
	$(DBT) docs generate
serve:
	$(DBT) docs serve --port 8082
lint:
	sqlfluff lint models macros tests
clean:
	$(DBT) clean
