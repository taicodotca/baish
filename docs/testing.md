# Testing

## Unit Tests

To run the unit tests, use something like the following commands:

```bash
. .venv/bin/activate && PYTHONPATH=. python -m coverage run -m unittest discover tests/unittests -v
python -m coverage report
```