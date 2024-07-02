VERSION := `poetry run python -c "import sys; from watchfs import __version__ as version; sys.stdout.write(version)"`

install:
  poetry install

test:
  poetry run pytest
  just clean

fmt:
  poetry run ruff format .

lint:
  poetry run pyright watchfs tests
  poetry run ruff check .

fmt-docs:
  prettier --write '**/*.md'

build:
  touch watchfs/py.typed
  poetry build

release:
  @echo 'Tagging v{{VERSION}}...'
  git tag "v{{VERSION}}"
  @echo 'Push to GitHub to trigger publish process...'
  git push --tags

publish:
  touch watchfs/py.typed
  poetry publish --build
  git tag "v{{VERSION}}"
  git push --tags
  just clean-builds

clean:
  find . -name "*.pyc" -print0 | xargs -0 rm -f
  rm -rf .pytest_cache/
  rm -rf .mypy_cache/
  find . -maxdepth 3 -type d -empty -print0 | xargs -0 -r rm -r

clean-builds:
  rm -rf build/
  rm -rf dist/
  rm -rf *.egg-info/

ci-install:
  poetry install --no-interaction --no-root

ci-fmt-check:
  poetry run ruff format --check .
  prettier --check '**/*.md'

ci-lint:
  just lint

ci-test:
  poetry run pytest --reruns 3 --reruns-delay 1
  just clean
