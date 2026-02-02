def filter_nulls_from_dict(dictionary: dict) -> dict:
	"""Keeps only the keys where the value is not None."""

	return {k: v for k, v in dictionary.items() if v is not None}
