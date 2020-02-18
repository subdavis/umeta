fmt:
	isort -rc umeta; black .;

dev:
	poetry install


reset:
	rm test.db && umeta migrate
